import http from '../utils/http';
import type { StorageStats } from '../types/user';
import type { StorageUsageTrend, GetUsageTrendRequest } from '../types/storage';

/**
 * 获取存储空间统计信息
 * @returns 存储空间统计信息
 */
export const getStorageSummary = () => {
  return http.get<StorageStats>('/storage/summary');
};

/**
 * 获取存储空间使用趋势
 * @param params 请求参数
 * @returns 存储空间使用趋势
 */
export const getUsageTrend = (params: GetUsageTrendRequest) => {
  return http.get<StorageUsageTrend>('/storage/usage-trend', params);
};

export const getStorageUsers = () => {
  return http.get<any>('/admin/storage/users');
};

export const updateStorageQuota = (userId: string, storageLimit: number) => {
  return http.patch<{
    userId: string;
    storageLimit: number;
    storageUsed: number;
    usagePercentage: number;
    updatedAt: string;
  }>(`/admin/storage/users/${userId}/quota`, { storageLimit });
};

/**
 * 管理员视角：全局存储概览
 */
export const getAdminStorageSummary = () => {
  return http.get<{
    storageUsed: number;
    storageLimit: number;
    storagePercentage: number;
    fileCount: number;
    userCount: number;
    updatedAt: string;
  }>('/admin/storage/summary');
};
