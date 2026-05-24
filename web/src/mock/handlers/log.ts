import Mock from 'mockjs';
import { mockLogs, mockUsers, paginate } from '../state';

export const setupLogMocks = () => {
  Mock.mock(/\/api\/v1\/admin\/logs(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const userId = url.searchParams.get('userId');
    const operation = url.searchParams.get('operation');
    const fromAt = url.searchParams.get('fromAt');
    const toAt = url.searchParams.get('toAt');

    const enriched = mockLogs.map((item, index) => ({
      ...item,
      userId: item.userId ?? mockUsers[index % mockUsers.length].userId,
    }));

    const filtered = enriched.filter((item) => {
      if (userId && item.userId !== userId) return false;
      if (operation && item.operation !== operation) return false;
      if (fromAt && new Date(item.performedAt).getTime() < new Date(fromAt).getTime()) return false;
      if (toAt && new Date(item.performedAt).getTime() > new Date(toAt).getTime()) return false;
      return true;
    });

    const paged = paginate(filtered, page, perPage);

    return {
      success: true,
      code: 200,
      data: {
        logs: paged.items,
        pagination: paged.pagination,
      },
    };
  });
};

