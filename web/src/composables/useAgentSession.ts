import { computed, onScopeDispose, ref, watch, type Ref } from 'vue';
import {
  cancelAgentJob,
  executeAgentPlan,
  getAgentJob,
  planAgentTask,
} from '../api/agent';
import { useUserStore } from '../store/user';
import type {
  AgentExecutionPolicy,
  AgentExecutionResult,
  AgentPlanResult,
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

const isTerminalStatus = (s?: string | null) =>
  s === 'succeeded' || s === 'failed' || s === 'canceled';

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

const loadSessions = (): Session[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((s) => s && typeof s.id === 'string' && Array.isArray(s.messages));
  } catch {
    return [];
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
  taskInput: Ref<string>;
  isSending: Ref<boolean>;
  pollTimers: Map<string, ReturnType<typeof setInterval>>;
}

let _state: SessionState | null = null;

const getState = (): SessionState => {
  if (_state) return _state;
  const sessions = ref<Session[]>(loadSessions());
  const activeSessionId = ref<string | null>(sessions.value[0]?.id ?? null);
  const policy = ref<AgentExecutionPolicy>('confirm');
  const taskInput = ref<string>('');
  const isSending = ref<boolean>(false);
  const pollTimers = new Map<string, ReturnType<typeof setInterval>>();

  watch(sessions, (v) => persistSessions(v), { deep: true });

  _state = { sessions, activeSessionId, policy, taskInput, isSending, pollTimers };
  return _state;
};

export const __resetForTests = () => {
  if (_state) {
    _state.pollTimers.forEach((t) => clearInterval(t));
    _state.pollTimers.clear();
  }
  _state = null;
};

const buildPlanPayload = (input: string, policy: AgentExecutionPolicy): PlanAgentRequest => ({
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
  hints: { preferSkillId: null, maxSteps: 12, budgetTokens: 8000 },
});

export default function useAgentSession() {
  const s = getState();
  const userStore = useUserStore();

  const activeSession = computed(() => {
    if (!s.activeSessionId.value) return null;
    return s.sessions.value.find((c) => c.id === s.activeSessionId.value) ?? null;
  });

  const activeTurns = computed<AgentTurn[]>(() => toTurns(activeSession.value?.messages ?? []));

  const stopPolling = (key: string) => {
    const t = s.pollTimers.get(key);
    if (t) {
      clearInterval(t);
      s.pollTimers.delete(key);
    }
  };

  const stopAllPolling = () => {
    s.pollTimers.forEach((t) => clearInterval(t));
    s.pollTimers.clear();
  };

  const createSession = () => {
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
    stopAllPolling();
    activeSession.value.messages = [];
    activeSession.value.title = 'New session';
    s.isSending.value = false;
  };

  const ensureSession = (): Session => activeSession.value ?? createSession();

  async function pollPlanJob(msg: ChatMessage, jobId: string): Promise<void> {
    const timerKey = `${msg.id}:plan`;
    stopPolling(timerKey);

    const tick = async () => {
      try {
        const job = await getAgentJob<AgentPlanResult>(jobId);
        msg.status = (job.status as MsgStatus) || 'running';

        if (job.status === 'succeeded' && job.result) {
          msg.planResult = job.result;
          msg.planHash = job.result.planHash;
        }
        if (job.status === 'failed' || job.status === 'canceled') {
          msg.errorMessage = job.errorMessage || 'Plan failed.';
        }
        if (isTerminalStatus(job.status)) {
          stopPolling(timerKey);
          if (msg.planResult && s.policy.value === 'autopilot') {
            await runExecute(msg);
          }
        }
      } catch {
        // network blips: skip this tick
      }
    };

    await tick();
    if (!isTerminalStatus(msg.status)) {
      s.pollTimers.set(timerKey, setInterval(tick, 1200));
    }
  }

  async function pollExecuteJob(msg: ChatMessage, jobId: string): Promise<void> {
    const timerKey = `${msg.id}:execute`;
    stopPolling(timerKey);

    const tick = async () => {
      try {
        const job = await getAgentJob<AgentExecutionResult>(jobId);
        msg.status = (job.status as MsgStatus) || 'running';

        if (job.status === 'succeeded' && job.result) {
          msg.executeResult = job.result;
        }
        if (job.status === 'failed' || job.status === 'canceled') {
          msg.errorMessage = job.errorMessage || 'Execute failed.';
        }
        if (isTerminalStatus(job.status)) stopPolling(timerKey);
      } catch {
        // skip
      }
    };

    await tick();
    if (!isTerminalStatus(msg.status)) {
      s.pollTimers.set(timerKey, setInterval(tick, 1200));
    }
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
      timestamp: now,
    };
    const agentMsg: ChatMessage = {
      id: nextMsgId(),
      role: 'agent',
      content: '',
      status: 'pending',
      timestamp: now,
    };
    session.messages.push(userMsg, agentMsg);
    session.updatedAt = now;
    if (session.title === 'New session') {
      session.title = input.slice(0, 40) + (input.length > 40 ? '…' : '');
    }
    s.taskInput.value = '';

    const reactiveAgent = session.messages[session.messages.length - 1];

    try {
      const res = await planAgentTask(buildPlanPayload(input, s.policy.value));
      reactiveAgent.planJobId = res.jobId;
      reactiveAgent.status = 'pending';
      await pollPlanJob(reactiveAgent, res.jobId);
    } catch {
      reactiveAgent.status = 'failed';
      reactiveAgent.errorMessage = 'Plan failed.';
    } finally {
      s.isSending.value = false;
    }
  }

  async function runExecute(msg: ChatMessage): Promise<void> {
    if (!msg.planResult || !msg.planHash) return;
    msg.status = 'running';
    msg.errorMessage = '';
    msg.executeResult = undefined;

    try {
      const res = await executeAgentPlan({
        planJobId: msg.planResult.planJobId,
        planHash: msg.planHash,
        approval: {
          confirmedBy: userStore.user?.userId || 'current-user',
          confirmedAt: new Date().toISOString(),
        },
      });
      msg.executeJobId = res.jobId;
      await pollExecuteJob(msg, res.jobId);
    } catch {
      msg.status = 'failed';
      msg.errorMessage = 'Execute failed.';
    }
  }

  async function cancel(msg: ChatMessage): Promise<void> {
    const jobId = msg.executeJobId || msg.planJobId;
    stopPolling(`${msg.id}:plan`);
    stopPolling(`${msg.id}:execute`);
    if (!jobId) return;
    try {
      await cancelAgentJob(jobId);
      msg.status = 'canceled';
    } catch {
      msg.errorMessage = 'Cancel failed.';
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
