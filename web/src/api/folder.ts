import http from '../utils/http';
import type { PaginatedData } from '../types/base';
import type {
  ContentItem,
  GetFolderContentsRequest,
  FolderPathResponse,
  FolderItem,
  CreateFolderRequest,
  RenameFolderRequest,
  MoveFolderRequest,
} from '../types/file';

/**
 * 获取特定文件夹的内容（文件和子文件夹）
 * @param params 请求参数，包括 folderId 和分页/排序选项
 */
export const getFolderContents = (params: GetFolderContentsRequest) => {
  const { folderId, ...rest } = params;
  
  // 特殊处理根文件夹
  if (folderId === 'root') {
    // 根文件夹使用专门的API端点
    const queryParams = new URLSearchParams();
    Object.entries(rest).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, String(value));
      }
    });
    const queryString = queryParams.toString();
    const url = `/folders/root${queryString ? `?${queryString}` : ''}`;
    return http.get<PaginatedData<ContentItem>>(url);
  }
  
  // 确保参数正确序列化，避免嵌套params对象
  const queryParams = new URLSearchParams();
  
  Object.entries(rest).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      queryParams.append(key, String(value));
    }
  });
  
  const queryString = queryParams.toString();
  const url = `/folders/${folderId}${queryString ? `?${queryString}` : ''}`;
  
  return http.get<PaginatedData<ContentItem>>(url);
};

/**
 * 创建一个新的文件夹
 * @param data 包含文件夹名称和父文件夹ID
 */
export const createFolder = (data: CreateFolderRequest) => {
  return http.post<FolderItem>('/folders', data);
};

/**
 * 获取文件夹列表
 * @param params 查询参数
 */
export const getFolders = (params: { parentId?: string; page?: number; perPage?: number }) => {
  return http.get<PaginatedData<FolderItem>>('/folders', params);
};



/**
 * 获取文件夹的完整路径信息
 * @param folderId 文件夹ID
 */
export const getFolderPath = (folderId: string) => {
  return http.get<{ pathItems: any[] }>(`/folders/${folderId}/path`);
};

/**
 * 重命名一个文件夹
 * @param folderId 要重命名的文件夹ID
 * @param data 包含新名称
 */
export const renameFolder = (folderId: string, data: RenameFolderRequest) => {
  return http.patch<FolderItem>(`/folders/${folderId}`, data);
};

/**
 * 移动一个文件夹
 * @param folderId 要移动的文件夹ID
 * @param data 包含目标父文件夹ID
 */
export const moveFolder = (folderId: string, data: MoveFolderRequest) => {
  return http.patch<{ folderId: string; targetParentId: string; movedAt: string }>(`/folders/${folderId}/move`, data);
};

/**
 * 删除一个文件夹
 * @param folderId 要删除的文件夹ID
 */
export const deleteFolder = (folderId: string) => {
  return http.delete<{ folderId: string; folderName: string; deletedAt: string }>(`/folders/${folderId}`);
};

/**
 * 获取文件夹大小统计
 * @param folderId 文件夹ID
 */
export const getFolderSize = (folderId: string) => {
  return http.get<{ totalSize: number; fileCount: number; folderCount: number }>(`/folders/${folderId}/size`);
};

/**
 * 复制一个文件夹
 * @param folderId 要复制的文件夹ID
 * @param data 包含目标父文件夹ID和新名称
 */
export const copyFolder = (folderId: string, data: { targetParentId: string; newName?: string }) => {
  return http.post<FolderItem>(`/folders/${folderId}/copy`, data);
}; 