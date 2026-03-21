import Mock from 'mockjs';
import { mockLogs } from '../state';

export const setupLogMocks = () => {
  Mock.mock(/\/api\/v1\/logs(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const operation = url.searchParams.get('operation');
    const startDate = url.searchParams.get('startDate');
    const endDate = url.searchParams.get('endDate');

    const filtered = mockLogs.filter((item) => {
      if (operation && item.operation !== operation) return false;
      if (startDate && new Date(item.performedAt).getTime() < new Date(startDate).getTime()) return false;
      if (endDate && new Date(item.performedAt).getTime() > new Date(endDate).getTime()) return false;
      return true;
    });

    const start = (Math.max(page, 1) - 1) * Math.max(perPage, 1);
    const sliced = filtered.slice(start, start + Math.max(perPage, 1));

    return {
      success: true,
      code: 200,
      data: {
        logs: sliced,
        totalCount: filtered.length,
        returnedCount: sliced.length,
        hasMore: start + sliced.length < filtered.length,
        filterSummary: {
          operation: operation || undefined,
          dateRange: startDate || endDate ? `${startDate || '-'} ~ ${endDate || '-'}` : undefined,
          matchedRecords: filtered.length,
        },
      },
    };
  });
};
