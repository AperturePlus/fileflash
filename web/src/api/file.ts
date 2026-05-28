import http from '../utils/http';
import type {
  PaginatedData
} from '../types/base';
import type {
  FileItem,
  ContentItem,
  FileDetails,
  FilePreviewUrlResponse,
  GetFilesRequest,
  RenameFileRequest,
  MoveFileRequest,
  MoveFileResponse,
  CopyFileRequest,
  BatchFilesRequest,
  BatchFilesResponse,
  BatchDownloadRequest,
  UploadPreflightRequest,
  UploadPreflightResponse,
  UploadRecoverableSession,
  BatchUploadPreflightRequest,
  BatchUploadPreflightResponse,
  BatchUploadCompleteRequest,
  BatchUploadCompleteResponse,
  BatchUploadStatusResponse,
  MergeChunksRequest,
  MergeChunksResponse,
  CancelUploadResponse,
  AdminFileAuditItem,
  AdminFileAuditDetail,
  GetAdminFilesRequest,
  ArchiveExtractRequest,
  BackgroundJob,
  JobResultArchiveExtract,
  JobResultArchivePreview,
} from '../types/file';

type MockPreviewPayload = {
  __mockPreview: true;
  mimeType: string;
  content: string;
  encoding: 'text' | 'base64';
};

function isBlobLike(value: unknown): value is Blob {
  return value instanceof Blob || Object.prototype.toString.call(value) === '[object Blob]';
}

function base64ToBytes(content: string) {
  const decoded = atob(content);
  const bytes = new Uint8Array(decoded.length);
  for (let index = 0; index < decoded.length; index += 1) {
    bytes[index] = decoded.charCodeAt(index);
  }
  return bytes;
}

function isMockPreviewPayload(value: unknown): value is MockPreviewPayload {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const payload = value as Partial<MockPreviewPayload>;
  return payload.__mockPreview === true && typeof payload.content === 'string';
}

function normalizePreviewBlob(response: Blob | MockPreviewPayload | string): Blob {
  if (isBlobLike(response)) {
    return response;
  }

  let payload: MockPreviewPayload | null = null;
  if (isMockPreviewPayload(response)) {
    payload = response;
  } else if (typeof response === 'string') {
    try {
      const parsed = JSON.parse(response);
      if (isMockPreviewPayload(parsed)) {
        payload = parsed;
      }
    } catch {
      return new Blob([response], { type: 'text/plain' });
    }
  }

  if (!payload) {
    return new Blob([], { type: 'application/octet-stream' });
  }

  const content = payload.encoding === 'base64'
    ? base64ToBytes(payload.content)
    : payload.content;
  return new Blob([content], { type: payload.mimeType || 'application/octet-stream' });
}

// 上传相关API
export const preflightUpload = (data: UploadPreflightRequest) => {
  return http.post<UploadPreflightResponse>('/uploads/preflight', data);
};

export const getRecoverableUploads = () => {
  return http.get<UploadRecoverableSession[]>('/uploads/recoverable');
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
  return http.post<BackgroundJob<MergeChunksResponse>>(`/uploads/${uploadId}/merge`, data);
};

export const cancelUploadSession = (uploadId: string) => {
  return http.post<CancelUploadResponse>(`/uploads/${uploadId}/cancel`);
};

// Archive preview/extract APIs
export const requestArchivePreview = (fileId: string) => {
  return http.post<BackgroundJob<JobResultArchivePreview>>(`/files/${fileId}/archive/preview`);
};

export const requestArchiveExtract = (fileId: string, data: ArchiveExtractRequest) => {
  return http.post<BackgroundJob<JobResultArchiveExtract>>(`/files/${fileId}/archive/extract`, data);
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

export const getPreviewUrl = (fileId: string) => {
  return http.post<FilePreviewUrlResponse>(`/files/${fileId}/preview-url`);
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
  return http.patch<MoveFileResponse>(`/files/${fileId}/move`, data);
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
export const batchDownloadFiles = (data: BatchDownloadRequest) => {
  return http.post<Blob>('/files/batch-download', data, { responseType: 'blob' });
};

/**
 * 批量操作文件
 * @param data 批量操作请求数据
 * @returns 操作后的文件信息
 */
export const batchFiles = (data: BatchFilesRequest) => {
  return http.post<BatchFilesResponse>('/files/batch', data);
};

export const getAdminFiles = (params: GetAdminFilesRequest) => {
  return http.get<PaginatedData<AdminFileAuditItem>>('/admin/files', params);
};

export const getAdminFileDetail = (fileId: string) => {
  return http.get<AdminFileAuditDetail>(`/admin/files/${fileId}`);
};

export const rescanAdminFile = (fileId: string) => {
  return http.post<{ fileId: string; virusStatus: 'clean' | 'pending' | 'flagged'; scannedAt: string }>(`/admin/files/${fileId}/rescan`);
};

export const previewAdminFile = async (fileId: string) => {
  const response = await http.get<Blob | MockPreviewPayload | string>(
    `/admin/files/${fileId}/preview`,
    undefined,
    { responseType: 'blob' },
  );
  return normalizePreviewBlob(response);
};

export const getAdminPreviewUrl = (fileId: string) => {
  return http.post<FilePreviewUrlResponse>(`/admin/files/${fileId}/preview-url`);
};
