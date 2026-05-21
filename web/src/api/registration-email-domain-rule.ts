import http from '../utils/http';
import type {
  CreateRegistrationEmailDomainRuleRequest,
  ListRegistrationEmailDomainRulesRequest,
  RegistrationEmailDomainRuleItem,
  RegistrationEmailDomainRulesList,
  UpdateRegistrationEmailDomainRuleRequest,
} from '../types/registration-email-domain-rule';

const BASE = '/admin/registration-email-domain-rules';

export const getRegistrationEmailDomainRules = (params: ListRegistrationEmailDomainRulesRequest) => {
  return http.get<RegistrationEmailDomainRulesList>(BASE, params);
};

export const createRegistrationEmailDomainRule = (data: CreateRegistrationEmailDomainRuleRequest) => {
  return http.post<RegistrationEmailDomainRuleItem>(BASE, data);
};

export const updateRegistrationEmailDomainRule = (
  ruleId: string,
  data: UpdateRegistrationEmailDomainRuleRequest,
) => {
  return http.patch<RegistrationEmailDomainRuleItem>(`${BASE}/${ruleId}`, data);
};

export const deleteRegistrationEmailDomainRule = (ruleId: string) => {
  return http.delete<{ ruleId: string; deletedAt: string }>(`${BASE}/${ruleId}`);
};

