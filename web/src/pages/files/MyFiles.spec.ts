import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../test/mount';
import MyFiles from './MyFiles.vue';
import { useFileStore } from '../../store/file';
import { eventBus } from '../../utils/eventBus';

const {
  openPreviewMock,
  getFolderContentsMock,
  getFolderPathMock,
  toggleFileStarMock,
  toggleFolderStarMock,
  toastMock,
} = vi.hoisted(() => ({
  openPreviewMock: vi.fn(),
  getFolderContentsMock: vi.fn(async () => ({ items: [] })),
  getFolderPathMock: vi.fn(async () => ({ pathItems: [{ folderId: 'root', name: 'My Files' }] })),
  toggleFileStarMock: vi.fn(async () => ({})),
  toggleFolderStarMock: vi.fn(async () => ({})),
  toastMock: vi.fn(),
}));

vi.mock('../../composables/useFilePreview', () => ({
  useFilePreview: () => ({
    openPreview: openPreviewMock,
  }),
}));

vi.mock('../../api/file', () => ({
  toggleFileStar: toggleFileStarMock,
}));

vi.mock('../../api/folder', () => ({
  getFolderContents: getFolderContentsMock,
  getFolderPath: getFolderPathMock,
  toggleFolderStar: toggleFolderStarMock,
}));

vi.mock('../../utils/ui', () => ({
  ui: {
    toast: toastMock,
    confirm: vi.fn(),
    promptText: vi.fn(),
    copyText: vi.fn(),
    resolveConfirm: vi.fn(),
    resolvePrompt: vi.fn(),
    dismissToast: vi.fn(),
  },
  uiState: {
    confirm: null,
    prompt: null,
    toasts: [],
  },
}));

describe('MyFiles', () => {
  beforeEach(() => {
    openPreviewMock.mockReset();
    getFolderContentsMock.mockClear();
    getFolderPathMock.mockClear();
    toggleFileStarMock.mockReset();
    toggleFolderStarMock.mockReset();
    toastMock.mockReset();
  });

  it('activating archive file opens extract dialog and skips normal preview', async () => {
    const wrapper = mount(MyFiles);
    const fileStore = useFileStore();
    fileStore.items = [{
      itemType: 'file',
      id: 'zip-file',
      name: 'archive.zip',
      size: 123,
      mimeType: 'application/zip',
      ownerName: 'tester',
      createdAt: '2026-05-12T00:00:00Z',
      updatedAt: '2026-05-12T00:00:00Z',
      folderId: 'root',
    }];
    await nextTick();

    const row = wrapper.findAll('.row')[0];
    await row.trigger('dblclick');
    await nextTick();

    expect(openPreviewMock).not.toHaveBeenCalled();
    const dialog = wrapper.findComponent({ name: 'ExtractArchiveDialog' });
    expect(dialog.props('isVisible')).toBe(true);
    expect((dialog.props('file') as { id: string }).id).toBe('zip-file');
  });

  it('activating non-archive file keeps normal preview behavior', async () => {
    const wrapper = mount(MyFiles);
    const fileStore = useFileStore();
    fileStore.items = [{
      itemType: 'file',
      id: 'txt-file',
      name: 'notes.txt',
      size: 123,
      mimeType: 'text/plain',
      ownerName: 'tester',
      createdAt: '2026-05-12T00:00:00Z',
      updatedAt: '2026-05-12T00:00:00Z',
      folderId: 'root',
    }];
    await nextTick();

    const row = wrapper.findAll('.row')[0];
    await row.trigger('dblclick');
    await nextTick();

    expect(openPreviewMock).toHaveBeenCalledTimes(1);
    expect(openPreviewMock.mock.calls[0][0]).toMatchObject({ id: 'txt-file' });
    const dialog = wrapper.findComponent({ name: 'ExtractArchiveDialog' });
    expect(dialog.props('isVisible')).toBe(false);
  });

  it('star success emits refresh-file-tree event', async () => {
    const wrapper = mount(MyFiles);
    const fileStore = useFileStore();
    const emitSpy = vi.spyOn(eventBus, 'emit');

    const fileItem = {
      itemType: 'file' as const,
      id: 'txt-file',
      name: 'notes.txt',
      size: 123,
      mimeType: 'text/plain',
      ownerName: 'tester',
      createdAt: '2026-05-12T00:00:00Z',
      updatedAt: '2026-05-12T00:00:00Z',
      folderId: 'root',
      isStarred: false,
    };
    fileStore.items = [fileItem];
    await nextTick();

    const table = wrapper.findComponent({ name: 'FileTable' });
    table.vm.$emit('toggleStar', fileItem);
    await nextTick();
    await Promise.resolve();

    expect(toggleFileStarMock).toHaveBeenCalledWith('txt-file', true);
    expect(emitSpy).toHaveBeenCalledWith('refresh-file-tree');
    emitSpy.mockRestore();
  });

  it('star failure shows toast with backend message', async () => {
    toggleFileStarMock.mockRejectedValueOnce({
      response: { data: { message: '已达收藏上限 20' } },
    });

    const wrapper = mount(MyFiles);
    const fileStore = useFileStore();

    const fileItem = {
      itemType: 'file' as const,
      id: 'txt-file',
      name: 'notes.txt',
      size: 123,
      mimeType: 'text/plain',
      ownerName: 'tester',
      createdAt: '2026-05-12T00:00:00Z',
      updatedAt: '2026-05-12T00:00:00Z',
      folderId: 'root',
      isStarred: false,
    };
    fileStore.items = [fileItem];
    await nextTick();

    const table = wrapper.findComponent({ name: 'FileTable' });
    table.vm.$emit('toggleStar', fileItem);
    await nextTick();
    await Promise.resolve();

    expect(toastMock).toHaveBeenCalledTimes(1);
    expect((toastMock.mock.calls[0]?.[0] as { type: string; message: string }).type).toBe('error');
    expect((toastMock.mock.calls[0]?.[0] as { type: string; message: string }).message).toContain('已达收藏上限 20');
  });
});
