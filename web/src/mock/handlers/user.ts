import Mock from 'mockjs';
import { addLog, addNotification, getCurrentUser, mockLogs, mockUsers, paginate } from '../state';

const profileGroups = [
  {
    groupId: 'group1',
    groupName: 'Developers',
    role: 'admin' as const,
  },
  {
    groupId: 'group2',
    groupName: 'Product Team',
    role: 'member' as const,
  },
];

export const setupUserMocks = () => {
  Mock.mock(/\/api\/v1\/users(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const search = (url.searchParams.get('search') || '').toLowerCase();
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);

    const filtered = mockUsers.filter((user) => {
      if (!search) return true;
      return user.username.toLowerCase().includes(search) || user.email.toLowerCase().includes(search);
    }).map((user) => ({
      userId: user.userId,
      username: user.username,
      email: user.email,
      storageLimit: user.storageLimit,
      storageUsed: user.storageUsed,
      emailVerified: user.emailVerified,
      emailVerifiedAt: user.emailVerifiedAt,
      createdAt: user.createdAt,
      role: user.role,
      status: user.status,
    }));

    return {
      success: true,
      code: 200,
      data: paginate(filtered, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/admin\/users(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);

    const users = mockUsers.map((user) => ({
      userId: user.userId,
      username: user.username,
      email: user.email,
      storageLimit: user.storageLimit,
      storageUsed: user.storageUsed,
      emailVerified: user.emailVerified,
      emailVerifiedAt: user.emailVerifiedAt,
      createdAt: user.createdAt,
      role: user.role,
      status: user.status,
      lastActiveAt: new Date(Date.now() - Mock.Random.integer(1, 72) * 3600000).toISOString(),
    }));

    return {
      success: true,
      code: 200,
      data: paginate(users, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/admin\/users\/([^/]+)\/status$/, 'patch', (options) => {
    const userId = (options.url.match(/\/api\/v1\/admin\/users\/([^/]+)\/status/) || [])[1];
    const { status } = JSON.parse(options.body || '{}');

    const target = mockUsers.find((user) => user.userId === userId);
    if (!target) {
      return {
        success: false,
        code: 404,
        message: 'User not found',
        data: null,
      };
    }

    target.status = status;
    addLog('admin_user_status_update', { userId, status });

    return {
      success: true,
      code: 200,
      data: {
        userId,
        status,
        updatedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/violations(?:\?.*)?$/, 'get', () => {
    const items = [
      {
        id: 'vio_1',
        fileId: 'file8',
        fileName: 'intro.mp3',
        type: 'copyright',
        level: 'medium',
        reportedAt: new Date(Date.now() - 36 * 3600000).toISOString(),
        status: 'pending',
      },
      {
        id: 'vio_2',
        fileId: 'file9',
        fileName: 'walkthrough.mp4',
        type: 'sensitive_content',
        level: 'high',
        reportedAt: new Date(Date.now() - 12 * 3600000).toISOString(),
        status: 'under_review',
      },
    ];

    return {
      success: true,
      code: 200,
      data: {
        items,
        pagination: {
          totalItems: items.length,
          totalPages: 1,
          perPage: items.length,
          currentPage: 1,
          hasPrev: false,
          hasNext: false,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/violations\/([^/]+)\/resolve$/, 'post', (options) => {
    const violationId = (options.url.match(/\/api\/v1\/admin\/violations\/([^/]+)\/resolve/) || [])[1];
    addLog('admin_violation_resolve', { violationId });

    return {
      success: true,
      code: 200,
      data: {
        violationId,
        resolvedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/me\/profile$/, 'get', () => {
    const user = getCurrentUser();

    return {
      success: true,
      code: 200,
      data: {
        userId: user.userId,
        username: user.username,
        email: user.email,
        storageLimit: user.storageLimit,
        storageUsed: user.storageUsed,
        emailVerified: user.emailVerified,
        emailVerifiedAt: user.emailVerifiedAt,
        createdAt: user.createdAt,
        role: user.role,
        status: user.status,
        preference: user.preference,
        updatedAt: new Date().toISOString(),
        lastLogin: new Date(Date.now() - 2 * 3600000).toISOString(),
        groups: profileGroups,
      },
    };
  });

  Mock.mock(/\/api\/v1\/me\/update-profile$/, 'put', (options) => {
    const { username, email } = JSON.parse(options.body || '{}');
    const user = getCurrentUser();

    if (username) user.username = username;
    if (email) user.email = email;

    return {
      success: true,
      code: 200,
      data: {
        userId: user.userId,
        username: user.username,
        email: user.email,
        storageLimit: user.storageLimit,
        storageUsed: user.storageUsed,
        emailVerified: user.emailVerified,
        emailVerifiedAt: user.emailVerifiedAt,
        createdAt: user.createdAt,
        role: user.role,
        status: user.status,
        preference: user.preference,
        updatedAt: new Date().toISOString(),
        lastLogin: new Date(Date.now() - 2 * 3600000).toISOString(),
        groups: profileGroups,
      },
    };
  });

  Mock.mock(/\/api\/v1\/me\/preferences$/, 'get', () => {
    const user = getCurrentUser();
    return {
      success: true,
      code: 200,
      data: user.preference,
    };
  });

  Mock.mock(/\/api\/v1\/me\/preferences$/, 'put', (options) => {
    const user = getCurrentUser();
    const { language } = JSON.parse(options.body || '{}');

    if (language && (language === 'zh-CN' || language === 'en-US')) {
      user.preference = {
        ...user.preference,
        language,
      };
      addLog('user_preference_update', { userId: user.userId, language });
    }

    return {
      success: true,
      code: 200,
      data: user.preference,
    };
  });

  Mock.mock(/\/api\/v1\/me\/password$/, 'put', () => {
    addNotification('Password updated successfully', true);

    return {
      success: true,
      code: 200,
      data: null,
    };
  });

  Mock.mock(/\/api\/v1\/me\/storage-stats$/, 'get', () => {
    const user = getCurrentUser();
    const percentage = Number(((user.storageUsed / user.storageLimit) * 100).toFixed(2));

    return {
      success: true,
      code: 200,
      data: {
        storageLimit: user.storageLimit,
        storageUsed: user.storageUsed,
        storageAvailable: user.storageLimit - user.storageUsed,
        storagePercentage: percentage,
        fileCount: 1247,
        folderCount: 86,
        breakdown: {
          documents: { size: 5368709120, count: 234 },
          images: { size: 10737418240, count: 567 },
          videos: { size: 4294967296, count: 12 },
          audio: { size: 1073741824, count: 89 },
          archives: { size: 268435456, count: 15 },
          others: { size: 268435456, count: 330 },
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/me\/activity-log(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const operation = url.searchParams.get('operation');

    const filtered = mockLogs.filter((item) => (operation ? item.operation === operation : true));
    const paged = paginate(filtered, page, perPage);

    return {
      success: true,
      code: 200,
      data: {
        items: paged.items.map((item) => ({
          id: Number(String(item.id).replace('log_', '')),
          operation: item.operation,
          details: {
            ...item.details,
            user_agent: Mock.Random.pick([
              'Mozilla/5.0 Chrome/123.0 Safari/537.36',
              'Mozilla/5.0 Firefox/120.0',
              'Mozilla/5.0 Edg/122.0',
            ]),
          },
          ipAddress: item.ipAddress,
          performedAt: item.performedAt,
        })),
        pagination: {
          totalItems: paged.pagination.totalItems,
          totalPages: paged.pagination.totalPages,
          perPage: paged.pagination.perPage,
          currentPage: paged.pagination.currentPage,
          hasPrev: paged.pagination.hasPrev,
          hasNext: paged.pagination.hasNext,
        },
      },
    };
  });
};
