import http from '../utils/http';
import type { PaginatedData } from '../types/base';
import type { RecycleBinItem, GetRecycleBinRequest, RestoreRecycleItemRequest } from '../types/file';

/**
 * 获取回收站内容
 * @param params 请求参数
 * @returns 回收站内容列表
 */
export const getRecycleBin = (params: GetRecycleBinRequest) => {
  return http.get<PaginatedData<RecycleBinItem>>('/recycle-bin', params);
};

/**
 * 恢复回收站项目
 * @param itemId 项目ID
 * @param data 恢复请求数据
 * @returns 恢复后的项目信息
 */
export const restoreItem = (itemId: string, data: RestoreRecycleItemRequest) => {
  return http.post<{ itemType: string; id: string; name: string; restoredTo: any; restoredAt: string }>(`/recycle-bin/${itemId}/restore`, data);
};

/**
 * 永久删除回收站项目
 * @param itemId 项目ID
 * @param itemType 项目类型
 * @returns 删除后的项目信息
 */
export const permanentDelete = (itemId: string, _itemType: string) => {
  return http.delete<{ }>(`/recycle-bin/${itemId}`);
};

/**
 * 清空回收站
 * @returns 清空后的统计信息
 */
export const clearRecycleBin = () => {
  return http.delete<{ filesDeleted: number; foldersDeleted: number; totalStorageFreed: number; cleanupCompletedAt: string }>('/recycle-bin');
}; 
