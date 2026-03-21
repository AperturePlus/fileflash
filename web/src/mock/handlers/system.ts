import Mock from 'mockjs';

export const setupSystemMocks = () => {
  Mock.mock(/\/api\/v1\/admin\/system\/health$/, 'get', () => {
    return {
      success: true,
      code: 200,
      data: {
        platformTargets: ['web', 'electron'],
        maxConcurrentUploads: 8,
        activeUploadSessions: Mock.Random.integer(1, 4),
        virusScanEnabled: true,
        thumbnailGenerationEnabled: true,
        registrationMailEnabled: true,
        hashComputationEnabled: true,
        lastUpdatedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/system\/rate-limit$/, 'get', () => {
    const rules = [
      {
        ruleId: 'auth-login-ip',
        scope: 'auth:login:ip',
        windowSeconds: 60,
        limit: 20,
        currentUsage: Mock.Random.integer(3, 16),
        blockedRequests: Mock.Random.integer(0, 2),
      },
      {
        ruleId: 'upload-user',
        scope: 'upload:user',
        windowSeconds: 60,
        limit: 120,
        currentUsage: Mock.Random.integer(20, 90),
        blockedRequests: Mock.Random.integer(0, 5),
      },
      {
        ruleId: 'share-access-ip',
        scope: 'share:access:ip',
        windowSeconds: 60,
        limit: 60,
        currentUsage: Mock.Random.integer(8, 35),
        blockedRequests: Mock.Random.integer(0, 3),
      },
    ];

    return {
      success: true,
      code: 200,
      data: {
        rules,
        evaluatedAt: new Date().toISOString(),
      },
    };
  });
};
