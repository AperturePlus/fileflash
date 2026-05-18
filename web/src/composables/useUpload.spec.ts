import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';

const emitSpy = vi.fn();

const mockFileStore = {
  items: [] as Array<{ id: string; itemType: 'file' | 'folder'; folderId?: string; parentFolderId?: string | null }>,
  path: [] as Array<{ name: string }>,
};

vi.mock('../store/file', () => ({
  useFileStore: () => mockFileStore,
}));

vi.mock('../store/settings', () => ({
  useSettingsStore: () => ({
    settings: {
      chunkSize: 4,
      maxConcurrentUploads: 2,
      autoRetryFailedUploads: true,
      retryAttempts: 2,
      uploadCompleteNotification: false,
    },
  }),
}));

vi.mock('../store/locale', () => ({
  useLocaleStore: () => ({
    t: (key: string) => {
      const messages: Record<string, string> = {
        'files.upload.toast.success': 'Uploaded {fileName}.',
        'files.upload.toast.failed': 'Upload of {fileName} failed: {reason}',
        'files.upload.toast.unknownError': 'Unknown error',
        'files.root.myFiles': 'My Files',
        'files.owner.you': 'You',
      };
      return messages[key] || key;
    },
  }),
}));

vi.mock('../utils/eventBus', () => ({
  eventBus: {
    emit: (...args: unknown[]) => emitSpy(...args),
  },
}));

vi.mock('../utils/uploader', () => ({
  uploadFile: vi.fn(),
}));

vi.mock('../utils/ui', () => ({
  ui: {
    toast: vi.fn(),
  },
}));

import { useUpload } from './useUpload';

function createInternalDropEvent(sourceItemIds: string[], options: { dropOnContainer: boolean }): DragEvent {
  const currentTarget = {} as EventTarget;
  const target = options.dropOnContainer ? currentTarget : ({} as EventTarget);

  return {
    preventDefault: vi.fn(),
    currentTarget,
    target,
    dataTransfer: {
      getData: (type: string) => (type === 'application/fileflash-item-ids' ? JSON.stringify(sourceItemIds) : ''),
      types: ['application/fileflash-item-ids'],
    } as unknown as DataTransfer,
  } as unknown as DragEvent;
}

describe('useUpload internal drag handling', () => {
  beforeEach(() => {
    emitSpy.mockReset();
    mockFileStore.items = [
      { id: 'file-1', itemType: 'file', folderId: '10' },
      { id: 'folder-1', itemType: 'folder', parentFolderId: '8' },
    ];
    mockFileStore.path = [{ name: 'Current Folder' }];
  });

  it('ignores bubbled internal drop events from child elements', async () => {
    const { handleDrop } = useUpload(ref('42'));
    const event = createInternalDropEvent(['file-1'], { dropOnContainer: false });

    await handleDrop(event);

    expect(emitSpy).not.toHaveBeenCalled();
  });

  it('emits move-items when internal drop lands on container itself', async () => {
    const { handleDrop } = useUpload(ref('42'));
    const event = createInternalDropEvent(['file-1'], { dropOnContainer: true });

    await handleDrop(event);

    expect(emitSpy).toHaveBeenCalledWith('move-items', {
      sourceItemIds: ['file-1'],
      targetFolderId: '42',
      targetFolderName: 'Current Folder',
    });
  });
});
