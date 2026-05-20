import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { nextTick } from 'vue';

vi.mock('../api/agent', () => ({
  planAgentTask: vi.fn(),
  executeAgentPlan: vi.fn(),
  cancelAgentJob: vi.fn(),
  getAgentJob: vi.fn(),
}));

vi.mock('../store/user', () => ({
  useUserStore: () => ({ user: { userId: 'u-1' } }),
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

const execResult = {
  planJobId: 'job-1',
  executeJobId: 'job-2',
  summary: 'done',
  appliedActions: 1,
  skippedActions: 0,
  warnings: [],
  finishedAt: '2026-05-20T00:00:00Z',
};

const loadComposable = async () => {
  const mod = await import('./useAgentSession');
  return mod;
};

describe('useAgentSession', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.useFakeTimers();
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

  it('cancel calls cancelAgentJob and clears polling for that turn', async () => {
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
    vi.mocked(agentApi.cancelAgentJob).mockResolvedValue({
      jobId: 'job-1',
      status: 'canceled',
      canceledAt: '2026-05-20T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { taskInput, sendMessage, cancel, activeTurns } = useAgentSession();
    taskInput.value = 'hello';
    await sendMessage();

    const turn = activeTurns.value[0];
    const callsBefore = vi.mocked(agentApi.getAgentJob).mock.calls.length;
    await cancel(turn.agent);
    expect(agentApi.cancelAgentJob).toHaveBeenCalled();
    // Advance time to ensure timer wouldn't fire again
    await vi.advanceTimersByTimeAsync(3000);
    const callsAfter = vi.mocked(agentApi.getAgentJob).mock.calls.length;
    expect(callsAfter).toBe(callsBefore);
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
});
