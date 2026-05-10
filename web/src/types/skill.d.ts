import type { PaginatedData } from './base';

export type AgentSkillVisibility = 'global' | 'private';
export type AgentSkillListVisibility = 'all' | AgentSkillVisibility;
export type ImportAgentSkillMode = 'upsert' | 'insertOnly';

export interface AgentSkillItem {
  skillId: string;
  skillKey: string;
  name: string;
  description: string;
  triggersText?: string | null;
  toolWhitelist: string[];
  planTemplate: Record<string, any>;
  inputsSchema: Record<string, any>;
  outputsSchema: Record<string, any>;
  visibility: AgentSkillVisibility;
  ownerUserId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ListAgentSkillsRequest {
  page?: number;
  perPage?: number;
  visibility?: AgentSkillListVisibility;
  queryText?: string;
}

export type AgentSkillsList = PaginatedData<AgentSkillItem>;

export interface CreateAgentSkillRequest {
  name: string;
  description: string;
  triggersText?: string | null;
  toolWhitelist?: string[];
  planTemplate?: Record<string, any>;
  inputsSchema?: Record<string, any>;
  outputsSchema?: Record<string, any>;
}

export interface UpdateAgentSkillRequest {
  name?: string | null;
  description?: string | null;
  triggersText?: string | null;
  toolWhitelist?: string[];
  planTemplate?: Record<string, any>;
  inputsSchema?: Record<string, any>;
  outputsSchema?: Record<string, any>;
}

export interface DeleteAgentSkillResponse {
  skillKey: string;
  deletedAt: string;
}

export interface ImportAgentSkillItem {
  skillKey: string;
  name: string;
  description: string;
  triggersText?: string | null;
  toolWhitelist?: string[];
  planTemplate?: Record<string, any>;
  inputsSchema?: Record<string, any>;
  outputsSchema?: Record<string, any>;
}

export interface ImportAgentSkillsRequest {
  mode?: ImportAgentSkillMode;
  items: ImportAgentSkillItem[];
}

export interface ImportAgentSkillResult {
  skillKey: string;
  action: 'created' | 'updated';
}

export interface ImportAgentSkillsResponse {
  results: ImportAgentSkillResult[];
}

