import Mock from 'mockjs';
import { addLog, addNotification, mockJobs } from '../state';
import { vfsApi } from '../vfs';
import { arrayBufferToBase64 } from '../../utils/hash';

type UploadSession = {
  uploadId: string;
  fileHash: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  parentId: string;
  chunkSize: number;
  chunks: Map<number, Blob>;
  uploadedChunkIndexes: Set<number>;
  createdAt: string;
};

const sessions = new Map<string, UploadSession>();
const hashToSessionId = new Map<string, string>();
const batchSessions = new Map<string, BatchUploadSession>();
const canceledUploadIds = new Set<string>();
const completedUploadIds = new Set<string>();

type BatchUploadItem = {
  clientFileId: string;
  fileName: string;
  fileHash: string;
  status: 'COMPLETE' | 'UPLOADING';
  fileId?: string;
  uploadId?: string;
};

type BatchUploadSession = {
  batchId: string;
  parentId: string;
  items: BatchUploadItem[];
  createdAt: string;
  updatedAt: string;
};

function findCompletedFileByHash(fileHash: string) {
  return Object.values(vfsApi.getAll()).find(
    (node) => node.type === 'file' && !node.isTrashed && node.hash === fileHash,
  );
}

function resolveUploadSession(
  fileHash: string,
  fileName: string,
  fileSize: number,
  mimeType: string,
  parentId: string,
) {
  const existingFile = findCompletedFileByHash(fileHash);
  if (existingFile) {
    return {
      status: 'COMPLETE' as const,
      fileId: existingFile.id,
    };
  }

  const existingSessionId = hashToSessionId.get(fileHash);
  if (existingSessionId && sessions.has(existingSessionId)) {
    const session = sessions.get(existingSessionId)!;
    return {
      status: 'UPLOADING' as const,
      uploadId: session.uploadId,
      chunkSize: session.chunkSize,
      uploadedChunkIndexes: [...session.uploadedChunkIndexes].sort((a, b) => a - b),
    };
  }

  const uploadId = Mock.Random.guid();
  const chunkSize = 5 * 1024 * 1024;
  canceledUploadIds.delete(uploadId);
  completedUploadIds.delete(uploadId);
  const newSession: UploadSession = {
    uploadId,
    fileHash,
    fileName,
    fileSize,
    mimeType: mimeType || 'application/octet-stream',
    parentId,
    chunkSize,
    chunks: new Map(),
    uploadedChunkIndexes: new Set(),
    createdAt: new Date().toISOString(),
  };

  sessions.set(uploadId, newSession);
  hashToSessionId.set(fileHash, uploadId);

  return {
    status: 'UPLOADING' as const,
    uploadId,
    chunkSize,
    uploadedChunkIndexes: [],
  };
}

function getBatchItemRuntimeStatus(item: BatchUploadItem) {
  const completed = findCompletedFileByHash(item.fileHash);
  if (completed) {
    return {
      status: 'COMPLETE' as const,
      fileId: completed.id,
      uploadId: item.uploadId,
      uploadedChunks: 0,
      totalChunks: 0,
      percentage: 100,
    };
  }

  if (item.uploadId && sessions.has(item.uploadId)) {
    const session = sessions.get(item.uploadId)!;
    const totalChunks = Math.max(1, Math.ceil(session.fileSize / session.chunkSize));
    const uploadedChunks = session.uploadedChunkIndexes.size;

    return {
      status: 'UPLOADING' as const,
      fileId: item.fileId,
      uploadId: item.uploadId,
      uploadedChunks,
      totalChunks,
      percentage: Math.floor((uploadedChunks / totalChunks) * 100),
    };
  }

  return {
    status: 'FAILED' as const,
    fileId: item.fileId,
    uploadId: item.uploadId,
    uploadedChunks: 0,
    totalChunks: 0,
    percentage: 0,
    message: 'Upload session not found or expired',
  };
}

export const setupUploadMocks = () => {
  Mock.mock(/\/api\/v1\/uploads\/batch-preflight$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}');
    const { parentId, files } = payload;

    if (!parentId || !Array.isArray(files) || files.length === 0) {
      return {
        success: false,
        code: 400,
        message: 'parentId and files[] are required',
        data: null,
      };
    }

    const invalidFile = files.find((file: any) => (
      !file?.clientFileId
      || !file?.fileHash
      || !file?.fileName
      || file?.fileSize === null
      || file?.fileSize === undefined
    ));

    if (invalidFile) {
      return {
        success: false,
        code: 400,
        message: 'Each file must include clientFileId, fileHash, fileName and fileSize',
        data: null,
      };
    }

    const batchId = Mock.Random.guid();
    const batchItems: BatchUploadItem[] = files.map((file: any) => {
      const resolved = resolveUploadSession(
        file.fileHash,
        file.fileName,
        Number(file.fileSize),
        file.mimeType || 'application/octet-stream',
        parentId,
      );

      return {
        clientFileId: String(file.clientFileId),
        fileName: String(file.fileName),
        fileHash: String(file.fileHash),
        status: resolved.status,
        fileId: resolved.fileId,
        uploadId: resolved.uploadId,
      };
    });

    const now = new Date().toISOString();
    batchSessions.set(batchId, {
      batchId,
      parentId,
      items: batchItems,
      createdAt: now,
      updatedAt: now,
    });

    const completeFiles = batchItems.filter((item) => item.status === 'COMPLETE').length;
    const uploadingFiles = batchItems.length - completeFiles;

    return {
      success: true,
      code: 200,
      message: 'Batch upload session initialized',
      data: {
        batchId,
        parentId,
        files: batchItems.map((item) => {
          const runtime = getBatchItemRuntimeStatus(item);
          return {
            clientFileId: item.clientFileId,
            fileName: item.fileName,
            status: item.status,
            fileId: runtime.fileId,
            uploadId: item.uploadId,
            chunkSize: runtime.totalChunks > 0 && item.uploadId ? sessions.get(item.uploadId)?.chunkSize : undefined,
            uploadedChunkIndexes: item.uploadId && sessions.has(item.uploadId)
              ? [...sessions.get(item.uploadId)!.uploadedChunkIndexes].sort((a, b) => a - b)
              : undefined,
          };
        }),
        summary: {
          totalFiles: batchItems.length,
          completeFiles,
          uploadingFiles,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/uploads\/batch\/([^/]+)\/complete$/, 'post', (options) => {
    const batchId = (options.url.match(/\/api\/v1\/uploads\/batch\/([^/]+)\/complete/) || [])[1];
    const payload = JSON.parse(options.body || '{}');
    const requestedFiles: Array<{ clientFileId: string }> = payload.files || [];
    const session = batchSessions.get(batchId);

    if (!session) {
      return {
        success: false,
        code: 404,
        message: 'Batch upload session not found',
        data: null,
      };
    }

    const targetClientIds = requestedFiles.length
      ? new Set(requestedFiles.map((item) => item.clientFileId))
      : new Set(session.items.map((item) => item.clientFileId));

    const results = session.items
      .filter((item) => targetClientIds.has(item.clientFileId))
      .map((item) => {
        const runtime = getBatchItemRuntimeStatus(item);
        if (runtime.status === 'COMPLETE' && runtime.fileId) {
          item.status = 'COMPLETE';
          item.fileId = runtime.fileId;
          return {
            clientFileId: item.clientFileId,
            fileName: item.fileName,
            success: true,
            fileId: runtime.fileId,
          };
        }

        const progressMessage = runtime.status === 'UPLOADING'
          ? `Upload in progress: ${runtime.uploadedChunks}/${runtime.totalChunks} chunks`
          : runtime.message;

        return {
          clientFileId: item.clientFileId,
          fileName: item.fileName,
          success: false,
          uploadId: item.uploadId,
          message: progressMessage || 'Upload is not complete',
        };
      });

    const succeeded = results.filter((item) => item.success).length;
    const failed = results.length - succeeded;
    session.updatedAt = new Date().toISOString();

    addLog('file_batch_upload_complete', {
      batchId,
      total: results.length,
      succeeded,
      failed,
    });

    return {
      success: true,
      code: 200,
      message: 'Batch completion evaluated',
      data: {
        batchId,
        completedAt: session.updatedAt,
        results,
        summary: {
          totalFiles: results.length,
          succeeded,
          failed,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/uploads\/batch\/([^/]+)$/, 'get', (options) => {
    const batchId = (options.url.match(/\/api\/v1\/uploads\/batch\/([^/?]+)/) || [])[1];
    const batch = batchSessions.get(batchId);

    if (!batch) {
      return {
        success: false,
        code: 404,
        message: 'Batch upload session not found',
        data: null,
      };
    }

    const files = batch.items.map((item) => {
      const runtime = getBatchItemRuntimeStatus(item);
      if (runtime.status === 'COMPLETE' && runtime.fileId) {
        item.status = 'COMPLETE';
        item.fileId = runtime.fileId;
      }

      return {
        clientFileId: item.clientFileId,
        fileName: item.fileName,
        status: runtime.status,
        fileId: runtime.fileId,
        uploadId: runtime.uploadId,
        uploadedChunks: runtime.uploadedChunks,
        totalChunks: runtime.totalChunks,
        percentage: runtime.percentage,
        message: runtime.message,
      };
    });

    const summary = {
      totalFiles: files.length,
      completeFiles: files.filter((item) => item.status === 'COMPLETE').length,
      uploadingFiles: files.filter((item) => item.status === 'UPLOADING').length,
      failedFiles: files.filter((item) => item.status === 'FAILED').length,
    };

    batch.updatedAt = new Date().toISOString();

    return {
      success: true,
      code: 200,
      message: 'Batch upload status fetched',
      data: {
        batchId: batch.batchId,
        parentId: batch.parentId,
        files,
        summary,
        updatedAt: batch.updatedAt,
      },
    };
  });

  Mock.mock(/\/api\/v1\/uploads\/preflight/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}');
    const { fileHash, fileName, fileSize, mimeType, parentId } = payload;

    if (!fileHash || !fileName || !fileSize || !parentId) {
      return {
        success: false,
        code: 400,
        message: 'fileHash, fileName, fileSize and parentId are required',
        data: null,
      };
    }

    const resolved = resolveUploadSession(fileHash, fileName, Number(fileSize), mimeType, parentId);

    return {
      success: true,
      code: 200,
      message: 'Ready for upload',
      data: resolved,
    };
  });

  Mock.mock(/\/api\/v1\/uploads\/([^/]+)\/chunk$/, 'post', (options) => {
    const uploadId = (options.url.match(/\/api\/v1\/uploads\/([^/]+)\/chunk/) || [])[1];
    const session = sessions.get(uploadId);

    if (!session) {
      return {
        success: false,
        code: 404,
        message: 'Upload session not found',
        data: null,
      };
    }

    const formData = options.body as FormData;
    const chunk = formData.get('chunk') as Blob | null;
    const chunkIndexText = formData.get('chunkIndex') as string | null;
    const chunkIndex = Number(chunkIndexText);

    if (!chunk || Number.isNaN(chunkIndex)) {
      return {
        success: false,
        code: 400,
        message: 'Invalid chunk payload',
        data: null,
      };
    }

    session.chunks.set(chunkIndex, chunk);
    session.uploadedChunkIndexes.add(chunkIndex);

    return {
      success: true,
      code: 200,
      message: `Chunk ${chunkIndex} uploaded`,
      data: null,
    };
  });

  Mock.mock(/\/api\/v1\/uploads\/([^/]+)\/cancel$/, 'post', (options) => {
    const uploadId = (options.url.match(/\/api\/v1\/uploads\/([^/]+)\/cancel/) || [])[1];
    const now = new Date().toISOString();

    if (completedUploadIds.has(uploadId)) {
      return {
        success: false,
        code: 409,
        message: 'Upload session already completed',
        data: null,
      };
    }

    if (canceledUploadIds.has(uploadId)) {
      return {
        success: true,
        code: 200,
        message: 'Upload session canceled',
        data: {
          uploadId,
          canceledAt: now,
        },
      };
    }

    const session = sessions.get(uploadId);
    if (!session) {
      return {
        success: false,
        code: 404,
        message: 'Upload session not found',
        data: null,
      };
    }

    sessions.delete(uploadId);
    hashToSessionId.delete(session.fileHash);
    canceledUploadIds.add(uploadId);

    for (const batch of batchSessions.values()) {
      const target = batch.items.find((item) => item.uploadId === uploadId);
      if (target) {
        target.status = 'UPLOADING';
        batch.updatedAt = now;
      }
    }

    return {
      success: true,
      code: 200,
      message: 'Upload session canceled',
      data: {
        uploadId,
        canceledAt: now,
      },
    };
  });

  Mock.mock(/\/api\/v1\/uploads\/([^/]+)\/merge$/, 'post', async (options) => {
    const uploadId = (options.url.match(/\/api\/v1\/uploads\/([^/]+)\/merge/) || [])[1];
    const mergeRequest = JSON.parse(options.body || '{}');
    const now = new Date().toISOString();
    const jobId = `job_${Mock.Random.guid()}`;
    const job = {
      jobId,
      taskType: 'task.upload_merge',
      status: 'pending',
      priority: 100,
      payload: {
        userId: 1,
        uploadId,
        mergeRequest,
      },
      result: {},
      errorMessage: null as string | null,
      attempt: 0,
      maxAttempts: 5,
      scheduledAt: now,
      startedAt: null as string | null,
      finishedAt: null as string | null,
      traceId: `mock-${jobId}`,
      idempotencyKey: `upload:1:${uploadId}:merge:mock`,
      cancelRequestedAt: null as string | null,
      requestedBy: '1',
      createdAt: now,
      updatedAt: now,
    };
    mockJobs[jobId] = job as any;

    setTimeout(() => {
      void (async () => {
        const runningAt = new Date().toISOString();
        job.status = 'running';
        job.startedAt = runningAt;
        job.updatedAt = runningAt;

        try {
          const session = sessions.get(uploadId);
          if (!session) {
            throw new Error('Upload session not found');
          }

          const sortedIndexes = [...session.uploadedChunkIndexes].sort((a, b) => a - b);
          const sortedChunks = sortedIndexes.map((index) => session.chunks.get(index)).filter(Boolean) as Blob[];
          if (!sortedChunks.length) {
            throw new Error('No uploaded chunks found');
          }

          const mergedBlob = new Blob(sortedChunks, { type: session.mimeType });
          const buffer = await mergedBlob.arrayBuffer();
          const base64Content = arrayBufferToBase64(buffer);

          const created = vfsApi.createFile(
            session.parentId,
            session.fileName,
            mergedBlob.size,
            session.mimeType,
            base64Content,
          );
          const node = vfsApi.get(created.id);
          if (node) {
            node.hash = session.fileHash;
            node.virusStatus = 'clean';
            node.updatedAt = new Date().toISOString();
          }

          sessions.delete(uploadId);
          hashToSessionId.delete(session.fileHash);
          completedUploadIds.add(uploadId);

          for (const batch of batchSessions.values()) {
            const target = batch.items.find((item) => item.fileHash === session.fileHash);
            if (target) {
              target.status = 'COMPLETE';
              target.fileId = created.id;
              batch.updatedAt = new Date().toISOString();
            }
          }

          addLog('file_upload', { fileId: created.id, fileName: created.name, size: created.size || 0 });
          addNotification(`Upload complete: ${created.name}`, true);

          job.status = 'succeeded';
          job.result = {
            fileId: created.id,
            fileName: created.name,
            fileSize: created.size || 0,
            mimeType: created.mimeType || 'application/octet-stream',
            folderId: created.parent || 'root',
            objectHash: session.fileHash,
            createdAt: created.createdAt,
            downloadUrl: `/api/v1/files/${created.id}/download`,
          };
          job.errorMessage = null;
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Merge failed';
          job.status = 'failed';
          job.errorMessage = message;
        } finally {
          const finishedAt = new Date().toISOString();
          job.finishedAt = finishedAt;
          job.updatedAt = finishedAt;
        }
      })();
    }, 120);

    return {
      success: true,
      code: 201,
      message: 'Upload merge job created',
      data: job,
    };
  });
};
