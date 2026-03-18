import http from '../utils/http';
import type { LogsList, GetLogsRequest } from '../types/log';

export const getLogs = (params: GetLogsRequest) => {
  return http.get<LogsList>('/logs', params);
}; 