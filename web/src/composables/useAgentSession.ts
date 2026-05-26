import { computed, onScopeDispose, ref, watch, type Ref } from 'vue';
import {
  cancelAgentJob,
  executeAgentPlan,
  getAgentJob,
  planAgentTask,
  streamAgentJobEvents,
} from '../api/agent';
import { useUserStore } from '../store/user';
import { useLocaleStore } from '../store/locale';
import { ui } from '../utils/ui';
import type {
  AgentExecutionPolicy,
  AgentExecutionResult,
  AgentJobEvent,
  AgentPlanResult,
  AgentReasoningEffort,
  PlanAgentRequest,
} from '../types/agent';

export type MsgStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'canceled';

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  status: MsgStatus;
  planJobId?: string;
  planHash?: string;
  planResult?: AgentPlanResult;
  executeJobId?: string;
  executeResult?: AgentExecutionResult;
  events: AgentJobEvent[];
  errorMessage?: string;
  timestamp: string;
}

export interface Session {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface AgentTurn {
  user: ChatMessage;
  agent: ChatMessage;
}

const STORAGE_KEY = 'fileflash.agent.sessions.v1';
const POLL_INTERVAL_MS = 1200;

const isTerminalStatus = (s?: string | null) =>
  s === 'succeeded' || s === 'failed' || s === 'canceled';

const isEmptySession = (session: Session) => session.messages.length === 0;

const isReadOnlyAutoExecutable = (plan: AgentPlanResult): boolean =>
  plan.proposedActions.length > 0 &&
  plan.proposedActions.every(
    (action) =>
      action.sideEffect === 'read' &&
      action.riskLevel === 'low' &&
      !action.requiresConfirmation,
  );

const toTurns = (messages: ChatMessage[]): AgentTurn[] => {
  const out: AgentTurn[] = [];
  let i = 0;
  while (i < messages.length - 1) {
    const u = messages[i];
    const a = messages[i + 1];
    if (u.role === 'user' && a.role === 'agent') {
      out.push({ user: u, agent: a });
      i += 2;
    } else {
      i += 1;
    }
  }
  return out;
};

const normalizeSessions = (value: unknown): Session[] => {
  if (!Array.isArray(value)) return [];
  const out: Session[] = [];
  let keptEmpty = false;

  for (const raw of value) {
    if (!raw || typeof raw !== 'object') continue;
    const record = raw as Record<string, unknown>;
    if (typeof record.id !== 'string' || !Array.isArray(record.messages)) continue;

    const now = new Date().toISOString();
    const session: Session = {
      id: record.id,
      title: typeof record.title === 'string' ? record.title : 'New session',
      messages: (record.messages as ChatMessage[]).map((message) => ({
        ...message,
        events: Array.isArray(message.events) ? message.events : [],
      })),
      createdAt: typeof record.createdAt === 'string' ? record.createdAt : now,
      updatedAt: typeof record.updatedAt === 'string' ? record.updatedAt : now,
    };

    if (isEmptySession(session)) {
      if (keptEmpty) continue;
      keptEmpty = true;
    }
    out.push(session);
  }
  return out;
};

const loadSessions = (): { sessions: Session[]; shouldPersist: boolean } => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { sessions: [], shouldPersist: false };
    const parsed = JSON.parse(raw);
    const sessions = normalizeSessions(parsed);
    const shouldPersist = JSON.stringify(parsed) !== JSON.stringify(sessions);
    return { sessions, shouldPersist };
  } catch {
    return { sessions: [], shouldPersist: false };
  }
};

const persistSessions = (sessions: Session[]) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {
    // quota or privacy-mode: ignore
  }
};

let msgCounter = 0;
const nextMsgId = () => `msg-${Date.now()}-${++msgCounter}`;
const nextSessionId = () =>
  `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

interface SessionState {
  sessions: Ref<Session[]>;
  activeSessionId: Ref<string | null>;
  policy: Ref<AgentExecutionPolicy>;
  reasoningEffort: Ref<AgentReasoningEffort>;
  taskInput: Ref<string>;
  isSending: Ref<boolean>;
  pollGenerations: Map<string, number>;
  pollSleepTimers: Map<string, ReturnType<typeof setTimeout>>;
  streamControllers: Map<string, AbortController>;
  canceledTurns: Set<string>;
}

let _state: SessionState | null = null;

const getState = (): SessionState => {
  if (_state) return _state;
  const loaded = loadSessions();
  const sessions = ref<Session[]>(loaded.sessions);
  const activeSessionId = ref<string | null>(sessions.value[0]?.id ?? null);
  const policy = ref<AgentExecutionPolicy>('confirm');
  const reasoningEffort = ref<AgentReasoningEffort>('adaptive');
  const taskInput = ref<string>('');
  const isSending = ref<boolean>(false);
  const pollGenerations = new Map<string, number>();
  const pollSleepTimers = new Map<string, ReturnType<typeof setTimeout>>();
  const streamControllers = new Map<string, AbortController>();
  const canceledTurns = new Set<string>();

  watch(sessions, (v) => persistSessions(v), { deep: true });
  if (loaded.shouldPersist) persistSessions(sessions.value);

  _state = {
    sessions,
    activeSessionId,
    policy,
    reasoningEffort,
    taskInput,
    isSending,
    pollGenerations,
    pollSleepTimers,
    streamControllers,
    canceledTurns,
  };
  return _state;
};

export const __resetForTests = () => {
  if (_state) {
    _state.pollSleepTimers.forEach((t) => clearTimeout(t));
    _state.pollSleepTimers.clear();
    _state.streamControllers.forEach((controller) => controller.abort());
    _state.streamControllers.clear();
    _state.pollGenerations.clear();
    _state.canceledTurns.clear();
  }
  _state = null;
};

const buildPlanPayload = (
  input: string,
  policy: AgentExecutionPolicy,
  reasoningEffort: AgentReasoningEffort,
): PlanAgentRequest => ({
  input,
  context: {
    rootFolderId: 'root',
    selectedFileIds: [],
    selectedFolderIds: [],
    currentPath: '/My Files',
  },
  executionPolicy: policy,
  dataPolicy: {
    allowFileContent: false,
    maxReadBytes: 1048576,
    allowedMimeTypes: ['*/*'],
  },
  hints: { preferSkillId: null, maxSteps: 12, budgetTokens: 8000, reasoningEffort },
});

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (error && typeof error === 'object') {
    const response = (error as { response?: { data?: { message?: unknown } } }).response;
    const responseMessage = response?.data?.message;
    if (typeof responseMessage === 'string' && responseMessage.trim()) {
      return responseMessage.trim();
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  if (error && typeof error === 'object') {
    const plainMessage = (error as { message?: unknown }).message;
    if (typeof plainMessage === 'string' && plainMessage.trim()) {
      return plainMessage.trim();
    }
  }
  return fallback;
};

export default function useAgentSession() {
  const s = getState();
  const userStore = useUserStore();
  const localeStore = useLocaleStore();
  const t = localeStore.t;

  const activeSession = computed(() => {
    if (!s.activeSessionId.value) return null;
    return s.sessions.value.find((c) => c.id === s.activeSessionId.value) ?? null;
  });

  const activeTurns = computed<AgentTurn[]>(() => toTurns(activeSession.value?.messages ?? []));

  const nextPollGeneration = (key: string): number => {
    const generation = (s.pollGenerations.get(key) ?? 0) + 1;
    s.pollGenerations.set(key, generation);
    return generation;
  };

  const clearSleepTimer = (key: string) => {
    const timer = s.pollSleepTimers.get(key);
    if (!timer) return;
    clearTimeout(timer);
    s.pollSleepTimers.delete(key);
  };

  const stopPolling = (key: string) => {
    nextPollGeneration(key);
    clearSleepTimer(key);
  };

  const stopStream = (key: string) => {
    const controller = s.streamControllers.get(key);
    if (!controller) return;
    controller.abort();
    s.streamControllers.delete(key);
  };

  const stopAllPolling = () => {
    s.pollSleepTimers.forEach((t) => clearTimeout(t));
    s.pollSleepTimers.clear();
    s.streamControllers.forEach((controller) => controller.abort());
    s.streamControllers.clear();
    s.pollGenerations.clear();
  };

  const isTurnCanceled = (msg: ChatMessage): boolean => s.canceledTurns.has(msg.id);

  const clearTurnCanceled = (msg: ChatMessage) => {
    s.canceledTurns.delete(msg.id);
  };

  const markTurnCanceled = (msg: ChatMessage) => {
    s.canceledTurns.add(msg.id);
  };

  const ensureTurnNotCanceled = (msg: ChatMessage): boolean =>
    !isTurnCanceled(msg) && msg.status !== 'canceled';

  const startPollLoop = async (
    key: string,
    msg: ChatMessage,
    tick: (generation: number) => Promise<boolean>,
  ): Promise<void> => {
    const generation = nextPollGeneration(key);
    const run = async (): Promise<void> => {
      if (s.pollGenerations.get(key) !== generation) return;
      if (!ensureTurnNotCanceled(msg)) {
        stopPolling(key);
        return;
      }
      const shouldContinue = await tick(generation);
      if (s.pollGenerations.get(key) !== generation) return;
      if (!shouldContinue) {
        stopPolling(key);
        return;
      }
      const timer = setTimeout(() => {
        if (s.pollSleepTimers.get(key) === timer) {
          s.pollSleepTimers.delete(key);
        }
        void run();
      }, POLL_INTERVAL_MS);
      s.pollSleepTimers.set(key, timer);
    };
    await run();
  };

  const createSession = () => {
    const empty = s.sessions.value.find(isEmptySession);
    if (empty) {
      stopAllPolling();
      s.activeSessionId.value = empty.id;
      s.taskInput.value = '';
      return empty;
    }

    const id = nextSessionId();
    const now = new Date().toISOString();
    const session: Session = {
      id,
      title: 'New session',
      messages: [],
      createdAt: now,
      updatedAt: now,
    };
    s.sessions.value.unshift(session);
    s.activeSessionId.value = id;
    s.taskInput.value = '';
    stopAllPolling();
    return session;
  };

  const switchSession = (id: string) => {
    if (s.activeSessionId.value === id) return;
    stopAllPolling();
    s.activeSessionId.value = id;
    s.taskInput.value = '';
  };

  const deleteSession = (id: string) => {
    const idx = s.sessions.value.findIndex((c) => c.id === id);
    if (idx === -1) return;
    const target = s.sessions.value[idx];
    target.messages.forEach((msg) => {
      clearTurnCanceled(msg);
      stopPolling(`${msg.id}:plan`);
      stopPolling(`${msg.id}:execute`);
      stopStream(`${msg.id}:plan`);
      stopStream(`${msg.id}:execute`);
    });
    s.sessions.value.splice(idx, 1);
    if (s.activeSessionId.value === id) {
      stopAllPolling();
      s.activeSessionId.value = s.sessions.value.length
        ? s.sessions.value[Math.min(idx, s.sessions.value.length - 1)].id
        : null;
    }
  };

  const resetActiveSession = () => {
    if (!activeSession.value) return;
    activeSession.value.messages.forEach((msg) => {
      clearTurnCanceled(msg);
      stopPolling(`${msg.id}:plan`);
      stopPolling(`${msg.id}:execute`);
      stopStream(`${msg.id}:plan`);
      stopStream(`${msg.id}:execute`);
    });
    stopAllPolling();
    activeSession.value.messages = [];
    activeSession.value.title = 'New session';
    s.isSending.value = false;
  };

  const ensureSession = (): Session => activeSession.value ?? createSession();

  const appendAgentEvent = (msg: ChatMessage, event: AgentJobEvent) => {
    if (msg.events.some((item) => item.id === event.id)) return;
    msg.events.push(event);
  };

  const applyAgentEvent = (msg: ChatMessage, event: AgentJobEvent, kind: 'plan' | 'execute') => {
    appendAgentEvent(msg, event);
    if (event.type === 'job.queued') {
      msg.status = 'pending';
    } else if (event.type === 'job.running' || event.type === 'tool.started') {
      msg.status = 'running';
    } else if (event.type === 'job.failed' || event.type === 'tool.failed') {
      msg.status = 'failed';
      const errorMessage = event.data?.errorMessage;
      msg.errorMessage = typeof errorMessage === 'string' ? errorMessage : event.message;
    } else if (event.type === 'job.canceled') {
      msg.status = 'canceled';
    } else if (event.type === 'job.succeeded') {
      msg.status = 'succeeded';
    }

    const result = event.data?.result;
    if (event.type === 'plan.ready' && result) {
      msg.planResult = result as AgentPlanResult;
      msg.planHash = msg.planResult.planHash;
    }
    if (event.type === 'job.succeeded' && result) {
      if (kind === 'plan') {
        msg.planResult = result as AgentPlanResult;
        msg.planHash = msg.planResult.planHash;
      } else {
        msg.executeResult = result as AgentExecutionResult;
      }
    }
  };

  const shouldAutoExecutePlan = (msg: ChatMessage): boolean =>
    Boolean(
      msg.planResult &&
        ((s.policy.value === 'autopilot' && !msg.planResult.requiresConfirmation) ||
          (s.policy.value === 'confirm' && isReadOnlyAutoExecutable(msg.planResult))),
    );

  async function streamJobEvents(
    kind: 'plan' | 'execute',
    msg: ChatMessage,
    jobId: string,
  ): Promise<boolean> {
    const timerKey = `${msg.id}:${kind}`;
    stopStream(timerKey);
    const controller = new AbortController();
    s.streamControllers.set(timerKey, controller);
    try {
      await streamAgentJobEvents(
        jobId,
        {
          onEvent: (event) => {
            if (!ensureTurnNotCanceled(msg)) return;
            applyAgentEvent(msg, event, kind);
          },
        },
        controller.signal,
      );
      return true;
    } catch {
      return controller.signal.aborted;
    } finally {
      if (s.streamControllers.get(timerKey) === controller) {
        s.streamControllers.delete(timerKey);
      }
    }
  }

  async function pollPlanJob(msg: ChatMessage, jobId: string): Promise<void> {
    const timerKey = `${msg.id}:plan`;
    await startPollLoop(timerKey, msg, async (generation) => {
      try {
        const job = await getAgentJob<AgentPlanResult>(jobId);
        if (s.pollGenerations.get(timerKey) !== generation || !ensureTurnNotCanceled(msg)) return false;
        msg.status = (job.status as MsgStatus) || 'running';

        if (job.status === 'succeeded' && job.result) {
          msg.planResult = job.result;
          msg.planHash = job.result.planHash;
        }
        if (job.status === 'failed' || job.status === 'canceled') {
          msg.errorMessage = job.errorMessage || 'Plan failed.';
        }
        if (isTerminalStatus(job.status)) {
          if (shouldAutoExecutePlan(msg)) {
            await runExecute(msg);
          }
          return false;
        }
        return true;
      } catch {
        // network blips: skip this tick
        return true;
      }
    });
  }

  async function pollExecuteJob(msg: ChatMessage, jobId: string): Promise<void> {
    const timerKey = `${msg.id}:execute`;
    await startPollLoop(timerKey, msg, async (generation) => {
      try {
        const job = await getAgentJob<AgentExecutionResult>(jobId);
        if (s.pollGenerations.get(timerKey) !== generation || !ensureTurnNotCanceled(msg)) return false;
        msg.status = (job.status as MsgStatus) || 'running';

        if (job.status === 'succeeded' && job.result) {
          msg.executeResult = job.result;
        }
        if (job.status === 'failed' || job.status === 'canceled') {
          msg.errorMessage = job.errorMessage || 'Execute failed.';
        }
        if (isTerminalStatus(job.status)) return false;
        return true;
      } catch {
        // skip
        return true;
      }
    });
  }

  async function sendMessage(): Promise<void> {
    const input = s.taskInput.value.trim();
    if (!input || s.isSending.value) return;
    const session = ensureSession();
    s.isSending.value = true;

    const now = new Date().toISOString();
    const userMsg: ChatMessage = {
      id: nextMsgId(),
      role: 'user',
      content: input,
      status: 'succeeded',
      events: [],
      timestamp: now,
    };
    const agentMsg: ChatMessage = {
      id: nextMsgId(),
      role: 'agent',
      content: '',
      status: 'pending',
      events: [],
      timestamp: now,
    };
    session.messages.push(userMsg, agentMsg);
    session.updatedAt = now;
    if (session.title === 'New session') {
      session.title = input.slice(0, 40) + (input.length > 40 ? '…' : '');
    }
    s.taskInput.value = '';

    const reactiveAgent = session.messages[session.messages.length - 1];
    clearTurnCanceled(reactiveAgent);

    try {
      const res = await planAgentTask(buildPlanPayload(input, s.policy.value, s.reasoningEffort.value));
      reactiveAgent.planJobId = res.jobId;
      if (isTurnCanceled(reactiveAgent) || reactiveAgent.status === 'canceled') {
        try {
          await cancelAgentJob(res.jobId);
        } catch {
          // ignore cancellation sync errors after local cancel
        }
        return;
      }
      reactiveAgent.status = 'pending';
      const streamed = await streamJobEvents('plan', reactiveAgent, res.jobId);
      if (!streamed && ensureTurnNotCanceled(reactiveAgent)) {
        await pollPlanJob(reactiveAgent, res.jobId);
      } else if (streamed && ensureTurnNotCanceled(reactiveAgent) && shouldAutoExecutePlan(reactiveAgent)) {
        await runExecute(reactiveAgent);
      }
    } catch (error) {
      if (isTurnCanceled(reactiveAgent) || reactiveAgent.status === 'canceled') return;
      reactiveAgent.status = 'failed';
      reactiveAgent.errorMessage = extractErrorMessage(error, 'Plan failed.');
    } finally {
      s.isSending.value = false;
    }
  }

  async function runExecute(msg: ChatMessage): Promise<void> {
    if (!msg.planResult || !msg.planHash) return;
    if (msg.executeJobId) return;
    if (msg.status !== 'succeeded') return;
    if (isTurnCanceled(msg)) return;
    const highRisk = msg.planResult.proposedActions.some(
      (action) => action.riskLevel === 'high' || action.requiresConfirmation,
    );
    const confirmedAt = new Date().toISOString();
    if (highRisk) {
      const reason =
        msg.planResult.proposedActions.find((action) => action.riskLevel === 'high' || action.requiresConfirmation)
          ?.confirmationReason || t('agent.v2.confirm.highRisk.message');
      const ok = await ui.confirm({
        title: t('agent.v2.confirm.highRisk.title'),
        message: reason,
        confirmText: t('agent.v2.confirm.highRisk.confirm'),
        cancelText: t('agent.v2.confirm.highRisk.cancel'),
        danger: true,
      });
      if (!ok) return;
    }
    if (!ensureTurnNotCanceled(msg)) return;
    msg.status = 'running';
    msg.errorMessage = '';
    msg.executeResult = undefined;

    try {
      const res = await executeAgentPlan({
        planJobId: msg.planResult.planJobId,
        planHash: msg.planHash,
        approval: {
          confirmedBy: userStore.user?.userId || 'current-user',
          confirmedAt,
          highRiskConfirmed: highRisk,
          highRiskConfirmedAt: highRisk ? confirmedAt : undefined,
        },
      });
      msg.executeJobId = res.jobId;
      if (!ensureTurnNotCanceled(msg)) {
        try {
          await cancelAgentJob(res.jobId);
        } catch {
          // ignore cancellation sync errors after local cancel
        }
        return;
      }
      const streamed = await streamJobEvents('execute', msg, res.jobId);
      if (!streamed && ensureTurnNotCanceled(msg)) {
        await pollExecuteJob(msg, res.jobId);
      }
    } catch (error) {
      if (!ensureTurnNotCanceled(msg)) return;
      msg.status = 'failed';
      msg.errorMessage = extractErrorMessage(error, 'Execute failed.');
    }
  }

  async function cancel(msg: ChatMessage): Promise<void> {
    markTurnCanceled(msg);
    msg.status = 'canceled';
    const jobId = msg.executeJobId || msg.planJobId;
    stopPolling(`${msg.id}:plan`);
    stopPolling(`${msg.id}:execute`);
    stopStream(`${msg.id}:plan`);
    stopStream(`${msg.id}:execute`);
    if (!jobId) return;
    try {
      await cancelAgentJob(jobId);
    } catch (error) {
      msg.errorMessage = extractErrorMessage(error, 'Cancel failed.');
    }
  }

  onScopeDispose(() => {
    // Each component disposal: leave singleton state intact but clean
    // its own listeners (none to clean here beyond polling, which
    // stays with the singleton).
  });

  return {
    sessions: s.sessions,
    activeSessionId: s.activeSessionId,
    activeSession,
    activeTurns,
    policy: s.policy,
    reasoningEffort: s.reasoningEffort,
    taskInput: s.taskInput,
    isSending: s.isSending,
    createSession,
    switchSession,
    deleteSession,
    resetActiveSession,
    sendMessage,
    runExecute,
    cancel,
  };
}
