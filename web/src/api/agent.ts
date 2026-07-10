import http from '../utils/http';
import { useUserStore } from '../store/user';
import type {
  AgentChatSessionDetail,
  AgentChatSessionItem,
  AgentChatSessionList,
  AgentBackgroundJob,
  AttachAgentJobsRequest,
  AttachAgentJobsResponse,
  CreateAgentChatSessionRequest,
  AgentInboxMessageRequest,
  AgentInboxMessageResponse,
  AgentJobEvent,
  ExecuteAgentRequest,
  ExecuteAgentResponse,
  PatchAgentChatSessionRequest,
  PlanAgentRequest,
  PlanAgentResponse,
} from '../types/agent';

export const createAgentChatSession = (data: CreateAgentChatSessionRequest = {}) => {
  return http.post<AgentChatSessionItem>('/agent/chat-sessions', data);
};

export const listAgentChatSessions = (params: { page?: number; perPage?: number } = {}) => {
  return http.get<AgentChatSessionList>('/agent/chat-sessions', params);
};

export const getAgentChatSession = (chatSessionId: string) => {
  return http.get<AgentChatSessionDetail>(
    `/agent/chat-sessions/${encodeURIComponent(chatSessionId)}`,
  );
};

export const patchAgentChatSession = (
  chatSessionId: string,
  data: PatchAgentChatSessionRequest,
) => {
  return http.patch<AgentChatSessionItem>(
    `/agent/chat-sessions/${encodeURIComponent(chatSessionId)}`,
    data,
  );
};

export const deleteAgentChatSession = (chatSessionId: string) => {
  return http.delete<AgentChatSessionItem>(
    `/agent/chat-sessions/${encodeURIComponent(chatSessionId)}`,
  );
};

export const attachAgentChatSessionJobs = (
  chatSessionId: string,
  data: AttachAgentJobsRequest,
) => {
  return http.post<AttachAgentJobsResponse>(
    `/agent/chat-sessions/${encodeURIComponent(chatSessionId)}/attach-jobs`,
    data,
  );
};

export const planAgentTask = (data: PlanAgentRequest) => {
  return http.post<PlanAgentResponse>('/agent/plan', data);
};

export const executeAgentPlan = (data: ExecuteAgentRequest) => {
  return http.post<ExecuteAgentResponse>('/agent/execute', data);
};

export const sendAgentMessage = (
  jobId: string,
  body: AgentInboxMessageRequest,
) => {
  return http.post<AgentInboxMessageResponse>(
    `/agent/jobs/${encodeURIComponent(jobId)}/messages`,
    body,
  );
};

export const sendAgentReply = (
  jobId: string,
  replyTo: string,
  value: unknown,
) => sendAgentMessage(jobId, { kind: 'reply', replyTo, value });

export const pauseAgentJob = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.pause' });

export const resumeAgentJob = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.resume' });

export const approveAgentStep = (jobId: string, step: number) =>
  sendAgentMessage(jobId, { kind: 'control.approve', metadata: { step } });

export const denyAgentStep = (jobId: string, step: number, reason?: string) =>
  sendAgentMessage(jobId, { kind: 'control.deny', metadata: { step, ...(reason ? { reason } : {}) } });

export const skipAgentStep = (jobId: string, step: number) =>
  sendAgentMessage(jobId, { kind: 'control.skip', metadata: { step } });

export const cancelAgentTurn = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.cancel' });

export const getAgentJob = <T = Record<string, any>>(jobId: string) => {
  return http.get<AgentBackgroundJob<T>>(`/jobs/${encodeURIComponent(jobId)}`);
};

export interface AgentJobEventHandlers {
  onEvent?: (event: AgentJobEvent) => void;
}

export const createAgentSseParser = (onEvent: (event: AgentJobEvent) => void) => {
  let buffer = '';

  const parseBlock = (block: string) => {
    const dataLines = block
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart());
    if (!dataLines.length) return;
    const raw = dataLines.join('\n').trim();
    if (!raw) return;
    onEvent(JSON.parse(raw) as AgentJobEvent);
  };

  const feed = (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, '\n');
    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      parseBlock(block);
      boundary = buffer.indexOf('\n\n');
    }
  };

  const flush = () => {
    if (!buffer.trim()) return;
    parseBlock(buffer);
    buffer = '';
  };

  return { feed, flush };
};

export const streamAgentJobEvents = async (
  jobId: string,
  handlers: AgentJobEventHandlers = {},
  signal?: AbortSignal,
) => {
  const userStore = useUserStore();
  const baseUrl = (import.meta.env.VITE_BASE_URL || '/api/v1').replace(/\/$/, '');
  const headers: Record<string, string> = { Accept: 'text/event-stream' };
  if (userStore.token) {
    headers.Authorization = `Bearer ${userStore.token}`;
  }
  const response = await fetch(`${baseUrl}/agent/jobs/${encodeURIComponent(jobId)}/events`, {
    method: 'GET',
    headers,
    credentials: 'include',
    signal,
  });
  if (!response.ok) {
    throw new Error(`Agent event stream failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error('Agent event stream is not readable');
  }

  const parser = createAgentSseParser((event) => handlers.onEvent?.(event));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    parser.feed(decoder.decode(value, { stream: true }));
  }
  parser.feed(decoder.decode());
  parser.flush();
};
