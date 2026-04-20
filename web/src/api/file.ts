import http from '../utils/http';
import type {
  PaginatedData
} from '../types/base';
import type {
  FileItem,
  ContentItem,
  FileDetails,
  GetFilesRequest,
  RenameFileRequest,
  MoveFileRequest,
  CopyFileRequest,
  BatchFilesRequest,
  UploadPreflightRequest,
  UploadPreflightResponse,
  BatchUploadPreflightRequest,
  BatchUploadPreflightResponse,
  BatchUploadCompleteRequest,
  BatchUploadCompleteResponse,
  BatchUploadStatusResponse,
  MergeChunksRequest,
  MergeChunksResponse,
  AdminFileAuditItem,
  GetAdminFilesRequest,
} from '../types/file';

// 上传相关API
export const preflightUpload = (data: UploadPreflightRequest) => {
  return http.post<UploadPreflightResponse>('/uploads/preflight', data);
};

/**
 * 批量上传预检
 * @param data 批量预检请求
 * @returns 每个文件的上传会话信息
 */
export const batchPreflightUpload = (data: BatchUploadPreflightRequest) => {
  return http.post<BatchUploadPreflightResponse>('/uploads/batch-preflight', data);
};

/**
 * 批量上传完成确认
 * @param batchId 批次ID
 * @param data 完成确认请求
 * @returns 批次完成结果
 */
export const completeBatchUpload = (batchId: string, data: BatchUploadCompleteRequest) => {
  return http.post<BatchUploadCompleteResponse>(`/uploads/batch/${batchId}/complete`, data);
};

/**
 * 获取批量上传状态
 * @param batchId 批次ID
 * @returns 批量上传状态
 */
export const getBatchUploadStatus = (batchId: string) => {
  return http.get<BatchUploadStatusResponse>(`/uploads/batch/${batchId}`);
};

/**
 * 上传分片
 * @param uploadId 上传ID
 * @param chunk 分片文件
 * @param chunkIndex 分片索引
 * @returns 上传分片的响应数据
 */
export const uploadChunk = (uploadId: string, chunk: File, chunkIndex: number) => {
  const formData = new FormData();
  formData.append('chunk', chunk);
  formData.append('chunkIndex', chunkIndex.toString());
  return http.post<void>(`/uploads/${uploadId}/chunk`, formData, { 
    headers: { 'Content-Type': 'multipart/form-data' } 
  });
};

/**
 * 合并分片
 * @param uploadId 上传ID
 * @param data 合并请求数据
 * @returns 合并后的文件信息
 */
export const mergeChunks = (uploadId: string, data: MergeChunksRequest) => {
  return http.post<MergeChunksResponse>(`/uploads/${uploadId}/merge`, data);
};

// 文件管理API
export const getFiles = (params: GetFilesRequest) => {
  return http.get<PaginatedData<FileItem>>('/files', params);
};

/**
 * 获取已星标文件与文件夹
 */
export const getStarredFiles = () => {
  return http.get<PaginatedData<ContentItem>>('/files/starred');
};

/**
 * 获取文件详情
 * @param fileId 文件ID
 * @returns 文件详情
 */
export const getFileDetails = (fileId: string) => {
  return http.get<FileDetails>(`/files/${fileId}`);
};

/**
 * 下载文件
 * @param fileId 文件ID
 * @param range 下载范围
 * @returns 下载的文件内容
 */
export const downloadFile = (fileId: string, range?: string) => {
  const config = range ? { headers: { Range: range }, responseType: 'blob' as const } : { responseType: 'blob' as const };
  return http.get<Blob>(`/files/${fileId}/download`, undefined, config);
};

/**
 * 预览文件
 * @param fileId 文件ID
 * @returns 预览的文件内容
 */
export const previewFile = (fileId: string) => {
  return http.get<Blob>(`/files/${fileId}/preview`, undefined, { responseType: 'blob' });
};

/**
 * 获取文件缩略图
 * @param fileId 文件ID
 * @param size 缩略图大小
 * @returns 文件缩略图
 */
export const getThumbnail = (fileId: string, size: 'small' | 'medium' | 'large' = 'small') => {
  return http.get<Blob>(`/files/${fileId}/thumbnail`, { size }, { responseType: 'blob' });
};

/**
 * 重命名文件
 * @param fileId 文件ID
 * @param data 重命名请求数据
 * @returns 重命名后的文件信息
 */
export const renameFile = (fileId: string, data: RenameFileRequest) => {
  return http.patch<FileDetails>(`/files/${fileId}`, data);
};

/**
 * 移动文件
 * @param fileId 文件ID
 * @param data 移动请求数据
 * @returns 移动后的文件信息
 */
export const moveFile = (fileId: string, data: MoveFileRequest) => {
  return http.patch<{ fileId: string; targetFolderId: string; movedAt: string }>(`/files/${fileId}/move`, data);
};

/**
 * 设置文件星标状态
 * @param fileId 文件ID
 * @param isStarred 是否星标
 */
export const toggleFileStar = (fileId: string, isStarred: boolean) => {
  return http.patch<FileDetails>(`/files/${fileId}/star`, { isStarred });
};

/**
 * 复制文件
 * @param fileId 文件ID
 * @param data 复制请求数据
 * @returns 复制后的文件信息
 */
export const copyFile = (fileId: string, data: CopyFileRequest) => {
  return http.post<{ fileId: string; originalFileId: string; targetFolderId: string; newName?: string; copiedAt: string }>(`/files/${fileId}/copy`, data);
};

/**
 * 删除文件
 * @param fileId 文件ID
 * @returns 删除后的文件信息
 */
export const deleteFile = (fileId: string) => {
  return http.delete<{ fileId: string; fileName: string; deletedAt: string }>(`/files/${fileId}`);
};

/**
 * 批量下载文件 (后端打包成zip)
 * @param fileIds 要下载的文件ID列表
 * @returns zip文件流
 */
export const batchDownloadFiles = (fileIds: string[]) => {
  return http.post<Blob>('/files/batch-download', { fileIds }, { responseType: 'blob' });
};

/**
 * 批量操作文件
 * @param data 批量操作请求数据
 * @returns 操作后的文件信息
 */
export const batchFiles = (data: BatchFilesRequest) => {
  return http.post<ResponseData>('/files/batch', data);
};

interface ResponseData {
  processed: number;
  action: string; 
  succeeded: number;
}

export const getAdminFiles = (params: GetAdminFilesRequest) => {
  return http.get<PaginatedData<AdminFileAuditItem>>('/admin/files', params);
};

export const rescanAdminFile = (fileId: string) => {
  return http.post<{ fileId: string; virusStatus: 'clean' | 'pending' | 'flagged'; scannedAt: string }>(`/admin/files/${fileId}/rescan`);
};
