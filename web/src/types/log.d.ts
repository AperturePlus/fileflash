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
  operation: string;
  operationName: string;
  details: Record<string, string | number>;
  ipAddress: string;
  performedAt: string;
}

/**
 * 日志列表
 * @property {LogItem[]} logs 日志列表
 * @property {number} totalCount 总日志数
 * @property {number} returnedCount 返回的日志数
 * @property {boolean} hasMore 是否有更多日志
 * @property {FilterSummary} filterSummary 过滤摘要
 */
export type LogsList = {
  logs: LogItem[];
  totalCount: number;
  returnedCount: number;
  hasMore: boolean;
  filterSummary: FilterSummary;
};

/**
 * 过滤摘要
 * @property {string} operation 操作类型
 * @property {string} dateRange 日期范围
 * @property {number} matchedRecords 匹配的记录数
 */
export interface FilterSummary {
  operation?: string;
  dateRange?: string;
  matchedRecords: number;
}

/**
 * 获取日志请求
 * @property {number} page 页码
 * @property {number} perPage 每页数量
 * @property {string} operation 操作类型
 * @property {string} startDate 开始日期
 * @property {string} endDate 结束日期
 */
export interface GetLogsRequest {
  page?: number;
  perPage?: number;
  operation?: string;
  startDate?: string;
  endDate?: string;
} 