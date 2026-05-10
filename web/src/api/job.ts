import http from '../utils/http';
import type { BackgroundJob } from '../types/file';

export const getJob = <T = any>(jobId: string) => {
  return http.get<BackgroundJob<T>>(`/jobs/${jobId}`);
};

