import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { mount } from '../../../test/mount';
import ContentPage from './ContentPage.vue';

const mocks = vi.hoisted(() => ({
  getAdminFiles: vi.fn(),
  getAdminFileDetail: vi.fn(),
  getAdminPreviewUrl: vi.fn(),
  previewAdminFile: vi.fn(),
  rescanAdminFile: vi.fn(),
}));

vi.mock('../../../api/file', () => ({
  getAdminFiles: mocks.getAdminFiles,
  getAdminFileDetail: mocks.getAdminFileDetail,
  getAdminPreviewUrl: mocks.getAdminPreviewUrl,
  previewAdminFile: mocks.previewAdminFile,
  rescanAdminFile: mocks.rescanAdminFile,
}));

vi.mock('../../../components/organisms/files/FilePreviewDialog.vue', () => ({
  default: {
    props: ['file'],
    template: '<div v-if="file" data-testid="admin-preview">{{ file.name }}</div>',
  },
}));

const auditItem = {
  id: '7',
  objectId: '20',
  name: 'report.pdf',
  size: 128,
  mimeType: 'application/pdf',
  hash: 'abcdef1234567890',
  virusStatus: 'clean',
  isShared: false,
  ownerName: 'Alice',
  uploadCount: 2,
  ownerCount: 1,
  scannedAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
  createdAt: '2026-01-01T00:00:00Z',
};

const auditDetail = {
  ...auditItem,
  objectHash: 'abcdef1234567890abcdef1234567890',
  hashAlgorithm: 'sha256',
  storageStatus: 'active',
  latestScan: {
    scanType: 'virus',
    scanResult: 'clean',
    virusStatus: 'clean',
    scannedAt: '2026-01-01T00:00:00Z',
    details: {},
  },
  owners: [
    {
      userId: '1',
      username: 'Alice',
      email: 'alice@example.com',
      fileCount: 2,
      firstUploadedAt: '2026-01-01T00:00:00Z',
      lastUploadedAt: '2026-01-01T00:00:00Z',
    },
  ],
};

describe('ContentPage', () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.clearAllMocks();
    mocks.getAdminFiles.mockResolvedValue({
      items: [auditItem],
      pagination: {
        totalItems: 1,
        totalPages: 1,
        perPage: 20,
        currentPage: 1,
        hasPrev: false,
        hasNext: false,
      },
    });
    mocks.getAdminFileDetail.mockResolvedValue(auditDetail);
    mocks.rescanAdminFile.mockResolvedValue({
      fileId: '7',
      virusStatus: 'pending',
      scannedAt: '2026-01-01T01:00:00Z',
    });
  });

  it('loads audit files, selects a row, shows ownership, previews, and rescans', async () => {
    const wrapper = mount(ContentPage, { attachTo: document.body });
    await flushPromises();

    expect(mocks.getAdminFiles).toHaveBeenCalledWith(expect.objectContaining({
      page: 1,
      perPage: 20,
    }));
    expect(wrapper.text()).toContain('report.pdf');
    expect(wrapper.text()).toContain('2 uploads');
    expect(wrapper.text()).toContain('1 owners');

    await wrapper.find('.row').trigger('click');
    await flushPromises();

    expect(mocks.getAdminFileDetail).toHaveBeenCalledWith('7');
    expect(wrapper.text()).toContain('alice@example.com');
    expect(wrapper.text()).toContain('Object');
    expect(wrapper.text()).toContain('20');

    await wrapper.find('.detail__actions .row__btn').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="admin-preview"]').text()).toContain('report.pdf');

    await wrapper.findAll('.detail__actions .row__btn')[1].trigger('click');
    await flushPromises();

    expect(mocks.rescanAdminFile).toHaveBeenCalledWith('7');
    expect(mocks.getAdminFileDetail).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });
});
