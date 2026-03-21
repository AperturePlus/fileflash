import http from '../utils/http';
import type { SystemHealth, RateLimitStatus } from '../types/system';

export const getSystemHealth = () => {
  return http.get<SystemHealth>('/admin/system/health');
};

export const getRateLimitStatus = () => {
  return http.get<RateLimitStatus>('/admin/system/rate-limit');
};
