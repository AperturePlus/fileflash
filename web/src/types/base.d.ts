/**
 * API通用响应体结构
 * @template T 响应数据类型
 * @property {boolean} success - 是否成功
 * @property {number} code - 状态码
 * @property {string} message - 消息
 * @property {T} data - 数据
 * @property {string} timestamp - 时间戳
 */
export interface ApiResponse<T> {
    success: boolean;
    code: number;
    message: string;
    data: T;
    timestamp: string;
}

/**
 * 标准化分页元数据
 * @property {number} totalItems - 总项数
 * @property {number} totalPages - 总页数
 * @property {number} perPage - 每页项数
 * @property {number} currentPage - 当前页码
 * @property {boolean} hasPrev - 是否有前一页
 * @property {boolean} hasNext - 是否有下一页
 */
export interface PaginationMeta{
    totalItems: number;
    totalPages: number;
    perPage: number;
    currentPage: number;
    hasPrev: boolean;
    hasNext: boolean;
}

/**
 * 标准化分页响应数据结构
 * @template T 数据项类型，代表items中每个元素的类型
 */
export interface PaginatedData<T>{
    items: T[];
    pagination: PaginationMeta;
}
