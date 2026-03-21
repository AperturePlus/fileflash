import http from '../utils/http';
import type { StorageStats } from '../types/user';
import type { StorageUsageTrend, GetUsageTrendRequest } from '../types/storage';

// 转换后端下划线命名为前端驼峰命名的数据转换函数
function convertStorageStatsFields(data: any): StorageStats {
  return {
    storageLimit: data.storage_limit,
    storageUsed: data.storage_used,
    storageAvailable: data.storage_available,
    storagePercentage: data.storage_percentage,
    fileCount: data.file_count,
    folderCount: data.folder_count,
    breakdown: data.breakdown || {}
  };
}

/**
 * 获取存储空间统计信息
 * @returns 存储空间统计信息
 */
export const getStorageSummary = async () => {
  const rawData = await http.get<any>('/storage/summary');
  return convertStorageStatsFields(rawData);
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
