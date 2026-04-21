import Mock from 'mockjs';
import { mockJobs } from '../state';

export const setupJobsMocks = () => {
  Mock.mock(/\/api\/v1\/jobs\/([^/?]+)(?:\?.*)?$/, 'get', (options) => {
    const jobId = (options.url.match(/\/api\/v1\/jobs\/([^/?]+)/) || [])[1];
    const job = jobId ? mockJobs[jobId] : undefined;

    if (!job) {
      return {
        success: false,
        code: 404,
        message: 'Job not found',
        data: null,
      };
    }

    return {
      success: true,
      code: 200,
      data: job,
    };
  });
};

