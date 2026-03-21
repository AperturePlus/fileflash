import Mock from 'mockjs';
import { addLog, addNotification } from '../state';
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

function findCompletedFileByHash(fileHash: string) {
  return Object.values(vfsApi.getAll()).find(
    (node) => node.type === 'file' && !node.isTrashed && node.hash === fileHash,
  );
}

export const setupUploadMocks = () => {
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

    const existingFile = findCompletedFileByHash(fileHash);
    if (existingFile) {
      return {
        success: true,
        code: 200,
        message: 'File already exists',
        data: {
          status: 'COMPLETE',
          fileId: existingFile.id,
        },
      };
    }

    const existingSessionId = hashToSessionId.get(fileHash);
    if (existingSessionId && sessions.has(existingSessionId)) {
      const session = sessions.get(existingSessionId)!;
      return {
        success: true,
        code: 200,
        message: 'Resume upload session',
        data: {
          status: 'UPLOADING',
          uploadId: session.uploadId,
          chunkSize: session.chunkSize,
          uploadedChunkIndexes: [...session.uploadedChunkIndexes].sort((a, b) => a - b),
        },
      };
    }

    const uploadId = Mock.Random.guid();
    const chunkSize = 5 * 1024 * 1024;
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
      success: true,
      code: 200,
      message: 'Ready for upload',
      data: {
        status: 'UPLOADING',
        uploadId,
        chunkSize,
        uploadedChunkIndexes: [],
      },
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

  Mock.mock(/\/api\/v1\/uploads\/([^/]+)\/merge$/, 'post', async (options) => {
    const uploadId = (options.url.match(/\/api\/v1\/uploads\/([^/]+)\/merge/) || [])[1];
    const session = sessions.get(uploadId);

    if (!session) {
      return {
        success: false,
        code: 404,
        message: 'Upload session not found',
        data: null,
      };
    }

    const sortedIndexes = [...session.uploadedChunkIndexes].sort((a, b) => a - b);
    const sortedChunks = sortedIndexes.map((index) => session.chunks.get(index)).filter(Boolean) as Blob[];

    if (!sortedChunks.length) {
      return {
        success: false,
        code: 400,
        message: 'No uploaded chunks found',
        data: null,
      };
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

    addLog('file_upload', { fileId: created.id, fileName: created.name, size: created.size || 0 });
    addNotification(`Upload complete: ${created.name}`, true);

    return {
      success: true,
      code: 201,
      message: 'File created successfully',
      data: {
        fileId: created.id,
        fileName: created.name,
        fileSize: created.size || 0,
        mimeType: created.mimeType || 'application/octet-stream',
        folderId: created.parent || 'root',
        objectHash: session.fileHash,
        createdAt: created.createdAt,
        downloadUrl: `/api/v1/files/${created.id}/download`,
      },
    };
  });
};
