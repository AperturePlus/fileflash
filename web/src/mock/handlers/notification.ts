import Mock from 'mockjs';
import { addNotification, mockNotifications, mockUsers, paginate } from '../state';

export const setupNotificationMocks = () => {
  Mock.mock(/\/api\/v1\/notifications(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const isReadText = url.searchParams.get('isRead');

    const filtered = mockNotifications.filter((item) => {
      if (isReadText === null || isReadText === '') return true;
      return item.isRead === (isReadText === 'true');
    });

    const paged = paginate(filtered, page, perPage);

    return {
      success: true,
      code: 200,
      data: {
        ...paged,
        unreadCount: mockNotifications.filter((item) => !item.isRead).length,
        totalCount: mockNotifications.length,
      },
    };
  });

  Mock.mock(/\/api\/v1\/notifications\/read-all$/, 'put', () => {
    let updatedCount = 0;
    mockNotifications.forEach((item) => {
      if (!item.isRead) {
        item.isRead = true;
        updatedCount += 1;
      }
    });

    return {
      success: true,
      code: 200,
      data: {
        updatedCount,
      },
    };
  });

  Mock.mock(/\/api\/v1\/notifications\/([^/]+)\/read$/, 'put', (options) => {
    const notificationId = Number((options.url.match(/\/api\/v1\/notifications\/([^/]+)\/read/) || [])[1]);
    const target = mockNotifications.find((item) => item.id === notificationId);

    if (!target) {
      return {
        success: false,
        code: 404,
        message: 'Notification not found',
        data: null,
      };
    }

    target.isRead = true;

    return {
      success: true,
      code: 200,
      data: {
        notificationId: target.id,
        updatedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/notifications\/([^/]+)$/, 'delete', (options) => {
    const notificationId = Number((options.url.match(/\/api\/v1\/notifications\/([^/?]+)/) || [])[1]);
    const index = mockNotifications.findIndex((item) => item.id === notificationId);

    if (index === -1) {
      return {
        success: false,
        code: 404,
        message: 'Notification not found',
        data: null,
      };
    }

    mockNotifications.splice(index, 1);

    return {
      success: true,
      code: 200,
      data: {
        notificationId,
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/notifications(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const paged = paginate(mockNotifications, page, perPage);

    return {
      success: true,
      code: 200,
      data: {
        ...paged,
        unreadCount: mockNotifications.filter((item) => !item.isRead).length,
        totalCount: mockNotifications.length,
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/notifications\/broadcast$/, 'post', (options) => {
    const body = JSON.parse(options.body || '{}');
    const message = (body.message || '').toString().trim();

    if (!message) {
      return {
        success: false,
        code: 422,
        message: 'BROADCAST_EMPTY_MESSAGE',
        data: null,
      };
    }

    addNotification(message);

    return {
      success: true,
      code: 200,
      data: {
        broadcastId: 'mock-' + Date.now(),
        recipientCount: mockUsers.length,
        sentAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/notifications\/([^/]+)$/, 'delete', (options) => {
    const id = (options.url.match(/\/api\/v1\/admin\/notifications\/([^/?]+)/) || [])[1];
    const notificationId = Number(id);
    const index = mockNotifications.findIndex((item) => item.id === notificationId);
    if (index !== -1) {
      mockNotifications.splice(index, 1);
    }
    return {
      success: true,
      code: 200,
      data: { notificationId: id, status: 'archived' },
    };
  });
};

