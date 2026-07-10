import Mock from 'mockjs';
import { createMockId, getCurrentUser, mockJobs } from '../state';
import type {
  AgentBackgroundJob,
  AgentChatMessage,
  AgentChatSessionDetail,
  AgentChatSessionItem,
  AgentExecutionResult,
  AgentInboxMessageRequest,
  AgentInboxMessageResponse,
  AgentPlanResult,
  AgentProposedAction,
  AttachAgentJobsRequest,
  CreateAgentChatSessionRequest,
  ExecuteAgentRequest,
  PatchAgentChatSessionRequest,
  PlanAgentRequest,
} from '../../types/agent';

const nowIso = () => new Date().toISOString();

type MockAgentChatSession = AgentChatSessionItem & {
  userId: string;
  deletedAt: string | null;
};

const mockChatSessions: Record<string, MockAgentChatSession> = {};

const parseUrl = (url: string) => new URL(url, 'http://localhost');

const response = (data: unknown, message = 'OK', code = 200) => ({
  success: true,
  code,
  message,
  data,
  timestamp: nowIso(),
});

const errorResponse = (code: number, message: string) => ({
  success: false,
  code,
  message,
  data: null,
  timestamp: nowIso(),
});

const isTerminal = (status: string) => ['succeeded', 'failed', 'canceled'].includes(status);

const sessionItem = (session: MockAgentChatSession): AgentChatSessionItem => ({
  chatSessionId: session.chatSessionId,
  title: session.title,
  archived: session.archived,
  createdAt: session.createdAt,
  updatedAt: session.updatedAt,
});

const getSession = (chatSessionId: string): MockAgentChatSession | null => {
  const session = mockChatSessions[chatSessionId];
  if (!session || session.deletedAt || session.userId !== getCurrentUser().userId) return null;
  return session;
};

const touchSession = (chatSessionId: string) => {
  const session = mockChatSessions[chatSessionId];
  if (!session || session.deletedAt) return;
  session.updatedAt = nowIso();
};

const createChatSession = (payload: CreateAgentChatSessionRequest = {}): AgentChatSessionItem => {
  const timestamp = nowIso();
  const chatSessionId = createMockId('chat');
  const title = String(payload.title || 'New session').trim() || 'New session';
  const session: MockAgentChatSession = {
    chatSessionId,
    title: title.slice(0, 255),
    archived: false,
    userId: getCurrentUser().userId,
    deletedAt: null,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
  mockChatSessions[chatSessionId] = session;
  return sessionItem(session);
};

const chatSessionJobs = (chatSessionId: string) =>
  Object.values(mockJobs)
    .filter((job) => {
      const agentJob = job as AgentBackgroundJob;
      return agentJob.chatSessionId === chatSessionId && !agentJob.deletedAt;
    })
    .sort((left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime());

const jobStatus = (job: AgentBackgroundJob): AgentChatMessage['status'] => {
  if (job.status === 'pending' || job.status === 'running' || job.status === 'succeeded') return job.status;
  if (job.status === 'failed' || job.status === 'canceled' || job.status === 'paused') return job.status;
  return 'running';
};

const sessionMessages = (chatSessionId: string): AgentChatMessage[] => {
  const jobs = chatSessionJobs(chatSessionId);
  const messages: AgentChatMessage[] = [];
  const planMessages = new Map<string, AgentChatMessage>();

  jobs.forEach((job) => {
    const agentJob = job as AgentBackgroundJob;
    if (agentJob.taskType !== 'agent.plan') return;
    const payload = agentJob.payload as Partial<PlanAgentRequest>;
    const result = agentJob.status === 'succeeded' ? (agentJob.result as AgentPlanResult) : null;
    const userMessage: AgentChatMessage = {
      id: `job-${agentJob.jobId}:user`,
      role: 'user',
      content: String(payload.input || ''),
      status: 'succeeded',
      events: [],
      timestamp: agentJob.createdAt,
    };
    const agentMessage: AgentChatMessage = {
      id: `job-${agentJob.jobId}:agent`,
      role: 'agent',
      content: '',
      status: jobStatus(agentJob),
      planJobId: agentJob.jobId,
      planHash: result?.planHash || null,
      planResult: result as any,
      executeJobId: null,
      executeResult: null,
      events: [],
      errorMessage: agentJob.errorMessage || null,
      timestamp: agentJob.createdAt,
      pendingAsk: null,
    };
    messages.push(userMessage, agentMessage);
    planMessages.set(agentJob.jobId, agentMessage);
  });

  jobs.forEach((job) => {
    const agentJob = job as AgentBackgroundJob;
    if (agentJob.taskType !== 'agent.execute') return;
    const payload = agentJob.payload as Partial<ExecuteAgentRequest>;
    let agentMessage = planMessages.get(String(payload.planJobId || ''));
    if (!agentMessage) {
      agentMessage = {
        id: `job-${agentJob.jobId}:agent`,
        role: 'agent',
        content: '',
        status: jobStatus(agentJob),
        events: [],
        errorMessage: agentJob.errorMessage || null,
        timestamp: agentJob.createdAt,
      };
      messages.push(agentMessage);
    }
    agentMessage.executeJobId = agentJob.jobId;
    agentMessage.status = jobStatus(agentJob);
    if (agentJob.status === 'succeeded') {
      agentMessage.executeResult = agentJob.result as any;
    }
    if (agentJob.errorMessage) {
      agentMessage.errorMessage = agentJob.errorMessage;
    }
  });

  return messages;
};

const sessionDetail = (session: MockAgentChatSession): AgentChatSessionDetail => ({
  ...sessionItem(session),
  messages: sessionMessages(session.chatSessionId),
});

const validateControlStep = (payload: AgentInboxMessageRequest) => {
  if (!['control.skip', 'control.approve', 'control.deny'].includes(payload.kind)) return true;
  const step = Number(payload.metadata?.step);
  return Number.isInteger(step) && step > 0;
};

const extractCountSearch = (input: string) => {
  let text = input.replace(/[?？!！。.,，;；:：]/g, ' ').trim();
  [
    '我上传了多少部',
    '我上传了多少个',
    '我上传了几部',
    '我上传了几个',
    '上传了多少部',
    '上传了多少个',
    '上传了几部',
    '上传了几个',
    '有多少部',
    '有多少个',
    '有几部',
    '有几个',
  ].forEach((phrase) => {
    text = text.split(phrase).join(' ');
  });
  [
    '我',
    '上传',
    '了',
    '有',
    '多少',
    '几个',
    '几部',
    '多少部',
    '多少个',
    '部',
    '个',
    '文件',
    '电影',
    '影片',
    '视频',
    '音频',
    '音乐',
    '图片',
    '照片',
    '文档',
    '压缩包',
  ].forEach((token) => {
    text = text.split(token).join(' ');
  });
  return text.split(/\s+/).filter(Boolean).join(' ') || undefined;
};

const pickPlanActions = (input: string): AgentProposedAction[] => {
  const normalized = input.toLowerCase();
  if (
    normalized.includes('多少') ||
    normalized.includes('几部') ||
    normalized.includes('how many') ||
    normalized.includes('count')
  ) {
    return [
      {
        step: 1,
        tool: 'drive.countFiles',
        sideEffect: 'read',
        riskLevel: 'low',
        requiresConfirmation: false,
        confirmationReason: null,
        input: {
          folderId: 'root',
          recursive: true,
          category:
            normalized.includes('电影') || normalized.includes('视频') || normalized.includes('几部') || normalized.includes('movie')
              ? 'video'
              : undefined,
          search: extractCountSearch(input),
        },
      },
    ];
  }
  if (normalized.includes('delete') || normalized.includes('删除')) {
    return [
      {
        step: 1,
        tool: 'drive.listFolder',
        sideEffect: 'read',
        riskLevel: 'low',
        requiresConfirmation: false,
        confirmationReason: null,
        input: { folderId: 'root' },
      },
      {
        step: 2,
        tool: 'drive.deleteFile',
        sideEffect: 'write',
        riskLevel: 'high',
        requiresConfirmation: true,
        confirmationReason: 'Deleting files is high risk and requires explicit confirmation.',
        input: { fileId: 'file_001' },
      },
    ];
  }
  if (normalized.includes('整理') || normalized.includes('organize')) {
    return [
      {
        step: 1,
        tool: 'drive.listFolder',
        sideEffect: 'read',
        riskLevel: 'low',
        requiresConfirmation: false,
        confirmationReason: null,
        input: { folderId: 'root' },
      },
      {
        step: 2,
        tool: 'drive.createFolder',
        sideEffect: 'write',
        riskLevel: 'medium',
        requiresConfirmation: false,
        confirmationReason: null,
        input: { parentFolderId: 'root', name: 'Organized' },
      },
      {
        step: 3,
        tool: 'drive.moveFile',
        sideEffect: 'write',
        riskLevel: 'medium',
        requiresConfirmation: false,
        confirmationReason: null,
        input: { fileId: 'file_001', targetFolderId: '$step2.folderId' },
      },
    ];
  }

  return [
    {
      step: 1,
      tool: 'drive.resolvePath',
      sideEffect: 'read',
      riskLevel: 'low',
      requiresConfirmation: false,
      confirmationReason: null,
      input: { path: '/My Files' },
    },
    {
      step: 2,
      tool: 'drive.listFolder',
      sideEffect: 'read',
      riskLevel: 'low',
      requiresConfirmation: false,
      confirmationReason: null,
      input: { folderId: '$step1.folderId' },
    },
    {
      step: 3,
      tool: 'drive.renameFile',
      sideEffect: 'write',
      riskLevel: 'medium',
      requiresConfirmation: false,
      confirmationReason: null,
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
    chatSessionId: typeof payload.chatSessionId === 'string' ? payload.chatSessionId : null,
    deletedAt: null,
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

const pauseJob = (job: AgentBackgroundJob) => {
  if (isTerminal(job.status)) return;
  const timestamp = nowIso();
  job.status = 'paused';
  job.agentPhase = 'executing';
  job.updatedAt = timestamp;
};

const resumeJob = (job: AgentBackgroundJob) => {
  if (isTerminal(job.status)) return;
  const timestamp = nowIso();
  job.status = 'running';
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
  const hasHighRiskAction = proposedActions.some((action) => action.riskLevel === 'high' || action.requiresConfirmation);
  const requiresConfirmation = payload.executionPolicy !== 'autopilot' || hasHighRiskAction;
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
    planningEvidence: [
      {
        step: 1,
        tool: 'drive.searchFiles',
        input: {
          folderId: payload.context.rootFolderId || 'root',
          query: payload.input,
          category: 'video',
        },
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
      answer: mockExecutionAnswer(plan),
      appliedActions: plan.proposedActions.length,
      skippedActions: 0,
      warnings: [],
      finishedAt: nowIso(),
    };
    finishJobSuccess(job, result, 'completed');
  }, 1900);
};

const mockExecutionAnswer = (plan: AgentPlanResult) => {
  const countAction = plan.proposedActions.find((action) => action.tool === 'drive.countFiles');
  if (!countAction) return null;
  const search = String(countAction.input.search || '').trim();
  const qualifier = search ? `名称包含“${search}”的` : '';
  if (countAction.input.category === 'video') {
    const total = search === '银翼杀手' ? 2 : 7;
    return `你上传了 ${total} 部${qualifier}电影（按视频文件统计）。`;
  }
  return `你上传了 12 个${qualifier}文件。`;
};

export const setupAgentMocks = () => {
  Mock.mock(/\/api\/v1\/agent\/chat-sessions(?:\?.*)?$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}') as CreateAgentChatSessionRequest;
    return response(createChatSession(payload), 'Agent chat session created');
  });

  Mock.mock(/\/api\/v1\/agent\/chat-sessions(?:\?.*)?$/, 'get', (options) => {
    const url = parseUrl(options.url);
    const page = Math.max(1, Number(url.searchParams.get('page') || 1));
    const perPage = Math.max(1, Number(url.searchParams.get('perPage') || 20));
    const items = Object.values(mockChatSessions)
      .filter((session) => !session.deletedAt && session.userId === getCurrentUser().userId)
      .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
      .map(sessionItem);
    const start = (page - 1) * perPage;
    const sliced = items.slice(start, start + perPage);
    const totalPages = Math.max(1, Math.ceil(items.length / perPage));
    return response(
      {
        items: sliced,
        pagination: {
          totalItems: items.length,
          totalPages,
          perPage,
          currentPage: page,
          hasPrev: page > 1,
          hasNext: page < totalPages,
        },
      },
      'Agent chat sessions loaded',
    );
  });

  Mock.mock(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)$/, 'get', (options) => {
    const chatSessionId = (options.url.match(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)/) || [])[1];
    const session = chatSessionId ? getSession(chatSessionId) : null;
    if (!session) return errorResponse(404, 'Agent chat session not found');
    return response(sessionDetail(session), 'Agent chat session loaded');
  });

  Mock.mock(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)$/, 'patch', (options) => {
    const chatSessionId = (options.url.match(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)/) || [])[1];
    const session = chatSessionId ? getSession(chatSessionId) : null;
    if (!session) return errorResponse(404, 'Agent chat session not found');
    const payload = JSON.parse(options.body || '{}') as PatchAgentChatSessionRequest;
    if (typeof payload.title === 'string') {
      const title = payload.title.trim();
      if (title) session.title = title.slice(0, 255);
    }
    if (typeof payload.archived === 'boolean') {
      session.archived = payload.archived;
    }
    session.updatedAt = nowIso();
    return response(sessionItem(session), 'Agent chat session updated');
  });

  Mock.mock(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)$/, 'delete', (options) => {
    const chatSessionId = (options.url.match(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)/) || [])[1];
    const session = chatSessionId ? getSession(chatSessionId) : null;
    if (!session) return errorResponse(404, 'Agent chat session not found');
    const timestamp = nowIso();
    session.deletedAt = timestamp;
    session.updatedAt = timestamp;
    chatSessionJobs(chatSessionId).forEach((job) => {
      const agentJob = job as AgentBackgroundJob;
      agentJob.deletedAt = timestamp;
      agentJob.updatedAt = timestamp;
      if (!isTerminal(agentJob.status)) {
        agentJob.cancelRequestedAt = agentJob.cancelRequestedAt || timestamp;
        finishJobCanceled(agentJob);
      }
    });
    return response(sessionItem(session), 'Agent chat session deleted');
  });

  Mock.mock(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)\/attach-jobs$/, 'post', (options) => {
    const chatSessionId = (options.url.match(/\/api\/v1\/agent\/chat-sessions\/([^/?]+)\/attach-jobs/) || [])[1];
    const session = chatSessionId ? getSession(chatSessionId) : null;
    if (!session) return errorResponse(404, 'Agent chat session not found');
    const payload = JSON.parse(options.body || '{}') as AttachAgentJobsRequest;
    let attachedCount = 0;
    (payload.jobIds || []).forEach((jobId) => {
      const job = getJobById(String(jobId));
      if (!job || job.requestedBy !== getCurrentUser().userId || job.deletedAt) return;
      if (job.chatSessionId && job.chatSessionId !== chatSessionId) return;
      if (job.chatSessionId !== chatSessionId) {
        job.chatSessionId = chatSessionId;
        job.updatedAt = nowIso();
        attachedCount += 1;
      }
    });
    touchSession(chatSessionId);
    return response({ attachedCount }, 'Agent jobs attached');
  });

  Mock.mock(/\/api\/v1\/agent\/plan$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}') as PlanAgentRequest;
    const input = String(payload?.input || '').trim();
    if (!input) {
      return errorResponse(400, 'input is required');
    }
    if (!payload.chatSessionId || !getSession(payload.chatSessionId)) {
      return errorResponse(404, 'Agent chat session not found');
    }

    const job = createAgentJob('agent.plan', payload as Record<string, any>);
    touchSession(payload.chatSessionId);
    schedulePlanLifecycle(job, payload);

    return response(
      {
        jobId: job.jobId,
        status: job.status,
        taskType: 'agent.plan',
      },
      'Plan job created',
    );
  });

  Mock.mock(/\/api\/v1\/agent\/execute$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}') as ExecuteAgentRequest;
    const planJobId = String(payload?.planJobId || '');
    const planHash = String(payload?.planHash || '');
    if (!payload.chatSessionId || !getSession(payload.chatSessionId)) {
      return errorResponse(404, 'Agent chat session not found');
    }
    if (!planJobId || !planHash) {
      return errorResponse(400, 'planJobId and planHash are required');
    }

    const planJob = getJobById(planJobId);
    if (
      !planJob ||
      planJob.taskType !== 'agent.plan' ||
      planJob.status !== 'succeeded' ||
      planJob.chatSessionId !== payload.chatSessionId ||
      planJob.deletedAt
    ) {
      return errorResponse(404, 'Plan job not found');
    }

    const planResult = planResultByJobId.get(planJobId);
    if (!planResult || planResult.planHash !== planHash) {
      return errorResponse(409, 'planHash mismatch');
    }
    const highRiskActions = planResult.proposedActions.filter((action) => action.riskLevel === 'high' || action.requiresConfirmation);
    if (highRiskActions.length && !payload.approval?.highRiskConfirmed) {
      return {
        success: false,
        code: 409,
        message: 'High-risk action requires confirmation',
        data: { highRiskActions },
      };
    }

    const executeJob = createAgentJob('agent.execute', {
      chatSessionId: payload.chatSessionId,
      planJobId,
      planHash,
      approval: payload.approval || null,
    });
    touchSession(payload.chatSessionId);

    const sourceInput = String((planJob.payload as PlanAgentRequest)?.input || '');
    scheduleExecuteLifecycle(executeJob, planResult, shouldSimulateFailure(sourceInput));

    return response(
      {
        jobId: executeJob.jobId,
        status: executeJob.status,
        taskType: 'agent.execute',
      },
      'Execute job created',
    );
  });

  Mock.mock(/\/api\/v1\/agent\/jobs\/([^/?]+)\/messages$/, 'post', (options) => {
    const jobId = (options.url.match(/\/api\/v1\/agent\/jobs\/([^/?]+)\/messages/) || [])[1];
    const job = jobId ? getJobById(jobId) : null;
    if (!job) {
      return errorResponse(404, 'Job not found');
    }

    const payload = JSON.parse(options.body || '{}') as AgentInboxMessageRequest;
    if (!validateControlStep(payload)) {
      return errorResponse(422, `${payload.kind} requires metadata.step`);
    }
    if (payload.kind === 'control.cancel') {
      finishJobCanceled(job);
    } else if (payload.kind === 'control.pause') {
      pauseJob(job);
    } else if (payload.kind === 'control.resume') {
      resumeJob(job);
    }

    const accepted: AgentInboxMessageResponse = {
      inboxMessageId: createMockId('inbox'),
      kind: payload.kind,
      acceptedAt: nowIso(),
    };

    return response(accepted, 'Agent message accepted');
  });
};
