import http from '../utils/http';
import type { LogsList, GetLogsRequest, GetAdminLogsRequest } from '../types/log';

export const getLogs = (params: GetLogsRequest) => {
  return http.get<LogsList>('/logs', params);
};

export const getAdminLogs = (params: GetAdminLogsRequest) => {
  return http.get<LogsList>('/admin/logs', params);
};
