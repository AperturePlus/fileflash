/**
 * 上传分片数据接口
 * @property {number} percentage - 整体上传百分比
 * @property {number} uploadedSize - 已上传大小
 * @property {number} totalSize - 文件总大小
 */
export interface UploadProgressData {  
    percentage: number; // 整体上传百分比
    uploadedSize: number; // 已上传大小
    totalSize: number; // 文件总大小
  }

export type UploadProgressCallback = (data: UploadProgressData) => void;

import axios from 'axios';
import http from './http';
import { calculateFileHash, type HashProgressCallback } from './hash';
import type { 
  UploadPreflightRequest, 
  UploadPreflightResponse, 
  MergeChunksRequest, 
  MergeChunksResponse 
} from '../types/file';

const PREFLIGHT_TIMEOUT_MS = 45_000;
const CHUNK_TIMEOUT_MS = 120_000;
const MERGE_TIMEOUT_MS = 300_000;
const MERGE_RETRY_TIMEOUT_MS = 120_000;


/**
 * 准备上传接口的响应体 - 这部分现在由 file.d.ts 定义，可以移除
 */
/*
interface PrepareUploadResponse {
  fileExists: boolean;
  uploadId: string;
  uploadedChunkIndexes: number[];
}
*/

/**
 * 上传文件选项
 * @property {File} file - 要上传的文件
 * @property {string} parentId - 目标父文件夹ID
 * @property {number} [chunkSize=5242880] - 分片大小 (默认 5MB)
 * @property {number} [concurrency=5] - 并发上传数量
 * @property {number} [maxRetries=3] - 单个分片最大重试次数
 * @property {HashProgressCallback} [onHashProgress] - 哈希计算进度回调
 * @property {UploadProgressCallback} [onUploadProgress] - 上传进度回调
 */
export interface UploadFileOptions {
  file: File;
  parentId: string;
  chunkSize?: number;
  concurrency?: number;
  maxRetries?: number;
  onHashProgress?: HashProgressCallback;
  onUploadProgress?: UploadProgressCallback;
}

/**
 * 完整文件上传流程
 * 1. 计算文件 Hash (用于秒传和校验)
 * 2. 请求后端，检查文件状态（是否存在、已上传分片）
 * 3. 如果文件已存在，则完成秒传
 * 4. 如果文件不存在或部分存在，则执行分片上传
 * 5. 所有分片上传完成后，通知后端合并分片
 * 
 * @param options 上传配置
 */
export async function uploadFile(options: UploadFileOptions): Promise<MergeChunksResponse> {
  const {
    file,
    parentId,
    chunkSize = 5 * 1024 * 1024, // 5MB
    concurrency = 5,
    maxRetries = 3,
    onHashProgress,
    onUploadProgress,
  } = options;

  // 1. 计算文件 Hash
  console.log('开始计算文件 Hash...');
  const fileHash = await calculateFileHash(file, onHashProgress, chunkSize);
  console.log(`文件 Hash 计算完成: ${fileHash}`);

  // 2. 预检上传
  const preflightRequest: UploadPreflightRequest = {
    fileName: file.name,
    fileHash: fileHash,
    fileSize: file.size,
    mimeType: file.type,
    parentId: parentId,
  };

  let preflightResponse: UploadPreflightResponse;
  try {
    preflightResponse = await http.post<UploadPreflightResponse>('/uploads/preflight', preflightRequest, {
      timeout: PREFLIGHT_TIMEOUT_MS,
    });
  } catch (error) {
    console.error('上传预检阶段失败:', error);
    throw new Error('无法开始上传，请检查网络连接或与管理员联系。');
  }

  const { status, fileId, uploadId, uploadedChunkIndexes } = preflightResponse;

  // 3. 秒传逻辑
  if (status === 'COMPLETE') {
    console.log(`文件已存在，实现秒传。File ID: ${fileId}`);
    if (onUploadProgress) {
      onUploadProgress({
        percentage: 100,
        uploadedSize: file.size,
        totalSize: file.size,
      });
    }
    // 对于秒传，后端可能在预检响应中直接返回文件信息，我们可以将其返回
    // 此处我们返回一个简化的标识，或根据实际API调整
    return {
      fileId: fileId!,
      fileName: file.name,
      fileSize: file.size,
      mimeType: file.type,
      folderId: parentId,
      objectHash: fileHash,
      createdAt: new Date().toISOString(),
      downloadUrl: '', // Mock does not provide this
    };
  }
  
  // 如果状态不是 UPLOADING 或没有 uploadId，说明服务器状态异常
  if (status !== 'UPLOADING' || !uploadId) {
    throw new Error('服务器未能正确初始化上传。');
  }

  console.log(`准备上传，Upload ID: ${uploadId}`);
  
  // 4. 上传分片
  await uploadChunks({
    file,
    uploadId: uploadId,
    chunkSize: preflightResponse.chunkSize || chunkSize, // 优先使用后端建议的分片大小
    uploadedChunkIndexes: uploadedChunkIndexes || [],
    onProgress: onUploadProgress,
    concurrency,
    maxRetries,
  });

  // 5. 合并分片
  console.log('所有分片上传完成，正在请求合并...');
  const mergeRequest: MergeChunksRequest = {
    fileName: file.name,
    fileHash: fileHash,
    mimeType: file.type,
    parentId: parentId,
  };

  try {
    const mergeResponse = await http.post<MergeChunksResponse>(`/uploads/${uploadId}/merge`, mergeRequest, {
      timeout: MERGE_TIMEOUT_MS,
    });
    console.log('文件合并成功，上传完成！', mergeResponse);
     // 最终进度更新，确保是100%
    if (onUploadProgress) {
      onUploadProgress({
        percentage: 100,
        uploadedSize: file.size,
        totalSize: file.size,
      });
    }
    return mergeResponse;
  } catch (error) {
    if (isTimeoutOrNetworkError(error)) {
      const reconciled = await reconcileMergeResult({
        uploadId,
        mergeRequest,
        preflightRequest,
        file,
      });
      if (reconciled) {
        if (onUploadProgress) {
          onUploadProgress({
            percentage: 100,
            uploadedSize: file.size,
            totalSize: file.size,
          });
        }
        return reconciled;
      }
    }
    const backendMessage = extractApiErrorMessage(error);
    console.error('合并分片失败:', error);
    throw new Error(backendMessage || '文件分片合并失败，请重试或联系管理员。');
  }
}

/**
 * 上传分片选项
 * @property {File} file - 要上传的文件
 * @property {string} uploadId - 上传会话ID
 * @property {number} chunkSize - 分片大小
 * @property {number[]} [uploadedChunkIndexes] - 已上传的分片索引
 * @property {UploadProgressCallback} [onProgress] - 上传进度回调
 * @property {number} [concurrency] - 并发上传数量
 * @property {number} [maxRetries] - 单个分片最大重试次数
 */
interface UploadChunkOptions {  
  file: File;  
  uploadId: string;  
  chunkSize: number;  
  uploadedChunkIndexes?: number[];  
  onProgress?: UploadProgressCallback;  
  concurrency?: number;  
  maxRetries?: number;  
} 

export async function uploadChunks(options: UploadChunkOptions): Promise<void> {
  const {
    file,
    uploadId,
    chunkSize,
    uploadedChunkIndexes = [],
    onProgress,
    concurrency = 5,
    maxRetries = 3
  } = options;

  const totalChunks = Math.ceil(file.size / chunkSize);
  const chunkRequests: (() => Promise<any>)[] = [];
  
  // 重新计算已上传大小，以应对异常情况或断点续传
  let uploadedSize = 0;
  for (const index of uploadedChunkIndexes) {
    const start = index * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    uploadedSize += end - start;
  }

  for (let i = 0; i < totalChunks; i++) {  
      // 如果该分片已上传，则跳过  
    if (uploadedChunkIndexes.includes(i)) {  
      continue;  
    }  

    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, file.size);  
    const chunk = file.slice(start, end);  

    // 将请求封装成一个函数，以便后续并发控制  
    const task = async () => {  
      const formData = new FormData();  
      formData.append('chunk', chunk);  
      formData.append('chunkIndex', String(i));  
      // formData.append('chunkHash', await calculateChunkHash(chunk)); // 可选的分片哈希  

      // 执行上传，并包含重试逻辑  
      for (let attempt = 1; attempt <= maxRetries; attempt++) {  
        try {  
          await http.post(`/uploads/${uploadId}/chunk`, formData, {
            timeout: CHUNK_TIMEOUT_MS,
          });  
          
          // 上传成功，更新进度  
          uploadedSize += chunk.size;  
          if (onProgress) {
            // 确保最终进度不超过100%
            const percentage = Math.min(Math.round((uploadedSize / file.size) * 100), 100);
            onProgress({  
              percentage: percentage,  
              uploadedSize,  
              totalSize: file.size,  
            });  
          }  
          return; // 任务成功，退出重试循环  
        } catch (error) {  
          console.error(`Chunk ${i} upload failed, attempt ${attempt}/${maxRetries}`, error);  
          if (attempt === maxRetries) {  
            throw new Error(`Chunk ${i} failed to upload after ${maxRetries} attempts.`);  
          }  
        }  
      }  
    };  
    chunkRequests.push(task);  
  } 
    // 并发执行上传任务  
  await executeConcurrentTasks(chunkRequests, concurrency);  

  // 3. 所有分片上传成功后，发送合并请求  

}

interface ReconcileMergeOptions {
  uploadId: string;
  mergeRequest: MergeChunksRequest;
  preflightRequest: UploadPreflightRequest;
  file: File;
}

function isTimeoutOrNetworkError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false;
  }
  return error.code === 'ECONNABORTED' || !error.response;
}

function extractApiErrorMessage(error: unknown): string | null {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as { message?: unknown } | undefined;
    if (typeof responseData?.message === 'string' && responseData.message.trim()) {
      return responseData.message.trim();
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  return null;
}

function buildCompleteResponse(
  params: {
    fileId: string;
    mergeRequest: MergeChunksRequest;
    file: File;
  },
): MergeChunksResponse {
  const { fileId, mergeRequest, file } = params;
  return {
    fileId,
    fileName: mergeRequest.fileName,
    fileSize: file.size,
    mimeType: mergeRequest.mimeType,
    folderId: mergeRequest.parentId,
    objectHash: mergeRequest.fileHash,
    createdAt: new Date().toISOString(),
    downloadUrl: `/api/v1/files/${fileId}/download`,
  };
}

async function reconcileMergeResult(options: ReconcileMergeOptions): Promise<MergeChunksResponse | null> {
  const { uploadId, mergeRequest, preflightRequest, file } = options;

  try {
    const preflight = await http.post<UploadPreflightResponse>('/uploads/preflight', preflightRequest, {
      timeout: PREFLIGHT_TIMEOUT_MS,
    });
    if (preflight.status === 'COMPLETE' && preflight.fileId) {
      return buildCompleteResponse({ fileId: preflight.fileId, mergeRequest, file });
    }

    const targetUploadId = preflight.uploadId || uploadId;
    try {
      return await http.post<MergeChunksResponse>(`/uploads/${targetUploadId}/merge`, mergeRequest, {
        timeout: MERGE_RETRY_TIMEOUT_MS,
      });
    } catch (retryError) {
      if (!isTimeoutOrNetworkError(retryError)) {
        throw retryError;
      }

      const finalPreflight = await http.post<UploadPreflightResponse>('/uploads/preflight', preflightRequest, {
        timeout: PREFLIGHT_TIMEOUT_MS,
      });
      if (finalPreflight.status === 'COMPLETE' && finalPreflight.fileId) {
        return buildCompleteResponse({ fileId: finalPreflight.fileId, mergeRequest, file });
      }
    }
  } catch (error) {
    console.warn('merge reconcile failed', error);
  }

  return null;
}

/**  
 * 并发执行一组 Promise 任务。  
 * @param tasks - 一个返回 Promise 的函数数组。  
 * @param limit - 并发上限。  
 */  
async function executeConcurrentTasks(tasks: (() => Promise<any>)[], limit: number) {  
    const results = [];  
    const executing: Promise<any>[] = [];  
    for (const task of tasks) {  
        const p = task();  
        results.push(p);  
        
        if (limit <= tasks.length) {  
            const e: Promise<any> = p.then(() => executing.splice(executing.indexOf(e), 1));  
            executing.push(e);  
            if (executing.length >= limit) {  
                await Promise.race(executing);  
            }  
        }  
    }  
    return Promise.all(results);  
}  
