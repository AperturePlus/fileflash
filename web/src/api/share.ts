import http from '../utils/http';
import type { PaginatedData } from '../types/base';
import type {
  CreateShareRequest,
  Share,
  AccessShareRequest,
  AccessShareResponseData,
  GetSharedItemsRequest,
  SharedItem
} from '../types/share';

/**
 * 创建分享
 * @param data 分享请求数据
 * @returns 创建的分享信息
 */
export const createShare = (data: CreateShareRequest) => {
  return http.post<Share>('/shares', data);
};

/**
 * 获取分享列表
 * @param params 请求参数
 * @returns 分享列表
 */
export const getShares = (params: { page?: number; perPage?: number }) => {
  return http.get<PaginatedData<Share>>('/shares', params);
};

/**
 * 获取分享详情
 * @param shareLink 分享链接
 * @returns 分享详情
 */
export const getShareDetails = (shareLink: string) => {
  return http.get<Share>(`/shares/${shareLink}`);
};

/**
 * 访问分享
 * @param shareLink 分享链接
 * @param data 访问请求数据
 * @returns 访问分享的响应数据
 */
export const accessShare = (shareLink: string, data: AccessShareRequest) => {
  return http.post<AccessShareResponseData>(`/shares/${shareLink}/access`, data);
};

/**
 * 删除分享
 * @param shareLink 分享链接
 * @returns 删除分享的响应数据
 */
export const deleteShare = (shareLink: string) => {
  return http.delete<{ shareId: string; shareLink: string; deletedAt: string }>(`/shares/${shareLink}`);
};

/**
 * 获取与我共享的项目列表
 * @param params 查询参数
 * @returns 共享项目列表
 */
export const getSharedItems = (params: GetSharedItemsRequest) => {
  return http.get<PaginatedData<SharedItem>>('/shared-items', params);
}; 