import Mock from 'mockjs';
import { addNotification, mockNotifications, paginate } from '../state';

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

  Mock.mock(/\/api\/v1\/notifications\/broadcast$/, 'post', (options) => {
    const { message } = JSON.parse(options.body || '{}');

    if (!message) {
      return {
        success: false,
        code: 400,
        message: 'message is required',
        data: null,
      };
    }

    const created = addNotification(message, false);

    return {
      success: true,
      code: 201,
      data: created,
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
};
