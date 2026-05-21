import Mock from 'mockjs';
import {
  addLog,
  addNotification,
  getCurrentUser,
  mockLogs,
  mockRegistrationEmailDomainRules,
  mockUsers,
  paginate,
} from '../state';

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

function extractDomain(email: string) {
  const at = email.lastIndexOf('@');
  if (at < 0) return '';
  return email.slice(at + 1).trim().toLowerCase();
}

function isAllowedEmailDomain(email: string) {
  const enabledRules = mockRegistrationEmailDomainRules.filter((item) => item.enabled);
  if (!enabledRules.length) return false;
  const domain = extractDomain(email);
  if (!domain) return false;
  return enabledRules.some((item) => {
    try {
      const regex = new RegExp(`^${item.pattern}$`);
      return regex.test(domain);
    } catch {
      return false;
    }
  });
}

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

  Mock.mock(/\/api\/v1\/admin\/registration-email-domain-rules(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const queryText = (url.searchParams.get('queryText') || '').trim().toLowerCase();
    const enabledRaw = url.searchParams.get('enabled');

    let filtered = mockRegistrationEmailDomainRules.slice();
    if (enabledRaw === 'true' || enabledRaw === 'false') {
      const enabledValue = enabledRaw === 'true';
      filtered = filtered.filter((item) => item.enabled === enabledValue);
    }
    if (queryText) {
      filtered = filtered.filter((item) =>
        item.name.toLowerCase().includes(queryText) || item.pattern.toLowerCase().includes(queryText),
      );
    }

    return {
      success: true,
      code: 200,
      data: paginate(filtered, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/admin\/registration-email-domain-rules$/, 'post', (options) => {
    const { name, pattern, enabled } = JSON.parse(options.body || '{}');
    if (!name || !pattern) {
      return {
        success: false,
        code: 400,
        message: 'name and pattern are required',
        data: null,
      };
    }

    const duplicate = mockRegistrationEmailDomainRules.find(
      (item) => item.name.toLowerCase() === String(name).toLowerCase(),
    );
    if (duplicate) {
      return {
        success: false,
        code: 409,
        message: 'Rule name already exists',
        data: null,
      };
    }
    try {
      new RegExp(`^${String(pattern)}$`);
    } catch {
      return {
        success: false,
        code: 400,
        message: 'Invalid regex pattern',
        data: null,
      };
    }

    const item = {
      ruleId: String(Date.now()),
      name: String(name),
      pattern: String(pattern),
      enabled: enabled !== false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    mockRegistrationEmailDomainRules.unshift(item);
    addLog('admin_registration_email_domain_rule_create', { ruleId: item.ruleId });
    return {
      success: true,
      code: 201,
      data: item,
    };
  });

  Mock.mock(/\/api\/v1\/admin\/registration-email-domain-rules\/([^/]+)$/, 'patch', (options) => {
    const ruleId = (options.url.match(/\/api\/v1\/admin\/registration-email-domain-rules\/([^/]+)/) || [])[1];
    const payload = JSON.parse(options.body || '{}');
    const target = mockRegistrationEmailDomainRules.find((item) => item.ruleId === ruleId);
    if (!target) {
      return {
        success: false,
        code: 404,
        message: 'Rule not found',
        data: null,
      };
    }
    if (typeof payload.name === 'string' && payload.name.trim()) {
      target.name = payload.name.trim();
    }
    if (typeof payload.pattern === 'string' && payload.pattern.trim()) {
      try {
        new RegExp(`^${payload.pattern.trim()}$`);
      } catch {
        return {
          success: false,
          code: 400,
          message: 'Invalid regex pattern',
          data: null,
        };
      }
      target.pattern = payload.pattern.trim();
    }
    if (typeof payload.enabled === 'boolean') {
      target.enabled = payload.enabled;
    }
    target.updatedAt = new Date().toISOString();
    addLog('admin_registration_email_domain_rule_update', { ruleId: target.ruleId });
    return {
      success: true,
      code: 200,
      data: target,
    };
  });

  Mock.mock(/\/api\/v1\/admin\/registration-email-domain-rules\/([^/]+)$/, 'delete', (options) => {
    const ruleId = (options.url.match(/\/api\/v1\/admin\/registration-email-domain-rules\/([^/]+)/) || [])[1];
    const index = mockRegistrationEmailDomainRules.findIndex((item) => item.ruleId === ruleId);
    if (index < 0) {
      return {
        success: false,
        code: 404,
        message: 'Rule not found',
        data: null,
      };
    }
    mockRegistrationEmailDomainRules.splice(index, 1);
    addLog('admin_registration_email_domain_rule_delete', { ruleId });
    return {
      success: true,
      code: 200,
      data: {
        ruleId,
        deletedAt: new Date().toISOString(),
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
    if (email) {
      if (!isAllowedEmailDomain(String(email))) {
        return {
          success: false,
          code: 400,
          message: '邮箱后缀不被允许，请更换邮箱',
          data: null,
        };
      }
      user.email = email;
      user.emailVerified = false;
      user.emailVerifiedAt = null;
    }

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
