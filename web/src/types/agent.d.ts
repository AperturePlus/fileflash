import type { BackgroundJob } from './file';

export type AgentExecutionPolicy = 'planOnly' | 'confirm' | 'autopilot';
export type AgentActionSideEffect = 'read' | 'write';
export type AgentActionRiskLevel = 'low' | 'medium' | 'high';
export type AgentReasoningEffort = 'adaptive' | 'low' | 'medium' | 'high' | 'xhigh' | 'max';
export type AgentJobPhase =
  | 'planning'
  | 'awaiting_confirm'
  | 'executing'
  | 'awaiting_commit'
  | 'completed'
  | 'failed'
  | 'canceled';

export interface AgentDataPolicy {
  allowFileContent: boolean;
  maxReadBytes: number;
  allowedMimeTypes: string[];
}

export interface AgentHints {
  preferSkillId: string | null;
  maxSteps: number;
  budgetTokens: number;
  reasoningEffort: AgentReasoningEffort;
}

export interface AgentPlanContext {
  rootFolderId: string;
  selectedFileIds: string[];
  selectedFolderIds: string[];
  currentPath: string;
}

export interface PlanAgentRequest {
  input: string;
  context: AgentPlanContext;
  executionPolicy: AgentExecutionPolicy;
  dataPolicy: AgentDataPolicy;
  hints: AgentHints;
}

export interface PlanAgentResponse {
  jobId: string;
  status: string;
  taskType: 'agent.plan';
}

export interface AgentProposedAction {
  step: number;
  tool: string;
  input: Record<string, any>;
  sideEffect: AgentActionSideEffect;
  riskLevel: AgentActionRiskLevel;
  requiresConfirmation: boolean;
  confirmationReason?: string | null;
}

export interface AgentCostEstimate {
  tokens: number;
  toolCalls: number;
  durationSecEstimate: number;
}

export interface AgentChosenSkill {
  id: string;
  name: string;
}

export interface AgentPlanResult {
  planJobId: string;
  planHash: string;
  chosenSkill: AgentChosenSkill | null;
  proposedActions: AgentProposedAction[];
  summary: string;
  requiresConfirmation: boolean;
  costEstimate: AgentCostEstimate;
}

export interface ExecuteAgentRequest {
  planJobId: string;
  planHash: string;
  approval: {
    confirmedBy: string;
    confirmedAt: string;
    highRiskConfirmed?: boolean;
    highRiskConfirmedAt?: string;
  };
}

export interface ExecuteAgentResponse {
  jobId: string;
  status: string;
  taskType: 'agent.execute';
}

export interface CancelAgentResponse {
  jobId: string;
  status: string;
  canceledAt: string;
}

export interface AgentExecutionResult {
  planJobId: string;
  executeJobId: string;
  summary: string;
  answer?: string | null;
  appliedActions: number;
  skippedActions: number;
  warnings: string[];
  finishedAt: string;
}

export type AgentBackgroundJob<T = Record<string, any>> = BackgroundJob<T> & {
  agentPhase?: AgentJobPhase | null;
  cancelRequestedAt?: string | null;
};
