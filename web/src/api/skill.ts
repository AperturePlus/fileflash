import http from '../utils/http';
import type {
  AgentSkillItem,
  AgentSkillsList,
  CreateAgentSkillRequest,
  DeleteAgentSkillResponse,
  ImportAgentSkillsRequest,
  ImportAgentSkillsResponse,
  ListAgentSkillsRequest,
  UpdateAgentSkillRequest,
} from '../types/skill';

const encodeKey = (skillKey: string) => encodeURIComponent(skillKey);

export const listAgentSkills = (params: ListAgentSkillsRequest) => {
  return http.get<AgentSkillsList>('/agent/skills', params);
};

export const getAgentSkill = (skillKey: string) => {
  return http.get<AgentSkillItem>(`/agent/skills/${encodeKey(skillKey)}`);
};

export const createCustomSkill = (data: CreateAgentSkillRequest) => {
  return http.post<AgentSkillItem>('/agent/skills', data);
};

export const updateCustomSkill = (skillKey: string, data: UpdateAgentSkillRequest) => {
  return http.patch<AgentSkillItem>(`/agent/skills/${encodeKey(skillKey)}`, data);
};

export const deleteCustomSkill = (skillKey: string) => {
  return http.delete<DeleteAgentSkillResponse>(`/agent/skills/${encodeKey(skillKey)}`);
};

export const importGlobalSkills = (data: ImportAgentSkillsRequest) => {
  return http.post<ImportAgentSkillsResponse>('/agent/skills/import', data);
};

