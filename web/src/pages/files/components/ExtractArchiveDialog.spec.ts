import { describe, expect, it, vi } from 'vitest';
import { mount } from '../../../test/mount';
import ExtractArchiveDialog from './ExtractArchiveDialog.vue';
import MoveItemDialog from '../../../components/common/MoveItemDialog.vue';

vi.mock('../../../store/file', () => ({
  useFileStore: () => ({
    navigateToFolder: vi.fn(),
  }),
}));

vi.mock('../../../utils/eventBus', () => ({
  eventBus: {
    emit: vi.fn(),
  },
}));

vi.mock('../../../api/file', () => ({
  requestArchivePreview: vi.fn(async () => ({ jobId: 'job-preview-1', status: 'pending', result: {} })),
  requestArchiveExtract: vi.fn(async () => ({ jobId: 'job-extract-1', status: 'pending', result: {} })),
}));

vi.mock('../../../api/folder', () => ({
  getFolderPath: vi.fn(async () => ({ pathItems: [{ folderId: 'root', name: 'My Files' }] })),
}));

vi.mock('../../../api/job', () => ({
  getJob: vi.fn(async () => ({
    jobId: 'job-preview-1',
    status: 'succeeded',
    result: {
      entries: [],
      summary: {
        fileCount: 0,
        dirCount: 0,
        totalUncompressedBytes: 0,
        truncated: false,
      },
    },
  })),
}));

describe('ExtractArchiveDialog', () => {
  it('uses modern tree variant for destination folder picker', () => {
    const wrapper = mount(ExtractArchiveDialog, {
      props: {
        isVisible: true,
        file: {
          itemType: 'file',
          id: 'zip-file',
          name: 'archive.zip',
          size: 123,
          mimeType: 'application/zip',
          ownerName: 'tester',
          createdAt: '2026-05-12T00:00:00Z',
          updatedAt: '2026-05-12T00:00:00Z',
          folderId: 'root',
        },
        currentFolderId: 'root',
      },
    });

    const picker = wrapper.findComponent(MoveItemDialog);
    expect(picker.exists()).toBe(true);
    expect(picker.props('treeVariant')).toBe('modern');
  });
});
