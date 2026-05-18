import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import type { FolderItem } from '../types/file';

const {
  createFolderMock,
  deleteFolderMock,
  renameFolderMock,
  batchFilesMock,
  deleteFileMock,
  downloadFileMock,
  renameFileMock,
  getSharesMock,
  toastMock,
  confirmMock,
  eventEmitMock,
  newFolderCancelInstallMock,
  newFolderCancelUninstallMock,
} = vi.hoisted(() => ({
  createFolderMock: vi.fn(async () => ({ id: 'f-created', name: 'created', itemType: 'folder' })),
  deleteFolderMock: vi.fn(async () => ({})),
  renameFolderMock: vi.fn(async () => ({ id: 'f-1', name: 'renamed', itemType: 'folder' })),
  batchFilesMock: vi.fn(async () => ({ processed: 0, succeeded: 0, failed: 0, results: [] })),
  deleteFileMock: vi.fn(async () => ({})),
  downloadFileMock: vi.fn(async () => new Blob()),
  renameFileMock: vi.fn(async () => ({ id: 'file-1', name: 'renamed', itemType: 'file' })),
  getSharesMock: vi.fn(async () => ({ items: [], pagination: { hasNext: false } })),
  toastMock: vi.fn(),
  confirmMock: vi.fn(async () => true),
  eventEmitMock: vi.fn(),
  newFolderCancelInstallMock: vi.fn(),
  newFolderCancelUninstallMock: vi.fn(),
}));

const mockFileStore = {
  items: [] as FolderItem[],
  currentFolderId: 'root' as string | null,
  fetchFolderContents: vi.fn(async () => {}),
};

vi.mock('../store/file', () => ({
  useFileStore: () => mockFileStore,
}));

vi.mock('../store/settings', () => ({
  useSettingsStore: () => ({
    settings: {
      confirmDelete: false,
    },
  }),
}));

vi.mock('../store/locale', () => ({
  useLocaleStore: () => ({
    t: (key: string) => {
      const m: Record<string, string> = {
        'files.toolbar.newFolder': '新建文件夹',
        'files.owner.you': 'You',
        'files.rename.toast.createdFolder': '已创建文件夹“{folderName}”。',
        'files.rename.toast.createFailed': '创建文件夹失败。',
        'files.rename.toast.renamed': '已重命名为“{newName}”。',
        'files.rename.toast.renameFailed': '重命名失败。',
        'files.toast.newFolderCanceled': '已取消新建文件夹',
      };
      return m[key] || key;
    },
  }),
}));

vi.mock('../api/folder', () => ({
  createFolder: (...args: unknown[]) => createFolderMock(...args),
  deleteFolder: (...args: unknown[]) => deleteFolderMock(...args),
  renameFolder: (...args: unknown[]) => renameFolderMock(...args),
}));

vi.mock('../api/file', () => ({
  batchFiles: (...args: unknown[]) => batchFilesMock(...args),
  deleteFile: (...args: unknown[]) => deleteFileMock(...args),
  downloadFile: (...args: unknown[]) => downloadFileMock(...args),
  renameFile: (...args: unknown[]) => renameFileMock(...args),
}));

vi.mock('../api/share', () => ({
  getShares: (...args: unknown[]) => getSharesMock(...args),
}));

vi.mock('../utils/eventBus', () => ({
  eventBus: {
    emit: (...args: unknown[]) => eventEmitMock(...args),
  },
}));

vi.mock('../utils/ui', () => ({
  ui: {
    toast: (...args: unknown[]) => toastMock(...args),
    confirm: (...args: unknown[]) => confirmMock(...args),
  },
}));

vi.mock('./useNewFolderCancel', () => ({
  useNewFolderCancel: () => ({
    install: (...args: unknown[]) => newFolderCancelInstallMock(...args),
    uninstall: (...args: unknown[]) => newFolderCancelUninstallMock(...args),
  }),
}));

import { useFileActions } from './useFileActions';

function makeFolder(id: string, name: string): FolderItem {
  return {
    itemType: 'folder',
    id,
    name,
    size: 0,
    ownerName: 'You',
    updatedAt: '2026-05-13T00:00:00Z',
    createdAt: '2026-05-13T00:00:00Z',
    parentFolderId: 'root',
    permission: 'owner',
  };
}

describe('useFileActions new folder flow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 4, 13, 14, 52, 30));
    mockFileStore.items = [];
    mockFileStore.currentFolderId = 'root';
    mockFileStore.fetchFolderContents.mockClear();

    createFolderMock.mockClear();
    deleteFolderMock.mockClear();
    renameFolderMock.mockClear();
    batchFilesMock.mockClear();
    deleteFileMock.mockClear();
    downloadFileMock.mockClear();
    renameFileMock.mockClear();
    getSharesMock.mockClear();
    toastMock.mockClear();
    confirmMock.mockClear();
    eventEmitMock.mockClear();
    newFolderCancelInstallMock.mockClear();
    newFolderCancelUninstallMock.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('creates temp folder with localized default name and enters renaming', () => {
    const actions = useFileActions(ref('root'));

    actions.handleCreateFolder();

    expect(mockFileStore.items).toHaveLength(1);
    expect(mockFileStore.items[0]?.name).toBe('新建文件夹-20260513-145230');
    expect(actions.renameInputValue.value).toBe('新建文件夹-20260513-145230');
    expect(actions.renamingItemId.value?.startsWith('temp-new-folder-')).toBe(true);
    expect(newFolderCancelInstallMock).toHaveBeenCalledTimes(1);
  });

  it('appends sequence suffix when creating multiple folders in the same second', () => {
    const actions = useFileActions(ref('root'));

    actions.handleCreateFolder();
    actions.handleCreateFolder();
    actions.handleCreateFolder();

    expect(mockFileStore.items[0]?.name).toBe('新建文件夹-20260513-145230-3');
    expect(mockFileStore.items[1]?.name).toBe('新建文件夹-20260513-145230-2');
    expect(mockFileStore.items[2]?.name).toBe('新建文件夹-20260513-145230');
  });

  it('registerRenameInput + startRename focuses and selects input', async () => {
    const actions = useFileActions(ref('root'));
    const folder = makeFolder('folder-1', 'Docs');
    mockFileStore.items = [folder];
    const input = document.createElement('input');
    const focusSpy = vi.spyOn(input, 'focus');
    const selectSpy = vi.spyOn(input, 'select');

    const task = actions.startRename(folder);
    actions.registerRenameInput(folder.id, input);
    await task;

    expect(actions.renamingItemId.value).toBe(folder.id);
    expect(actions.renameInputValue.value).toBe('Docs');
    expect(focusSpy).toHaveBeenCalledTimes(1);
    expect(selectSpy).toHaveBeenCalledTimes(1);
  });

  it('empty name on finishRename cancels temp folder and does not create', async () => {
    const actions = useFileActions(ref('root'));
    actions.handleCreateFolder();
    actions.renameInputValue.value = '   ';

    await actions.finishRename();

    expect(createFolderMock).not.toHaveBeenCalled();
    expect(mockFileStore.items.find((item) => item.id.startsWith('temp-new-folder-'))).toBeUndefined();
    expect(actions.renamingItemId.value).toBe(null);
  });

  it('non-empty temp folder name on finishRename creates folder (including unchanged default name)', async () => {
    const actions = useFileActions(ref('root'));
    actions.handleCreateFolder();
    const createdName = actions.renameInputValue.value;

    await actions.finishRename();

    expect(createFolderMock).toHaveBeenCalledTimes(1);
    expect(createFolderMock).toHaveBeenCalledWith({ folderName: createdName, parentFolderId: 'root' });
    expect(mockFileStore.fetchFolderContents).toHaveBeenCalledWith('root', { silent: true });
    expect(actions.renamingItemId.value).toBe(null);
  });

  it('cancelRename removes temp folder immediately', () => {
    const actions = useFileActions(ref('root'));
    actions.handleCreateFolder();

    actions.cancelRename();

    expect(mockFileStore.items.find((item) => item.id.startsWith('temp-new-folder-'))).toBeUndefined();
    expect(actions.renamingItemId.value).toBe(null);
  });
});
