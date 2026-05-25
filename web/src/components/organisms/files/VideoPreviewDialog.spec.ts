import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { mount } from '../../../test/mount';
import VideoPreviewDialog from './VideoPreviewDialog.vue';

const mocks = vi.hoisted(() => ({
  getPreviewUrl: vi.fn(),
  previewFile: vi.fn(),
  downloadFile: vi.fn(),
  mountVideo: vi.fn(),
  destroyVideo: vi.fn(),
}));

vi.mock('../../../api/file', () => ({
  getPreviewUrl: mocks.getPreviewUrl,
  previewFile: mocks.previewFile,
  downloadFile: mocks.downloadFile,
}));

vi.mock('../../../composables/useVideoPlayer', () => ({
  useVideoPlayer: () => ({
    mount: mocks.mountVideo,
    destroy: mocks.destroyVideo,
  }),
}));

const videoFile = {
  itemType: 'file',
  id: 'v1',
  name: 'movie.mp4',
  size: 1024,
  mimeType: 'video/mp4',
  ownerName: 'me',
  updatedAt: '2026-01-01T00:00:00Z',
  createdAt: '2026-01-01T00:00:00Z',
  folderId: 'root',
};

describe('VideoPreviewDialog', () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.clearAllMocks();
    mocks.getPreviewUrl.mockResolvedValue({
      url: 'http://testserver/api/v1/files/v1/preview-stream?token=signed',
      expiresAt: '2026-01-01T04:00:00Z',
    });
  });

  it('loads a signed stream URL instead of downloading the preview blob', async () => {
    const wrapper = mount(VideoPreviewDialog, {
      props: { file: videoFile as any },
      attachTo: document.body,
    });

    await flushPromises();

    expect(mocks.getPreviewUrl).toHaveBeenCalledWith('v1');
    expect(mocks.previewFile).not.toHaveBeenCalled();
    expect(mocks.mountVideo).toHaveBeenCalledWith(expect.objectContaining({
      source: 'http://testserver/api/v1/files/v1/preview-stream?token=signed',
      isHls: false,
    }));
    expect(document.body.querySelector('.video-preview-dialog')).toBeTruthy();

    wrapper.unmount();
  });

  it('uses injected admin preview URL loader and hides download control', async () => {
    const previewUrlLoader = vi.fn().mockResolvedValue({
      url: 'http://testserver/api/v1/admin/files/v1/preview-stream?token=signed',
      expiresAt: '2026-01-01T04:00:00Z',
    });
    const wrapper = mount(VideoPreviewDialog, {
      props: {
        file: videoFile as any,
        previewUrlLoader,
        showDownload: false,
      },
      attachTo: document.body,
    });

    await flushPromises();

    expect(previewUrlLoader).toHaveBeenCalledWith('v1');
    expect(mocks.getPreviewUrl).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain('Download');
    expect(mocks.mountVideo).toHaveBeenCalledWith(expect.objectContaining({
      source: 'http://testserver/api/v1/admin/files/v1/preview-stream?token=signed',
    }));

    wrapper.unmount();
  });
});
