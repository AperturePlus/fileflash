import Mock from 'mockjs';
import { createMockId, getCurrentUser, mockJobs } from '../state';
import type {
  AgentBackgroundJob,
  AgentExecutionResult,
  AgentPlanResult,
  AgentProposedAction,
  ExecuteAgentRequest,
  PlanAgentRequest,
} from '../../types/agent';

const nowIso = () => new Date().toISOString();

const isTerminal = (status: string) => ['succeeded', 'failed', 'canceled'].includes(status);

const pickPlanActions = (input: string): AgentProposedAction[] => {
  const normalized = input.toLowerCase();
  if (normalized.includes('整理') || normalized.includes('organize')) {
    return [
      {
        step: 1,
        tool: 'drive.listFolder',
        sideEffect: 'read',
        input: { folderId: 'root' },
      },
      {
        step: 2,
        tool: 'drive.createFolder',
        sideEffect: 'write',
        input: { parentFolderId: 'root', name: 'Organized' },
      },
      {
        step: 3,
        tool: 'drive.moveFile',
        sideEffect: 'write',
        input: { fileId: 'file_001', targetFolderId: '$step2.folderId' },
      },
    ];
  }

  return [
    {
      step: 1,
      tool: 'drive.resolvePath',
      sideEffect: 'read',
      input: { path: '/My Files' },
    },
    {
      step: 2,
      tool: 'drive.listFolder',
      sideEffect: 'read',
      input: { folderId: '$step1.folderId' },
    },
    {
      step: 3,
      tool: 'drive.renameFile',
      sideEffect: 'write',
      input: { fileId: 'file_002', fileName: 'renamed-by-agent.txt' },
    },
  ];
};

const createAgentJob = (taskType: 'agent.plan' | 'agent.execute', payload: Record<string, any>) => {
  const timestamp = nowIso();
  const jobId = createMockId('job');
  const requestedBy = getCurrentUser().userId;
  const job: AgentBackgroundJob = {
    jobId,
    taskType,
    status: 'pending',
    agentPhase: taskType === 'agent.plan' ? 'planning' : 'executing',
    priority: 100,
    payload,
    result: {},
    errorMessage: null,
    attempt: 0,
    maxAttempts: 3,
    scheduledAt: timestamp,
    startedAt: null,
    finishedAt: null,
    traceId: `trace-${jobId}`,
    idempotencyKey: null,
    cancelRequestedAt: null,
    requestedBy,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
  mockJobs[jobId] = job as any;
  return job;
};

const startJob = (job: AgentBackgroundJob, phase: AgentBackgroundJob['agentPhase']) => {
  if (isTerminal(job.status)) return;
  const timestamp = nowIso();
  job.status = 'running';
  job.agentPhase = phase || job.agentPhase;
  job.startedAt = job.startedAt || timestamp;
  job.updatedAt = timestamp;
};

const finishJobSuccess = (job: AgentBackgroundJob, result: Record<string, any>, phase: AgentBackgroundJob['agentPhase'] = 'completed') => {
  if (isTerminal(job.status)) return;
  const timestamp = nowIso();
  job.status = 'succeeded';
  job.agentPhase = phase;
  job.result = result;
  job.finishedAt = timestamp;
  job.updatedAt = timestamp;
  job.errorMessage = null;
};

const finishJobFailed = (job: AgentBackgroundJob, message: string) => {
  if (isTerminal(job.status)) return;
  const timestamp = nowIso();
  job.status = 'failed';
  job.agentPhase = 'failed';
  job.errorMessage = message;
  job.finishedAt = timestamp;
  job.updatedAt = timestamp;
};

const finishJobCanceled = (job: AgentBackgroundJob) => {
  if (isTerminal(job.status)) return;
  const timestamp = nowIso();
  job.status = 'canceled';
  job.agentPhase = 'canceled';
  job.cancelRequestedAt = timestamp;
  job.finishedAt = timestamp;
  job.updatedAt = timestamp;
};

const getJobById = (jobId: string) => (mockJobs[jobId] || null) as AgentBackgroundJob | null;

const shouldSimulateFailure = (input: string) => {
  const normalized = input.toLowerCase();
  return normalized.includes('fail') || normalized.includes('错误') || normalized.includes('失败');
};

const planResultByJobId = new Map<string, AgentPlanResult>();

const schedulePlanLifecycle = (job: AgentBackgroundJob, payload: PlanAgentRequest) => {
  const failure = shouldSimulateFailure(payload.input);
  const proposedActions = pickPlanActions(payload.input);
  const requiresConfirmation = payload.executionPolicy !== 'autopilot';
  const planHash = `sha256:${Mock.Random.string('hex', 16)}`;
  const result: AgentPlanResult = {
    planJobId: job.jobId,
    planHash,
    chosenSkill: {
      id: payload.hints.preferSkillId || 'builtin:organizeByType',
      name: payload.hints.preferSkillId ? 'Preferred Skill' : 'Organize By Type',
    },
    proposedActions,
    summary: `Cloud Agent generated ${proposedActions.length} actions for: ${payload.input}`,
    requiresConfirmation,
    costEstimate: {
      tokens: Math.max(1600, Math.floor(payload.hints.budgetTokens * 0.18)),
      toolCalls: proposedActions.length,
      durationSecEstimate: proposedActions.length * 4,
    },
  };

  setTimeout(() => {
    startJob(job, 'planning');
  }, 500);

  setTimeout(() => {
    if (failure) {
      finishJobFailed(job, 'Agent planning failed in mock mode. Try a different prompt.');
      return;
    }
    finishJobSuccess(job, result, requiresConfirmation ? 'awaiting_confirm' : 'completed');
    planResultByJobId.set(job.jobId, result);
  }, 1700);
};

const scheduleExecuteLifecycle = (job: AgentBackgroundJob, plan: AgentPlanResult, shouldFail: boolean) => {
  setTimeout(() => {
    startJob(job, 'executing');
  }, 450);

  setTimeout(() => {
    if (job.cancelRequestedAt) {
      finishJobCanceled(job);
      return;
    }
    if (shouldFail) {
      finishJobFailed(job, 'Agent execution failed in mock mode. You can retry with a safer plan.');
      return;
    }

    const result: AgentExecutionResult = {
      planJobId: plan.planJobId,
      executeJobId: job.jobId,
      summary: `Execution completed with ${plan.proposedActions.length} planned actions.`,
      appliedActions: plan.proposedActions.length,
      skippedActions: 0,
      warnings: [],
      finishedAt: nowIso(),
    };
    finishJobSuccess(job, result, 'completed');
  }, 1900);
};

export const setupAgentMocks = () => {
  Mock.mock(/\/api\/v1\/agent\/plan$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}') as PlanAgentRequest;
    const input = String(payload?.input || '').trim();
    if (!input) {
      return {
        success: false,
        code: 400,
        message: 'input is required',
        data: null,
      };
    }

    const job = createAgentJob('agent.plan', payload as Record<string, any>);
    schedulePlanLifecycle(job, payload);

    return {
      success: true,
      code: 200,
      message: 'Plan job created',
      data: {
        jobId: job.jobId,
        status: job.status,
        taskType: 'agent.plan',
      },
    };
  });

  Mock.mock(/\/api\/v1\/agent\/execute$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}') as ExecuteAgentRequest;
    const planJobId = String(payload?.planJobId || '');
    const planHash = String(payload?.planHash || '');
    if (!planJobId || !planHash) {
      return {
        success: false,
        code: 400,
        message: 'planJobId and planHash are required',
        data: null,
      };
    }

    const planJob = getJobById(planJobId);
    if (!planJob || planJob.taskType !== 'agent.plan' || planJob.status !== 'succeeded') {
      return {
        success: false,
        code: 404,
        message: 'Plan job not found',
        data: null,
      };
    }

    const planResult = planResultByJobId.get(planJobId);
    if (!planResult || planResult.planHash !== planHash) {
      return {
        success: false,
        code: 409,
        message: 'planHash mismatch',
        data: null,
      };
    }

    const executeJob = createAgentJob('agent.execute', {
      planJobId,
      planHash,
      approval: payload.approval || null,
    });

    const sourceInput = String((planJob.payload as PlanAgentRequest)?.input || '');
    scheduleExecuteLifecycle(executeJob, planResult, shouldSimulateFailure(sourceInput));

    return {
      success: true,
      code: 200,
      message: 'Execute job created',
      data: {
        jobId: executeJob.jobId,
        status: executeJob.status,
        taskType: 'agent.execute',
      },
    };
  });

  Mock.mock(/\/api\/v1\/agent\/cancel\/([^/?]+)$/, 'post', (options) => {
    const jobId = (options.url.match(/\/api\/v1\/agent\/cancel\/([^/?]+)/) || [])[1];
    const job = jobId ? getJobById(jobId) : null;
    if (!job) {
      return {
        success: false,
        code: 404,
        message: 'Job not found',
        data: null,
      };
    }

    if (!isTerminal(job.status)) {
      finishJobCanceled(job);
    }

    return {
      success: true,
      code: 200,
      message: 'Job canceled',
      data: {
        jobId: job.jobId,
        status: job.status,
        canceledAt: job.cancelRequestedAt || nowIso(),
      },
    };
  });
};
