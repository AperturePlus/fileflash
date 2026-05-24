import http from '../utils/http';
import type { LogsList, GetAdminLogsRequest } from '../types/log';

export const getAdminLogs = (params: GetAdminLogsRequest) => {
  return http.get<LogsList>('/admin/logs', params);
};
