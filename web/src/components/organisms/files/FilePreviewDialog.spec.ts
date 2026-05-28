import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '../../../test/mount';
import { flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';
import FilePreviewDialog from './FilePreviewDialog.vue';

vi.mock('../../../api/file', () => ({
  previewFile: vi.fn(() => Promise.resolve(new Blob(['ok'], { type: 'text/plain' }))),
  getPreviewUrl: vi.fn(() => Promise.resolve({ url: '/mock-video.mp4', expiresAt: '2026-01-01T01:00:00Z' })),
  downloadFile: vi.fn(),
}));

vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({ default: '/mock.js' }));
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: vi.fn(),
}));

vi.mock('hls.js', () => ({
  default: class {
    static isSupported() { return false; }
    destroy() {}
    loadSource() {}
    attachMedia() {}
    on() {}
  },
}));
vi.mock('plyr', () => ({
  default: class {
    destroy() {}
  },
}));

const sampleFile = {
  itemType: 'file',
  id: 'f1',
  name: 'a.txt',
  size: 4,
  mimeType: 'text/plain',
  ownerName: 'me',
  updatedAt: '2026-01-01T00:00:00Z',
  createdAt: '2026-01-01T00:00:00Z',
  folderId: 'root',
};

describe('FilePreviewDialog', () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it('renders nothing when file is null', () => {
    const w = mount(FilePreviewDialog, { props: { file: null }, attachTo: document.body });
    expect(document.body.querySelector('.file-preview-dialog')).toBeNull();
    w.unmount();
  });

  it('renders overlay and FileDetailPanel when file is present', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile as any }, attachTo: document.body });
    await nextTick();
    const overlay = document.body.querySelector('.file-preview-dialog__overlay');
    expect(overlay).toBeTruthy();
    expect(document.body.querySelector('.detail')).toBeTruthy();
    w.unmount();
  });

  it('emits close on overlay self-click', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile as any }, attachTo: document.body });
    await nextTick();
    const overlay = document.body.querySelector('.file-preview-dialog__overlay') as HTMLElement;
    overlay.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(w.emitted('close')).toBeTruthy();
    w.unmount();
  });

  it('emits close on ESC keydown', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile as any }, attachTo: document.body });
    await nextTick();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(w.emitted('close')).toBeTruthy();
    w.unmount();
  });

  it('emits close on × button click', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile as any }, attachTo: document.body });
    await nextTick();
    const x = document.body.querySelector('.file-preview-dialog__close') as HTMLButtonElement;
    x.click();
    expect(w.emitted('close')).toBeTruthy();
    w.unmount();
  });

  it('renders VideoPreviewDialog instead of FileDetailPanel for video files', async () => {
    const videoFile = { ...sampleFile, id: 'v1', name: 'clip.mp4', mimeType: 'video/mp4' };
    const w = mount(FilePreviewDialog, { props: { file: videoFile as any }, attachTo: document.body });
    await nextTick();
    expect(document.body.querySelector('.video-preview-dialog')).toBeTruthy();
    expect(document.body.querySelector('.file-preview-dialog')).toBeNull();
    w.unmount();
  });

  it('hides download controls when showDownload is false', async () => {
    const w = mount(FilePreviewDialog, {
      props: { file: sampleFile as any, showDownload: false },
      attachTo: document.body,
    });
    await flushPromises();
    expect(document.body.textContent).not.toContain('Download');
    w.unmount();
  });
});
