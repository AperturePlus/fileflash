import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useUploadStore } from './upload';
import { useLocaleStore } from './locale';
import type { MergeChunksResponse, UploadRecoverableSession } from '../types/file';

const uploadFileMock = vi.fn();
const completeUploadSessionMock = vi.fn();
const cancelUploadSessionMock = vi.fn(async (_uploadId: string) => ({
  uploadId: 'upload-1',
  canceledAt: '2026-05-24T00:00:00Z',
}));
const getRecoverableUploadsMock = vi.fn(async () => [] as UploadRecoverableSession[]);

vi.mock('../utils/uploader', () => ({
  uploadFile: (options: unknown) => uploadFileMock(options),
  completeUploadSession: (options: unknown) => completeUploadSessionMock(options),
  isUploadCanceledError: (error: unknown) => error instanceof Error && error.name === 'UploadCanceledError',
}));

vi.mock('../api/file', () => ({
  cancelUploadSession: (uploadId: string) => cancelUploadSessionMock(uploadId),
  getRecoverableUploads: () => getRecoverableUploadsMock(),
}));

vi.mock('../utils/ui', () => ({
  ui: {
    toast: vi.fn(),
  },
}));

vi.mock('../utils/eventBus', () => ({
  eventBus: {
    emit: vi.fn(),
  },
}));

function createPendingUploadPromise(options: {
  onUploadId?: (uploadId: string) => void;
  signal?: AbortSignal;
}) {
  return new Promise<MergeChunksResponse>((_resolve, reject) => {
    options.onUploadId?.('upload-1');
    options.signal?.addEventListener('abort', () => {
      const error = new Error('canceled');
      error.name = 'UploadCanceledError';
      reject(error);
    }, { once: true });
  });
}

describe('upload store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    uploadFileMock.mockReset();
    completeUploadSessionMock.mockReset();
    cancelUploadSessionMock.mockClear();
    getRecoverableUploadsMock.mockReset();
    getRecoverableUploadsMock.mockResolvedValue([]);
  });

  it('keeps task state across multiple store consumers', async () => {
    uploadFileMock.mockImplementation((options: any) => createPendingUploadPromise(options));

    const storeA = useUploadStore();
    await storeA.startUpload(new File(['hello'], 'demo.txt', { type: 'text/plain' }), 'root');

    const storeB = useUploadStore();
    expect(storeB.tasks).toHaveLength(1);
    expect(storeB.tasks[0]?.name).toBe('demo.txt');
    expect(storeB.activeUploadingCount).toBe(1);
  });

  it('cancelTask aborts upload and calls backend cancel endpoint', async () => {
    uploadFileMock.mockImplementation((options: any) => createPendingUploadPromise(options));

    const store = useUploadStore();
    const taskId = await store.startUpload(new File(['hello'], 'cancel-me.txt', { type: 'text/plain' }), 'root');

    await Promise.resolve();
    const task = store.tasks.find((item) => item.id === taskId);
    expect(task?.uploadId).toBe('upload-1');

    await store.cancelTask(taskId);
    await Promise.resolve();

    expect(cancelUploadSessionMock).toHaveBeenCalledWith('upload-1');
    const canceledTask = store.tasks.find((item) => item.id === taskId);
    expect(canceledTask?.status).toBe('canceled');
  });

  it('bootstrapRecovery hydrates persisted tasks and reconciles progress from backend', async () => {
    localStorage.setItem('fileflash-upload-tasks-v1', JSON.stringify([{
      id: 'persist-1',
      name: 'demo.txt',
      parentId: 'root',
      uploadId: 'upload-keep',
      fileHash: 'a'.repeat(64),
      mimeType: 'text/plain',
      status: 'uploading',
      progress: { percentage: 10, uploadedSize: 10, totalSize: 100 },
      errorMessage: null,
      createdAt: '2026-05-24T01:00:00Z',
      updatedAt: '2026-05-24T01:00:00Z',
    }]));
    getRecoverableUploadsMock.mockResolvedValue([{
      uploadId: 'upload-keep',
      fileName: 'demo.txt',
      fileSize: 100,
      uploadedBytes: 60,
      chunkSize: 20,
      fileHash: 'a'.repeat(64),
      mimeType: 'text/plain',
      parentId: 'root',
      updatedAt: '2026-05-24T01:10:00Z',
      expiredAt: '2026-05-25T01:00:00Z',
      status: 'uploading',
    }]);

    const store = useUploadStore();
    await store.bootstrapRecovery();

    expect(store.tasks).toHaveLength(1);
    expect(store.tasks[0]?.status).toBe('paused');
    expect(store.tasks[0]?.progress.uploadedSize).toBe(60);
    expect(store.tasks[0]?.progress.percentage).toBe(60);
  });

  it('bootstrapRecovery marks missing backend sessions as expired', async () => {
    localStorage.setItem('fileflash-upload-tasks-v1', JSON.stringify([{
      id: 'persist-2',
      name: 'stale.txt',
      parentId: 'root',
      uploadId: 'upload-missing',
      fileHash: 'b'.repeat(64),
      mimeType: 'text/plain',
      status: 'paused',
      progress: { percentage: 20, uploadedSize: 20, totalSize: 100 },
      errorMessage: null,
      createdAt: '2026-05-24T01:00:00Z',
      updatedAt: '2026-05-24T01:00:00Z',
    }]));
    getRecoverableUploadsMock.mockResolvedValue([]);

    const store = useUploadStore();
    const localeStore = useLocaleStore();
    await store.bootstrapRecovery();

    expect(store.tasks).toHaveLength(1);
    expect(store.tasks[0]?.status).toBe('paused');
    expect(store.tasks[0]?.errorMessage).toBe(localeStore.t('files.upload.hint.sessionExpired'));
  });

  it('resumeTask reuses upload flow for resumable task', async () => {
    localStorage.setItem('fileflash-upload-tasks-v1', JSON.stringify([{
      id: 'persist-3',
      name: 'resume.txt',
      parentId: 'root',
      uploadId: 'upload-resume',
      fileHash: 'c'.repeat(64),
      mimeType: 'text/plain',
      status: 'paused',
      progress: { percentage: 50, uploadedSize: 50, totalSize: 100 },
      errorMessage: null,
      createdAt: '2026-05-24T01:00:00Z',
      updatedAt: '2026-05-24T01:00:00Z',
    }]));
    getRecoverableUploadsMock.mockResolvedValue([{
      uploadId: 'upload-resume',
      fileName: 'resume.txt',
      fileSize: 100,
      uploadedBytes: 50,
      chunkSize: 10,
      fileHash: 'c'.repeat(64),
      mimeType: 'text/plain',
      parentId: 'root',
      updatedAt: '2026-05-24T01:10:00Z',
      expiredAt: '2026-05-25T01:00:00Z',
      status: 'uploading',
    }]);
    uploadFileMock.mockImplementation(async (options: any) => {
      options.onFileHashed?.('c'.repeat(64));
      options.onUploadId?.('upload-resume');
      options.onUploadProgress?.({ percentage: 100, uploadedSize: 100, totalSize: 100 });
      return {
        fileId: 'file-100',
        fileName: 'resume.txt',
        fileSize: 100,
        mimeType: 'text/plain',
        folderId: 'root',
        objectHash: 'c'.repeat(64),
        createdAt: '2026-05-24T01:11:00Z',
        downloadUrl: '/api/v1/files/file-100/download',
      };
    });

    const store = useUploadStore();
    await store.bootstrapRecovery();
    await store.resumeTask('persist-3', new File(['x'.repeat(100)], 'resume.txt', { type: 'text/plain' }));
    await Promise.resolve();

    expect(uploadFileMock).toHaveBeenCalledTimes(1);
    expect(store.tasks.find((task) => task.id === 'persist-3')?.status).toBe('succeeded');
  });

  it('auto merge runs only for fully uploaded recoverable sessions', async () => {
    getRecoverableUploadsMock.mockResolvedValue([
      {
        uploadId: 'upload-complete',
        fileName: 'full.bin',
        fileSize: 100,
        uploadedBytes: 100,
        chunkSize: 10,
        fileHash: 'd'.repeat(64),
        mimeType: 'application/octet-stream',
        parentId: 'root',
        updatedAt: '2026-05-24T02:00:00Z',
        expiredAt: '2026-05-25T02:00:00Z',
        status: 'uploading',
      },
      {
        uploadId: 'upload-partial',
        fileName: 'part.bin',
        fileSize: 100,
        uploadedBytes: 40,
        chunkSize: 10,
        fileHash: 'e'.repeat(64),
        mimeType: 'application/octet-stream',
        parentId: 'root',
        updatedAt: '2026-05-24T02:00:00Z',
        expiredAt: '2026-05-25T02:00:00Z',
        status: 'uploading',
      },
    ]);
    completeUploadSessionMock.mockResolvedValue({
      fileId: 'file-merged',
      fileName: 'full.bin',
      fileSize: 100,
      mimeType: 'application/octet-stream',
      folderId: 'root',
      objectHash: 'd'.repeat(64),
      createdAt: '2026-05-24T02:01:00Z',
      downloadUrl: '/api/v1/files/file-merged/download',
    });

    const store = useUploadStore();
    await store.bootstrapRecovery();

    expect(completeUploadSessionMock).toHaveBeenCalledTimes(1);
    expect((completeUploadSessionMock.mock.calls[0]?.[0] as { uploadId: string }).uploadId).toBe('upload-complete');
    expect(store.tasks.find((task) => task.uploadId === 'upload-partial')?.status).toBe('paused');
  });
});
