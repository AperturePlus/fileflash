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
export type AgentJobEventType =
  | 'job.queued'
  | 'job.running'
  | 'plan.ready'
  | 'tool.started'
  | 'tool.succeeded'
  | 'tool.failed'
  | 'tool.partial'
  | 'agent.thinking'
  | 'agent.progress'
  | 'agent.ask'
  | 'agent.paused'
  | 'agent.resumed'
  | 'job.succeeded'
  | 'job.failed'
  | 'job.canceled';

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

export interface AgentJobEvent {
  id: string;
  jobId: string;
  taskType: string;
  type: AgentJobEventType;
  status: string;
  agentPhase?: AgentJobPhase | string | null;
  message: string;
  data: Record<string, any>;
  timestamp: string;
}

export type AgentBackgroundJob<T = Record<string, any>> = BackgroundJob<T> & {
  agentPhase?: AgentJobPhase | null;
  cancelRequestedAt?: string | null;
};

// ----------------- Inbox (upstream channel) -----------------

export type AgentInboxMessageKind =
  | 'reply'
  | 'control.pause'
  | 'control.resume'
  | 'control.approve'
  | 'control.deny'
  | 'control.skip'
  | 'control.cancel';

export interface AgentInboxMessageRequest {
  kind: AgentInboxMessageKind;
  replyTo?: string;
  value?: unknown;
  metadata?: Record<string, unknown>;
}

export interface AgentInboxMessageResponse {
  inboxMessageId: string;
  kind: AgentInboxMessageKind;
  acceptedAt: string;
}

// ----------------- New event payloads -----------------

export interface AgentAskPayload {
  messageId: string;
  prompt: string;
  schema: Record<string, unknown>;
  timeoutSec: number;
}

export interface AgentProgressPayload {
  step: number;
  total: number;
  message?: string;
  percent?: number;
}

export interface AgentThinkingPayload {
  text: string;
}

export interface AgentToolPartialPayload {
  step: number;
  tool: string;
  chunk: unknown;
}
