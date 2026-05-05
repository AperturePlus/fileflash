import http from '../utils/http';
import type {
  AgentBackgroundJob,
  CancelAgentResponse,
  ExecuteAgentRequest,
  ExecuteAgentResponse,
  PlanAgentRequest,
  PlanAgentResponse,
} from '../types/agent';

export const planAgentTask = (data: PlanAgentRequest) => {
  return http.post<PlanAgentResponse>('/agent/plan', data);
};

export const executeAgentPlan = (data: ExecuteAgentRequest) => {
  return http.post<ExecuteAgentResponse>('/agent/execute', data);
};

export const cancelAgentJob = (jobId: string) => {
  return http.post<CancelAgentResponse>(`/agent/cancel/${encodeURIComponent(jobId)}`);
};

export const getAgentJob = <T = Record<string, any>>(jobId: string) => {
  return http.get<AgentBackgroundJob<T>>(`/jobs/${encodeURIComponent(jobId)}`);
};
