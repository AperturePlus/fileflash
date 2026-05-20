import type { PaginatedData } from './base';

export interface RegistrationEmailDomainRuleItem {
  ruleId: string;
  name: string;
  pattern: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ListRegistrationEmailDomainRulesRequest {
  page?: number;
  perPage?: number;
  queryText?: string;
  enabled?: boolean;
}

export interface CreateRegistrationEmailDomainRuleRequest {
  name: string;
  pattern: string;
  enabled: boolean;
}

export interface UpdateRegistrationEmailDomainRuleRequest {
  name?: string;
  pattern?: string;
  enabled?: boolean;
}

export type RegistrationEmailDomainRulesList = PaginatedData<RegistrationEmailDomainRuleItem>;

