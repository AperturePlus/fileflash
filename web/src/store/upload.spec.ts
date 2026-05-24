import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useUploadStore } from './upload';
import type { MergeChunksResponse } from '../types/file';

const uploadFileMock = vi.fn();
const cancelUploadSessionMock = vi.fn(async (_uploadId: string) => ({
  uploadId: 'upload-1',
  canceledAt: '2026-05-24T00:00:00Z',
}));

vi.mock('../utils/uploader', () => ({
  uploadFile: (options: unknown) => uploadFileMock(options),
  isUploadCanceledError: (error: unknown) => error instanceof Error && error.name === 'UploadCanceledError',
}));

vi.mock('../api/file', () => ({
  cancelUploadSession: (uploadId: string) => cancelUploadSessionMock(uploadId),
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
    uploadFileMock.mockReset();
    cancelUploadSessionMock.mockClear();
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
});
