import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../test/mount';
import MyFiles from './MyFiles.vue';
import { useFileStore } from '../../store/file';

const {
  openPreviewMock,
  getFolderContentsMock,
  getFolderPathMock,
} = vi.hoisted(() => ({
  openPreviewMock: vi.fn(),
  getFolderContentsMock: vi.fn(async () => ({ items: [] })),
  getFolderPathMock: vi.fn(async () => ({ pathItems: [{ folderId: 'root', name: 'My Files' }] })),
}));

vi.mock('../../composables/useFilePreview', () => ({
  useFilePreview: () => ({
    openPreview: openPreviewMock,
  }),
}));

vi.mock('../../api/file', () => ({
  toggleFileStar: vi.fn(async () => ({})),
}));

vi.mock('../../api/folder', () => ({
  getFolderContents: getFolderContentsMock,
  getFolderPath: getFolderPathMock,
  toggleFolderStar: vi.fn(async () => ({})),
}));

describe('MyFiles', () => {
  beforeEach(() => {
    openPreviewMock.mockReset();
    getFolderContentsMock.mockClear();
    getFolderPathMock.mockClear();
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
});
