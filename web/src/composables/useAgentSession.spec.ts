import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { nextTick } from 'vue';
import type { ChatMessage } from './useAgentSession';

vi.mock('../api/agent', () => ({
  planAgentTask: vi.fn(),
  executeAgentPlan: vi.fn(),
  cancelAgentTurn: vi.fn(),
  getAgentJob: vi.fn(),
  streamAgentJobEvents: vi.fn(),
  sendAgentMessage: vi.fn(),
  sendAgentReply: vi.fn(),
  pauseAgentJob: vi.fn(),
  resumeAgentJob: vi.fn(),
  approveAgentStep: vi.fn(),
  denyAgentStep: vi.fn(),
  skipAgentStep: vi.fn(),
}));

vi.mock('../store/user', () => ({
  useUserStore: () => ({ user: { userId: 'u-1' } }),
}));

vi.mock('../store/locale', () => ({
  useLocaleStore: () => ({ t: (key: string) => key }),
}));

import * as agentApi from '../api/agent';

const STORAGE_KEY = 'fileflash.agent.sessions.v1';

const planResult = {
  planJobId: 'job-1',
  planHash: 'hash-1',
  chosenSkill: null,
  proposedActions: [],
  summary: 'do it',
  requiresConfirmation: false,
  costEstimate: { tokens: 10, toolCalls: 1, durationSecEstimate: 1 },
};

const readOnlyPlanResult = {
  ...planResult,
  proposedActions: [
    {
      step: 1,
      tool: 'drive.countFiles',
      input: { folderId: 'root', recursive: true, category: 'video' },
      sideEffect: 'read',
      riskLevel: 'low',
      requiresConfirmation: false,
      confirmationReason: null,
    },
  ],
  requiresConfirmation: true,
};

const readOnlyPlanResultWithEvidence = {
  ...readOnlyPlanResult,
  planningEvidence: [
    {
      step: 1,
      tool: 'drive.searchFiles',
      input: { folderId: 'root', query: '银翼杀手', category: 'video' },
      outputPreview: {
        totalItems: 2,
        items: [
          { fileId: '19', name: '银翼杀手1982.mp4' },
          { fileId: '20', name: '银翼杀手2049.mp4' },
        ],
      },
    },
  ],
};

const writePlanResult = {
  ...planResult,
  proposedActions: [
    {
      step: 1,
      tool: 'drive.createFolder',
      input: { parentFolderId: 'root', name: 'Movies' },
      sideEffect: 'write',
      riskLevel: 'medium',
      requiresConfirmation: false,
      confirmationReason: null,
    },
  ],
  requiresConfirmation: true,
};

const execResult = {
  planJobId: 'job-1',
  executeJobId: 'job-2',
  summary: 'done',
  answer: '你上传了 3 部电影（按视频文件统计）。',
  appliedActions: 1,
  skippedActions: 0,
  warnings: [],
  finishedAt: '2026-05-20T00:00:00Z',
};

const loadComposable = async () => {
  const mod = await import('./useAgentSession');
  return mod;
};

const deferred = <T>() => {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

describe('useAgentSession', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.useFakeTimers();
    vi.mocked(agentApi.streamAgentJobEvents).mockRejectedValue(new Error('stream unavailable'));
  });

  afterEach(async () => {
    const { __resetForTests } = await loadComposable();
    __resetForTests();
    vi.useRealTimers();
  });

  it('createSession adds a session, sets active, persists to localStorage', async () => {
    const { default: useAgentSession } = await loadComposable();
    const { sessions, activeSessionId, createSession } = useAgentSession();
    createSession();
    expect(sessions.value.length).toBe(1);
    expect(activeSessionId.value).toBe(sessions.value[0].id);
    await nextTick();
    const stored = localStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored!).length).toBe(1);
  });

  it('createSession reuses existing empty session and does not grow list', async () => {
    const { default: useAgentSession } = await loadComposable();
    const { sessions, activeSessionId, createSession } = useAgentSession();
    const first = createSession();
    const second = createSession();

    expect(sessions.value.length).toBe(1);
    expect(second.id).toBe(first.id);
    expect(activeSessionId.value).toBe(first.id);
  });

  it('createSession creates new only when there is no empty session', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);

    const { default: useAgentSession } = await loadComposable();
    const { sessions, taskInput, sendMessage, createSession } = useAgentSession();

    createSession();
    taskInput.value = 'hello';
    await sendMessage();

    expect(sessions.value.length).toBe(1);
    const firstId = sessions.value[0].id;

    const created = createSession();
    expect(sessions.value.length).toBe(2);
    expect(created.id).not.toBe(firstId);

    const reused = createSession();
    expect(sessions.value.length).toBe(2);
    expect(reused.id).toBe(created.id);
  });

  it('sendMessage plans and polls to succeeded', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, activeSession } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const conv = activeSession.value!;
    expect(conv.messages.length).toBe(2);
    expect(conv.messages[0].role).toBe('user');
    expect(conv.messages[1].role).toBe('agent');
    expect(conv.messages[1].planResult?.planHash).toBe('hash-1');
    expect(conv.messages[1].planHash).toBe('hash-1');
    expect(conv.messages[1].status).toBe('succeeded');
    expect(agentApi.planAgentTask).toHaveBeenCalled();
  });

  it('runExecute is a no-op when executeJobId is already set', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);
    vi.mocked(agentApi.executeAgentPlan).mockResolvedValue({
      jobId: 'job-2',
      status: 'pending',
      taskType: 'agent.execute',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, runExecute, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    turn.agent.executeJobId = 'already-exec-1';
    await runExecute(turn.agent);
    expect(agentApi.executeAgentPlan).not.toHaveBeenCalled();
  });

  it('runExecute is a no-op when the turn is not in succeeded state', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);
    vi.mocked(agentApi.executeAgentPlan).mockResolvedValue({
      jobId: 'job-2',
      status: 'pending',
      taskType: 'agent.execute',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, runExecute, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    turn.agent.status = 'running';
    await runExecute(turn.agent);
    expect(agentApi.executeAgentPlan).not.toHaveBeenCalled();
  });

  it('runExecute calls executeAgentPlan and polls to succeeded', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob)
      .mockResolvedValueOnce({ jobId: 'job-1', status: 'succeeded', result: planResult } as any)
      .mockResolvedValueOnce({ jobId: 'job-2', status: 'succeeded', result: execResult } as any);
    vi.mocked(agentApi.executeAgentPlan).mockResolvedValue({
      jobId: 'job-2',
      status: 'pending',
      taskType: 'agent.execute',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, runExecute, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    await runExecute(turn.agent);
    expect(agentApi.executeAgentPlan).toHaveBeenCalled();
    expect(turn.agent.executeResult?.executeJobId).toBe('job-2');
    expect(turn.agent.status).toBe('succeeded');
  });

  it('auto-executes read-only low-risk plans in confirm policy', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob)
      .mockResolvedValueOnce({ jobId: 'job-1', status: 'succeeded', result: readOnlyPlanResult } as any)
      .mockResolvedValueOnce({ jobId: 'job-2', status: 'succeeded', result: execResult } as any);
    vi.mocked(agentApi.executeAgentPlan).mockResolvedValue({
      jobId: 'job-2',
      status: 'pending',
      taskType: 'agent.execute',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, activeTurns } = useAgentSession();
    taskInput.value = '我上传了多少部电影？';
    await sendMessage();

    const turn = activeTurns.value[0];
    expect(agentApi.executeAgentPlan).toHaveBeenCalled();
    expect(turn.agent.executeResult?.answer).toContain('3 部电影');
    expect(turn.agent.status).toBe('succeeded');
  });

  it('uses streamed plan and execute events when available', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.executeAgentPlan).mockResolvedValue({
      jobId: 'job-2',
      status: 'pending',
      taskType: 'agent.execute',
    });
    vi.mocked(agentApi.streamAgentJobEvents)
      .mockImplementationOnce(async (_jobId, handlers) => {
        handlers?.onEvent?.({
          id: 'plan-ready-1',
          jobId: 'job-1',
          taskType: 'agent.plan',
          type: 'plan.ready',
          status: 'succeeded',
          agentPhase: 'completed',
          message: '计划已生成。',
          data: { result: readOnlyPlanResultWithEvidence },
          timestamp: '2026-05-20T00:00:00Z',
        });
        handlers?.onEvent?.({
          id: 'plan-done-1',
          jobId: 'job-1',
          taskType: 'agent.plan',
          type: 'job.succeeded',
          status: 'succeeded',
          agentPhase: 'completed',
          message: '任务已完成。',
          data: { result: readOnlyPlanResultWithEvidence },
          timestamp: '2026-05-20T00:00:01Z',
        });
      })
      .mockImplementationOnce(async (_jobId, handlers) => {
        handlers?.onEvent?.({
          id: 'tool-start-1',
          jobId: 'job-2',
          taskType: 'agent.execute',
          type: 'tool.started',
          status: 'running',
          agentPhase: 'executing',
          message: '正在读取名称包含“银翼杀手”的视频文件数量。',
          data: { step: 1, tool: 'drive.countFiles' },
          timestamp: '2026-05-20T00:00:02Z',
        });
        handlers?.onEvent?.({
          id: 'execute-done-1',
          jobId: 'job-2',
          taskType: 'agent.execute',
          type: 'job.succeeded',
          status: 'succeeded',
          agentPhase: 'completed',
          message: '答案已生成。',
          data: { result: execResult },
          timestamp: '2026-05-20T00:00:03Z',
        });
      });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, activeTurns } = useAgentSession();
    taskInput.value = '我上传了几部银翼杀手？';
    await sendMessage();

    const turn = activeTurns.value[0];
    expect(agentApi.getAgentJob).not.toHaveBeenCalled();
    expect(agentApi.executeAgentPlan).toHaveBeenCalled();
    expect(turn.agent.events.map((event) => event.id)).toContain('tool-start-1');
    expect(turn.agent.planResult?.planningEvidence?.[0]?.tool).toBe('drive.searchFiles');
    expect(turn.agent.executeResult?.answer).toContain('3 部电影');
    expect(turn.agent.status).toBe('succeeded');
  });

  it('does not auto-execute write plans in confirm policy', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: writePlanResult,
    } as any);

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, activeTurns } = useAgentSession();
    taskInput.value = '整理电影';
    await sendMessage();

    const turn = activeTurns.value[0];
    expect(agentApi.executeAgentPlan).not.toHaveBeenCalled();
    expect(turn.agent.executeJobId).toBeUndefined();
    expect(turn.agent.status).toBe('succeeded');
  });

  it('does not auto-execute read-only plans in planOnly policy', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: readOnlyPlanResult,
    } as any);

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, policy, sendMessage, activeTurns } = useAgentSession();
    policy.value = 'planOnly';
    taskInput.value = '我上传了多少部电影？';
    await sendMessage();

    const turn = activeTurns.value[0];
    expect(agentApi.executeAgentPlan).not.toHaveBeenCalled();
    expect(turn.agent.executeResult).toBeUndefined();
    expect(turn.agent.status).toBe('succeeded');
  });

  it('runExecute surfaces backend response message when execute returns 409', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);
    vi.mocked(agentApi.executeAgentPlan).mockRejectedValue({
      response: { data: { message: 'planHash mismatch' } },
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, runExecute, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    await runExecute(turn.agent);

    expect(turn.agent.status).toBe('failed');
    expect(turn.agent.errorMessage).toBe('planHash mismatch');
  });

  it('runExecute falls back to Error.message when backend message is missing', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);
    vi.mocked(agentApi.executeAgentPlan).mockRejectedValue(new Error('network timeout'));

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, runExecute, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    await runExecute(turn.agent);

    expect(turn.agent.status).toBe('failed');
    expect(turn.agent.errorMessage).toBe('network timeout');
  });

  it('runExecute falls back to default message when error has no message', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'succeeded',
      result: planResult,
    } as any);
    vi.mocked(agentApi.executeAgentPlan).mockRejectedValue({});

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, runExecute, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    await runExecute(turn.agent);

    expect(turn.agent.status).toBe('failed');
    expect(turn.agent.errorMessage).toBe('Execute failed.');
  });

  it('cancel calls cancelAgentTurn and clears polling for that turn', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    // Keep job 'running' so interval is scheduled
    vi.mocked(agentApi.getAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'running',
    } as any);
    vi.mocked(agentApi.cancelAgentTurn).mockResolvedValue({
      inboxMessageId: 'inbox-1',
      kind: 'control.cancel',
      acceptedAt: '2026-05-20T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, cancel, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    const callsBefore = vi.mocked(agentApi.getAgentJob).mock.calls.length;
    await cancel(turn.agent);
    expect(agentApi.cancelAgentTurn).toHaveBeenCalled();
    // Advance time to ensure timer wouldn't fire again
    await vi.advanceTimersByTimeAsync(3000);
    const callsAfter = vi.mocked(agentApi.getAgentJob).mock.calls.length;
    expect(callsAfter).toBe(callsBefore);
  });

  it('cancel before plan job id arrives keeps turn canceled and does not start polling', async () => {
    const planGate = deferred<any>();
    vi.mocked(agentApi.planAgentTask).mockReturnValue(planGate.promise);
    vi.mocked(agentApi.cancelAgentTurn).mockResolvedValue({
      inboxMessageId: 'inbox-late',
      kind: 'control.cancel',
      acceptedAt: '2026-05-20T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, cancel, activeTurns } = useAgentSession();
    taskInput.value = 'hello';

    const sendTask = sendMessage();
    await Promise.resolve();
    const turn = activeTurns.value[0];
    await cancel(turn.agent);
    expect(turn.agent.status).toBe('canceled');

    planGate.resolve({
      jobId: 'job-late',
      status: 'pending',
      taskType: 'agent.plan',
    });
    await sendTask;

    expect(agentApi.getAgentJob).not.toHaveBeenCalled();
    expect(agentApi.cancelAgentTurn).toHaveBeenCalledWith('job-late');
    expect(turn.agent.status).toBe('canceled');
  });

  it('in-flight poll response after cancel cannot overwrite canceled status', async () => {
    const firstPoll = deferred<any>();
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-1',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.getAgentJob).mockReturnValue(firstPoll.promise);
    vi.mocked(agentApi.cancelAgentTurn).mockResolvedValue({
      inboxMessageId: 'inbox-1',
      kind: 'control.cancel',
      acceptedAt: '2026-05-20T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, cancel, activeTurns } = useAgentSession();
    taskInput.value = 'hello';

    const sendTask = sendMessage();
    for (let i = 0; i < 6 && vi.mocked(agentApi.getAgentJob).mock.calls.length === 0; i += 1) {
      await Promise.resolve();
    }
    const turn = activeTurns.value[0];
    await cancel(turn.agent);
    expect(turn.agent.status).toBe('canceled');

    firstPoll.resolve({
      jobId: 'job-1',
      status: 'running',
    });
    await sendTask;
    await vi.advanceTimersByTimeAsync(3000);

    expect(turn.agent.status).toBe('canceled');
    expect(vi.mocked(agentApi.getAgentJob).mock.calls.length).toBe(1);
  });

  it('applies ask, progress, thinking, pause, resume, and partial stream events', async () => {
    vi.mocked(agentApi.planAgentTask).mockResolvedValue({
      jobId: 'job-ask',
      status: 'pending',
      taskType: 'agent.plan',
    });
    vi.mocked(agentApi.streamAgentJobEvents).mockImplementationOnce(async (_jobId, handlers) => {
      handlers?.onEvent?.({
        id: 'progress-1',
        jobId: 'job-ask',
        taskType: 'agent.plan',
        type: 'agent.progress',
        status: 'running',
        agentPhase: 'planning',
        message: 'step one',
        data: { step: 1, total: 3, message: 'Reading folders', percent: 33 },
        timestamp: '2026-05-26T00:00:00Z',
      });
      handlers?.onEvent?.({
        id: 'thinking-1',
        jobId: 'job-ask',
        taskType: 'agent.plan',
        type: 'agent.thinking',
        status: 'running',
        agentPhase: 'planning',
        message: '',
        data: { text: 'Need user choice.' },
        timestamp: '2026-05-26T00:00:01Z',
      });
      handlers?.onEvent?.({
        id: 'partial-1',
        jobId: 'job-ask',
        taskType: 'agent.plan',
        type: 'tool.partial',
        status: 'running',
        agentPhase: 'planning',
        message: '',
        data: { step: 1, tool: 'drive.listFolder', chunk: { name: 'A' } },
        timestamp: '2026-05-26T00:00:02Z',
      });
      handlers?.onEvent?.({
        id: 'paused-1',
        jobId: 'job-ask',
        taskType: 'agent.plan',
        type: 'agent.paused',
        status: 'paused',
        agentPhase: 'planning',
        message: 'paused',
        data: {},
        timestamp: '2026-05-26T00:00:03Z',
      });
      handlers?.onEvent?.({
        id: 'resumed-1',
        jobId: 'job-ask',
        taskType: 'agent.plan',
        type: 'agent.resumed',
        status: 'running',
        agentPhase: 'planning',
        message: 'resumed',
        data: {},
        timestamp: '2026-05-26T00:00:04Z',
      });
      handlers?.onEvent?.({
        id: 'ask-1',
        jobId: 'job-ask',
        taskType: 'agent.plan',
        type: 'agent.ask',
        status: 'waiting_for_user',
        agentPhase: 'planning',
        message: 'choose',
        data: {
          messageId: 'ask-101',
          prompt: 'Pick one',
          schema: { choice: ['A', 'B'] },
          timeoutSec: 60,
        },
        timestamp: '2026-05-26T00:00:05Z',
      });
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, activeTurns } = useAgentSession();
    taskInput.value = 'choose a folder';
    await sendMessage();

    const turn = activeTurns.value[0];
    expect(turn.agent.status).toBe('waiting_for_user');
    expect(turn.agent.pendingAsk?.messageId).toBe('ask-101');
    expect(turn.agent.progress?.step).toBe(1);
    expect(turn.agent.thinking).toContain('Need user choice.');
    expect(turn.agent.partials?.[1].chunks).toEqual([{ name: 'A' }]);
  });

  it('replyToAsk forwards reply via inbox and advances status to running', async () => {
    vi.mocked(agentApi.sendAgentReply).mockResolvedValue({
      inboxMessageId: 'reply-1',
      kind: 'reply',
      acceptedAt: '2026-05-26T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { createSession, replyToAsk } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-e2e',
      role: 'agent',
      content: '',
      status: 'waiting_for_user',
      events: [],
      timestamp: new Date().toISOString(),
      executeJobId: '99',
      pendingAsk: {
        messageId: '101',
        prompt: 'pick',
        schema: { choice: ['A', 'B'] },
        timeoutSec: 60,
        askedAt: new Date().toISOString(),
      },
    };
    session.messages.push(msg);

    await replyToAsk(msg, 'A');

    expect(agentApi.sendAgentReply).toHaveBeenCalledWith('99', '101', 'A');
    expect(msg.status).toBe('running');
    expect(msg.pendingAsk).toBeUndefined();
  });

  it('pause and resume send control.pause then control.resume', async () => {
    vi.mocked(agentApi.pauseAgentJob).mockResolvedValue({
      inboxMessageId: 'pause-1',
      kind: 'control.pause',
      acceptedAt: '2026-05-26T00:00:00Z',
    });
    vi.mocked(agentApi.resumeAgentJob).mockResolvedValue({
      inboxMessageId: 'resume-1',
      kind: 'control.resume',
      acceptedAt: '2026-05-26T00:00:01Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { createSession, pauseTurn, resumeTurn } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-pp',
      role: 'agent',
      content: '',
      status: 'running',
      events: [],
      timestamp: new Date().toISOString(),
      executeJobId: '77',
    };
    session.messages.push(msg);

    await pauseTurn(msg);
    expect(agentApi.pauseAgentJob).toHaveBeenCalledWith('77');
    expect(msg.pauseRequestedAt).toBeTruthy();

    await resumeTurn(msg);
    expect(agentApi.resumeAgentJob).toHaveBeenCalledWith('77');
  });

  it('approve, deny, and skip send inbox control helpers', async () => {
    vi.mocked(agentApi.approveAgentStep).mockResolvedValue({
      inboxMessageId: 'approve-1',
      kind: 'control.approve',
      acceptedAt: '2026-05-26T00:00:00Z',
    });
    vi.mocked(agentApi.denyAgentStep).mockResolvedValue({
      inboxMessageId: 'deny-1',
      kind: 'control.deny',
      acceptedAt: '2026-05-26T00:00:00Z',
    });
    vi.mocked(agentApi.skipAgentStep).mockResolvedValue({
      inboxMessageId: 'skip-1',
      kind: 'control.skip',
      acceptedAt: '2026-05-26T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { createSession, approveStep, denyStep, skipStep } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-controls',
      role: 'agent',
      content: '',
      status: 'running',
      events: [],
      timestamp: new Date().toISOString(),
      planJobId: '66',
    };
    session.messages.push(msg);

    await approveStep(msg);
    await denyStep(msg);
    await skipStep(msg);

    expect(agentApi.approveAgentStep).toHaveBeenCalledWith('66');
    expect(agentApi.denyAgentStep).toHaveBeenCalledWith('66');
    expect(agentApi.skipAgentStep).toHaveBeenCalledWith('66');
  });

  it('reload — sessions persist via localStorage', async () => {
    const { default: useAgentSession, __resetForTests } = await loadComposable();
    const a = useAgentSession();
    a.createSession();
    a.sessions.value[0].title = 'TestRun';
    await nextTick();

    __resetForTests();
    const b = useAgentSession();
    expect(b.sessions.value.length).toBe(1);
    expect(b.sessions.value[0].title).toBe('TestRun');
  });

  it('reload deduplicates multiple empty sessions from localStorage', async () => {
    const now = '2026-05-20T00:00:00Z';
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        { id: 's-1', title: 'New session', messages: [], createdAt: now, updatedAt: now },
        { id: 's-2', title: 'New session', messages: [], createdAt: now, updatedAt: now },
      ]),
    );

    const { default: useAgentSession } = await loadComposable();
    const { sessions, activeSessionId } = useAgentSession();

    expect(sessions.value.length).toBe(1);
    expect(sessions.value[0].id).toBe('s-1');
    expect(activeSessionId.value).toBe('s-1');
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')).toHaveLength(1);
  });
});
