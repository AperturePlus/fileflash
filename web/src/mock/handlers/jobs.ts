import Mock from 'mockjs';
import { mockJobs } from '../state';

export const setupJobsMocks = () => {
  mockJobs['job_transcode_demo'] = {
    jobId: 'job_transcode_demo',
    taskType: 'task.transcode',
    status: 'succeeded',
    priority: 100,
    payload: {
      sourceBucketName: 'fileflash',
      sourceObjectKey: 'objects/u1/sample-video',
      sourceObjectId: 1001,
      outputBucketName: 'fileflash',
      outputObjectKey: 'optimized/transcode/v1/object-1001/sample-mp4-v1.mp4',
      fileId: 1001,
    },
    result: {
      mediaType: 'video',
      optimizedMimeType: 'video/mp4',
      transcodeProfile: {
        version: 'mp4-v1',
        container: 'mp4',
        videoCodec: 'h264',
        audioCodec: 'aac',
      },
      metadata: {
        durationMs: 12000,
        width: 1280,
        height: 720,
        bitrate: 1200000,
        sampleRate: 44100,
      },
    },
    errorMessage: null,
    attempt: 0,
    maxAttempts: 5,
    scheduledAt: new Date().toISOString(),
    startedAt: new Date().toISOString(),
    finishedAt: new Date().toISOString(),
    traceId: 'mock-job-transcode',
    idempotencyKey: 'object:1001:transcode:mp4-v1',
    requestedBy: '1',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

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

