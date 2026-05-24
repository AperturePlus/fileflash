import type { PaginationMeta } from './base';

/**
 * 日志项
 * @property {string} id 日志ID
 * @property {string} operation 操作类型
 * @property {string} operationName 操作名称
 * @property {Record<string, string | number>} details 操作详情
 * @property {string} ipAddress 操作IP地址
 * @property {string} performedAt 操作时间
 */
export interface LogItem {
  id: string;
  userId?: string | null;
  operation: string;
  operationName: string;
  details: Record<string, string | number>;
  ipAddress: string;
  performedAt: string;
}

/**
 * 日志列表（标准分页形状）
 */
export type LogsList = {
  logs: LogItem[];
  pagination: PaginationMeta;
};

/**
 * 管理员视角的日志查询请求
 */
export interface GetAdminLogsRequest {
  userId?: string;
  operation?: string;
  result?: 'success' | 'failure';
  fromAt?: string;
  toAt?: string;
  page?: number;
  perPage?: number;
}
