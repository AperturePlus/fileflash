import axios from 'axios';
import http from './http';
import { calculateFileHash, type HashProgressCallback } from './hash';
import type {
  BackgroundJob,
  MergeChunksRequest,
  MergeChunksResponse,
  UploadPreflightRequest,
  UploadPreflightResponse,
} from '../types/file';

const PREFLIGHT_TIMEOUT_MS = 45_000;
const CHUNK_TIMEOUT_MS = 120_000;
const MERGE_TIMEOUT_MS = 300_000;
const MERGE_RETRY_TIMEOUT_MS = 120_000;
const MERGE_JOB_POLL_INTERVAL_MS = 900;
const MERGE_JOB_POLL_TIMEOUT_MS = 300_000;

export interface UploadProgressData {
  percentage: number;
  uploadedSize: number;
  totalSize: number;
}

export type UploadProgressCallback = (data: UploadProgressData) => void;

export class UploadCanceledError extends Error {
  constructor(message = 'Upload canceled by user.') {
    super(message);
    this.name = 'UploadCanceledError';
  }
}

export function isUploadCanceledError(error: unknown): boolean {
  if (error instanceof UploadCanceledError) return true;
  if (error instanceof DOMException && error.name === 'AbortError') return true;
  if (error instanceof Error && error.name === 'AbortError') return true;
  if (axios.isAxiosError(error)) {
    return error.code === 'ERR_CANCELED';
  }
  return false;
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw new UploadCanceledError();
  }
}

function asUploadError(error: unknown): Error {
  if (error instanceof Error) return error;
  return new Error(String(error));
}

function normalizeCanceledError(error: unknown): UploadCanceledError | null {
  if (isUploadCanceledError(error)) {
    return new UploadCanceledError();
  }
  return null;
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

async function delay(ms: number, signal?: AbortSignal): Promise<void> {
  if (!signal) {
    await new Promise((resolve) => setTimeout(resolve, ms));
    return;
  }
  await new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new UploadCanceledError());
      return;
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      signal.removeEventListener('abort', onAbort);
      reject(new UploadCanceledError());
    };
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

export interface UploadFileOptions {
  file: File;
  parentId: string;
  chunkSize?: number;
  concurrency?: number;
  maxRetries?: number;
  onHashProgress?: HashProgressCallback;
  onFileHashed?: (fileHash: string) => void;
  onUploadProgress?: UploadProgressCallback;
  onUploadId?: (uploadId: string) => void;
  signal?: AbortSignal;
}

export async function uploadFile(options: UploadFileOptions): Promise<MergeChunksResponse> {
  const {
    file,
    parentId,
    chunkSize = 5 * 1024 * 1024,
    concurrency = 5,
    maxRetries = 3,
    onHashProgress,
    onFileHashed,
    onUploadProgress,
    onUploadId,
    signal,
  } = options;

  try {
    throwIfAborted(signal);
    const fileHash = await calculateFileHash(file, onHashProgress, chunkSize, { signal });
    onFileHashed?.(fileHash);
    throwIfAborted(signal);

    const preflightRequest: UploadPreflightRequest = {
      fileName: file.name,
      fileHash,
      fileSize: file.size,
      mimeType: file.type,
      parentId,
    };

    let preflightResponse: UploadPreflightResponse;
    try {
      preflightResponse = await http.post<UploadPreflightResponse>('/uploads/preflight', preflightRequest, {
        timeout: PREFLIGHT_TIMEOUT_MS,
        signal,
      });
    } catch (error) {
      const canceled = normalizeCanceledError(error);
      if (canceled) throw canceled;
      throw new Error('无法开始上传，请检查网络连接或与管理员联系。');
    }

    const { status, fileId, uploadId, uploadedChunkIndexes } = preflightResponse;
    if (status === 'COMPLETE') {
      onUploadProgress?.({
        percentage: 100,
        uploadedSize: file.size,
        totalSize: file.size,
      });
      return {
        fileId: fileId!,
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
        folderId: parentId,
        objectHash: fileHash,
        createdAt: new Date().toISOString(),
        downloadUrl: '',
      };
    }

    if (status !== 'UPLOADING' || !uploadId) {
      throw new Error('服务器未能正确初始化上传。');
    }

    onUploadId?.(uploadId);
    await uploadChunks({
      file,
      uploadId,
      chunkSize: preflightResponse.chunkSize || chunkSize,
      uploadedChunkIndexes: uploadedChunkIndexes || [],
      onProgress: onUploadProgress,
      concurrency,
      maxRetries,
      signal,
    });

    throwIfAborted(signal);
    const mergeRequest: MergeChunksRequest = {
      fileName: file.name,
      fileHash,
      mimeType: file.type,
      parentId,
    };

    try {
      const mergeResponse = await requestMergeAndWait(uploadId, mergeRequest, MERGE_TIMEOUT_MS, signal);
      onUploadProgress?.({
        percentage: 100,
        uploadedSize: file.size,
        totalSize: file.size,
      });
      return mergeResponse;
    } catch (error) {
      const canceled = normalizeCanceledError(error);
      if (canceled) throw canceled;

      if (isTimeoutOrNetworkError(error)) {
        const reconciled = await reconcileMergeResult({
          uploadId,
          mergeRequest,
          preflightRequest,
          file,
          signal,
        });
        if (reconciled) {
          onUploadProgress?.({
            percentage: 100,
            uploadedSize: file.size,
            totalSize: file.size,
          });
          return reconciled;
        }
      }
      const backendMessage = extractApiErrorMessage(error);
      throw new Error(backendMessage || '文件分片合并失败，请重试或联系管理员。');
    }
  } catch (error) {
    const canceled = normalizeCanceledError(error);
    if (canceled) throw canceled;
    throw asUploadError(error);
  }
}

export interface CompleteUploadSessionOptions {
  uploadId: string;
  fileHash: string;
  fileName: string;
  mimeType: string;
  parentId: string;
  conflictStrategy?: 'rename' | 'overwrite' | 'cancel';
  signal?: AbortSignal;
}

export async function completeUploadSession(options: CompleteUploadSessionOptions): Promise<MergeChunksResponse> {
  const {
    uploadId,
    fileHash,
    fileName,
    mimeType,
    parentId,
    conflictStrategy,
    signal,
  } = options;
  const mergeRequest: MergeChunksRequest = {
    fileHash,
    fileName,
    mimeType,
    parentId,
    conflictStrategy,
  };

  try {
    return await requestMergeAndWait(uploadId, mergeRequest, MERGE_TIMEOUT_MS, signal);
  } catch (error) {
    const canceled = normalizeCanceledError(error);
    if (canceled) throw canceled;
    const backendMessage = extractApiErrorMessage(error);
    throw new Error(backendMessage || '文件分片合并失败，请重试或联系管理员。');
  }
}

interface UploadChunkOptions {
  file: File;
  uploadId: string;
  chunkSize: number;
  uploadedChunkIndexes?: number[];
  onProgress?: UploadProgressCallback;
  concurrency?: number;
  maxRetries?: number;
  signal?: AbortSignal;
}

export async function uploadChunks(options: UploadChunkOptions): Promise<void> {
  const {
    file,
    uploadId,
    chunkSize,
    uploadedChunkIndexes = [],
    onProgress,
    concurrency = 5,
    maxRetries = 3,
    signal,
  } = options;

  throwIfAborted(signal);
  const totalChunks = Math.ceil(file.size / chunkSize);
  const chunkRequests: Array<() => Promise<void>> = [];

  let uploadedSize = 0;
  for (const index of uploadedChunkIndexes) {
    const start = index * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    uploadedSize += end - start;
  }

  for (let i = 0; i < totalChunks; i += 1) {
    if (uploadedChunkIndexes.includes(i)) {
      continue;
    }

    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const chunk = file.slice(start, end);

    chunkRequests.push(async () => {
      throwIfAborted(signal);
      const formData = new FormData();
      formData.append('chunk', chunk);
      formData.append('chunkIndex', String(i));

      for (let attempt = 1; attempt <= maxRetries; attempt += 1) {
        throwIfAborted(signal);
        try {
          await http.post(`/uploads/${uploadId}/chunk`, formData, {
            timeout: CHUNK_TIMEOUT_MS,
            signal,
          });
          uploadedSize += chunk.size;
          onProgress?.({
            percentage: Math.min(Math.round((uploadedSize / file.size) * 100), 100),
            uploadedSize,
            totalSize: file.size,
          });
          return;
        } catch (error) {
          const canceled = normalizeCanceledError(error);
          if (canceled) throw canceled;
          if (attempt === maxRetries) {
            throw new Error(`Chunk ${i} failed to upload after ${maxRetries} attempts.`);
          }
        }
      }
    });
  }

  await executeConcurrentTasks(chunkRequests, concurrency, signal);
}

interface ReconcileMergeOptions {
  uploadId: string;
  mergeRequest: MergeChunksRequest;
  preflightRequest: UploadPreflightRequest;
  file: File;
  signal?: AbortSignal;
}

async function reconcileMergeResult(options: ReconcileMergeOptions): Promise<MergeChunksResponse | null> {
  const {
    uploadId,
    mergeRequest,
    preflightRequest,
    file,
    signal,
  } = options;

  throwIfAborted(signal);
  try {
    const preflight = await http.post<UploadPreflightResponse>('/uploads/preflight', preflightRequest, {
      timeout: PREFLIGHT_TIMEOUT_MS,
      signal,
    });
    if (preflight.status === 'COMPLETE' && preflight.fileId) {
      return buildCompleteResponse({ fileId: preflight.fileId, mergeRequest, file });
    }

    const targetUploadId = preflight.uploadId || uploadId;
    try {
      return await requestMergeAndWait(targetUploadId, mergeRequest, MERGE_RETRY_TIMEOUT_MS, signal);
    } catch (retryError) {
      const canceled = normalizeCanceledError(retryError);
      if (canceled) throw canceled;
      if (!isTimeoutOrNetworkError(retryError)) {
        throw retryError;
      }

      const finalPreflight = await http.post<UploadPreflightResponse>('/uploads/preflight', preflightRequest, {
        timeout: PREFLIGHT_TIMEOUT_MS,
        signal,
      });
      if (finalPreflight.status === 'COMPLETE' && finalPreflight.fileId) {
        return buildCompleteResponse({ fileId: finalPreflight.fileId, mergeRequest, file });
      }
    }
  } catch (error) {
    const canceled = normalizeCanceledError(error);
    if (canceled) throw canceled;
    console.warn('merge reconcile failed', error);
  }

  return null;
}

function isTerminalJobStatus(status: string | undefined): boolean {
  return status === 'succeeded' || status === 'failed' || status === 'canceled';
}

function extractMergeResult(job: BackgroundJob<MergeChunksResponse>): MergeChunksResponse | null {
  if (job.status === 'succeeded') {
    const result = job.result;
    if (
      result
      && typeof result.fileId === 'string'
      && typeof result.fileName === 'string'
      && typeof result.downloadUrl === 'string'
    ) {
      return result;
    }
    throw new Error('Merge job succeeded but result is missing.');
  }

  if (job.status === 'failed' || job.status === 'canceled') {
    throw new Error(job.errorMessage || `Merge job ${job.status}.`);
  }
  return null;
}

async function requestMergeAndWait(
  uploadId: string,
  mergeRequest: MergeChunksRequest,
  timeoutMs: number,
  signal?: AbortSignal,
): Promise<MergeChunksResponse> {
  throwIfAborted(signal);
  const mergeJob = await http.post<BackgroundJob<MergeChunksResponse>>(`/uploads/${uploadId}/merge`, mergeRequest, {
    timeout: timeoutMs,
    signal,
  });

  const immediate = extractMergeResult(mergeJob);
  if (immediate) {
    return immediate;
  }
  return await pollMergeJob(mergeJob.jobId, MERGE_JOB_POLL_TIMEOUT_MS, signal);
}

async function pollMergeJob(jobId: string, timeoutMs: number, signal?: AbortSignal): Promise<MergeChunksResponse> {
  const startedAt = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    throwIfAborted(signal);
    if (Date.now() - startedAt > timeoutMs) {
      throw new Error('Merge job polling timeout.');
    }
    const job = await http.get<BackgroundJob<MergeChunksResponse>>(`/jobs/${jobId}`, undefined, {
      timeout: MERGE_RETRY_TIMEOUT_MS,
      signal,
    });
    const result = extractMergeResult(job);
    if (result) {
      return result;
    }
    if (isTerminalJobStatus(job.status)) {
      throw new Error(job.errorMessage || `Merge job ${job.status}.`);
    }
    await delay(MERGE_JOB_POLL_INTERVAL_MS, signal);
  }
}

async function executeConcurrentTasks(
  tasks: Array<() => Promise<void>>,
  limit: number,
  signal?: AbortSignal,
): Promise<void> {
  const results: Array<Promise<void>> = [];
  const executing: Array<Promise<void>> = [];

  for (const task of tasks) {
    throwIfAborted(signal);
    const p = Promise.resolve().then(task);
    results.push(p);

    if (limit <= tasks.length) {
      const e = p.finally(() => {
        const index = executing.indexOf(e);
        if (index >= 0) {
          executing.splice(index, 1);
        }
      });
      executing.push(e);
      if (executing.length >= limit) {
        await Promise.race(executing);
      }
    }
  }
  await Promise.all(results);
}
