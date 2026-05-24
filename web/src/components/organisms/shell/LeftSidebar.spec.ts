import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../../test/mount';
import LeftSidebar from './LeftSidebar.vue';
import { useFileStore } from '../../../store/file';
import { eventBus } from '../../../utils/eventBus';

const activeUploadingCountRef = vi.hoisted(() => ({ value: 0, __v_isRef: true }));

const {
  getStarredFilesMock,
  getFolderPathMock,
  pushMock,
} = vi.hoisted(() => ({
  getStarredFilesMock: vi.fn(),
  getFolderPathMock: vi.fn(),
  pushMock: vi.fn(async () => undefined),
}));

vi.mock('../../../api/file', () => ({
  getStarredFiles: getStarredFilesMock,
}));

vi.mock('../../../api/folder', () => ({
  getFolderPath: getFolderPathMock,
}));

vi.mock('../../../store/upload', () => ({
  useUploadStore: () => ({
    activeUploadingCount: activeUploadingCountRef,
  }),
}));

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router');
  return {
    ...actual,
    useRouter: () => ({
      push: pushMock,
      currentRoute: { value: { path: '/shared' } },
    }) as any,
  };
});

const baseTimestamp = '2026-05-13T10:00:00Z';

const starredFile = {
  itemType: 'file' as const,
  id: 'file-1',
  name: 'notes.txt',
  size: 120,
  mimeType: 'text/plain',
  ownerName: 'You',
  updatedAt: baseTimestamp,
  createdAt: baseTimestamp,
  folderId: 'folder-1',
  isStarred: true,
};

const starredFolder = {
  itemType: 'folder' as const,
  id: 'folder-2',
  name: 'Design',
  size: 320,
  ownerName: 'You',
  updatedAt: baseTimestamp,
  createdAt: baseTimestamp,
  parentFolderId: 'root',
  isStarred: true,
};

const flush = async () => {
  await Promise.resolve();
  await nextTick();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await Promise.resolve();
  await nextTick();
};

describe('LeftSidebar', () => {
  beforeEach(() => {
    getStarredFilesMock.mockReset();
    getFolderPathMock.mockReset();
    pushMock.mockReset();
    getStarredFilesMock.mockResolvedValue({
      items: [starredFile, starredFolder],
      pagination: {
        totalItems: 2,
        totalPages: 1,
        perPage: 20,
        currentPage: 1,
        hasPrev: false,
        hasNext: false,
      },
    });
    getFolderPathMock.mockImplementation(async (folderId: string) => ({
      fullPath: `My Files/${folderId}`,
      pathItems: [
        { folderId: 'root', name: 'My Files' },
        { folderId, name: `Path-${folderId}` },
      ],
    }));
    activeUploadingCountRef.value = 0;
  });

  it('renders Starred section above Workspace Tree and shows path subtitle', async () => {
    const wrapper = mount(LeftSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          FileTreeNode: true,
          StorageStatusWidget: true,
        },
      },
    });
    await flush();
    await flush();

    const labels = wrapper.findAll('.tree-section .ff-text');
    expect(labels[0]?.text()).toContain('Starred');
    expect(labels[1]?.text()).toMatch(/工作区目录|Workspace Tree/);
    expect(getFolderPathMock).toHaveBeenCalledWith('folder-1');
    expect(getFolderPathMock).toHaveBeenCalledWith('folder-2');

    const subtitles = wrapper.findAll('.starred-path');
    expect(subtitles).toHaveLength(2);
    expect(subtitles[0]?.text()).toContain('Path-folder-1');
    expect(subtitles[1]?.text()).toContain('Path-folder-2');
    wrapper.unmount();
  });

  it('clicking starred file opens preview via fileStore.previewFile', async () => {
    const wrapper = mount(LeftSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          FileTreeNode: true,
          StorageStatusWidget: true,
        },
      },
    });
    await flush();
    const fileStore = useFileStore();

    const firstRow = wrapper.findAll('.starred-row')[0];
    await firstRow.trigger('click');

    expect(fileStore.previewFile).toMatchObject({ id: 'file-1', itemType: 'file' });
    wrapper.unmount();
  });

  it('clicking starred folder navigates to /files and target folder', async () => {
    const wrapper = mount(LeftSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          FileTreeNode: true,
          StorageStatusWidget: true,
        },
      },
    });
    await flush();
    const fileStore = useFileStore();
    const navigateSpy = vi.spyOn(fileStore, 'navigateToFolder');

    const folderRow = wrapper.findAll('.starred-row')[1];
    await folderRow.trigger('click');

    expect(pushMock).toHaveBeenCalledWith('/files');
    expect(navigateSpy).toHaveBeenCalledWith('folder-2');
    wrapper.unmount();
  });

  it('refresh-file-tree event refreshes starred data', async () => {
    const wrapper = mount(LeftSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          FileTreeNode: true,
          StorageStatusWidget: true,
        },
      },
    });
    await flush();
    const before = getStarredFilesMock.mock.calls.length;

    eventBus.emit('refresh-file-tree');
    await flush();

    expect(getStarredFilesMock.mock.calls.length).toBeGreaterThan(before);
    wrapper.unmount();
  });

  it('shows upload indicator on My Files when uploads are active', async () => {
    activeUploadingCountRef.value = 1;

    const wrapper = mount(LeftSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          FileTreeNode: true,
          StorageStatusWidget: true,
        },
      },
    });
    await flush();

    expect(wrapper.find('.upload-indicator').exists()).toBe(true);
    wrapper.unmount();
  });
});
