import { describe, it, expect, beforeEach, vi } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../../test/mount';
import RightSidebar from './RightSidebar.vue';

const mocks = vi.hoisted(() => {
  const previewFileMock = vi.fn();
  const downloadFileMock = vi.fn();
  const fileStoreMock: { selectedFile: any } = { selectedFile: null };

  const viewerDestroyMock = vi.fn();
  const viewerConstructorMock = vi.fn(class {
    destroy = viewerDestroyMock;
  });

  const plyrDestroyMock = vi.fn();
  const plyrConstructorMock = vi.fn(class {
    destroy = plyrDestroyMock;
  });

  const hlsLoadSourceMock = vi.fn();
  const hlsAttachMediaMock = vi.fn();
  const hlsOnMock = vi.fn();
  const hlsDestroyMock = vi.fn();
  const HlsMock = vi.fn(class {
    loadSource = hlsLoadSourceMock;
    attachMedia = hlsAttachMediaMock;
    on = hlsOnMock;
    destroy = hlsDestroyMock;
  });

  (HlsMock as unknown as { isSupported: () => boolean; Events: { ERROR: string } }).isSupported = () => true;
  (HlsMock as unknown as { Events: { ERROR: string } }).Events = { ERROR: 'error' };

  const getDocumentMock = vi.fn();

  return {
    previewFileMock,
    downloadFileMock,
    fileStoreMock,
    viewerDestroyMock,
    viewerConstructorMock,
    plyrDestroyMock,
    plyrConstructorMock,
    hlsLoadSourceMock,
    hlsAttachMediaMock,
    hlsOnMock,
    hlsDestroyMock,
    HlsMock,
    getDocumentMock,
  };
});

vi.mock('../../../api/file', () => ({
  previewFile: mocks.previewFileMock,
  downloadFile: mocks.downloadFileMock,
}));

vi.mock('../../../store/file', () => ({
  useFileStore: () => mocks.fileStoreMock,
}));

vi.mock('viewerjs', () => ({
  default: mocks.viewerConstructorMock,
}));

vi.mock('plyr', () => ({
  default: mocks.plyrConstructorMock,
}));

vi.mock('hls.js', () => ({
  default: mocks.HlsMock,
}));

vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({
  default: '/mock-pdf-worker.js',
}));

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: mocks.getDocumentMock,
}));

function createFile(overrides: Partial<Record<string, any>> = {}) {
  return {
    itemType: 'file',
    id: 'file-id-1',
    name: 'sample.pdf',
    size: 1024,
    mimeType: 'application/pdf',
    ownerName: 'You',
    updatedAt: '2026-01-01T00:00:00Z',
    createdAt: '2026-01-01T00:00:00Z',
    folderId: 'root',
    ...overrides,
  };
}

async function flushUi() {
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
  await new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}

describe('components/organisms/shell/RightSidebar', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mocks.previewFileMock.mockReset();
    mocks.downloadFileMock.mockReset();
    mocks.viewerConstructorMock.mockClear();
    mocks.viewerDestroyMock.mockClear();
    mocks.plyrConstructorMock.mockClear();
    mocks.plyrDestroyMock.mockClear();
    mocks.hlsLoadSourceMock.mockClear();
    mocks.hlsAttachMediaMock.mockClear();
    mocks.hlsOnMock.mockClear();
    mocks.hlsDestroyMock.mockClear();
    mocks.getDocumentMock.mockReset();
    mocks.fileStoreMock.selectedFile = null;

    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      clearRect: vi.fn(),
    } as unknown as CanvasRenderingContext2D);

    // Stable ResizeObserver for component tests.
    (globalThis as { ResizeObserver?: typeof ResizeObserver }).ResizeObserver = class ResizeObserverMock {
      observe() {}
      disconnect() {}
      unobserve() {}
    } as unknown as typeof ResizeObserver;
  });

  it('renders first PDF page via pdf.js path', async () => {
    const pageMock = {
      getViewport: vi.fn(({ scale }: { scale: number }) => ({ width: 640 * scale, height: 800 * scale })),
      render: vi.fn(() => ({
        promise: Promise.resolve(),
        cancel: vi.fn(),
      })),
      cleanup: vi.fn(),
    };
    const pdfDocMock = {
      numPages: 2,
      getPage: vi.fn().mockResolvedValue(pageMock),
      destroy: vi.fn(),
    };

    mocks.previewFileMock.mockResolvedValue(new Blob(['mock-pdf'], { type: 'application/pdf' }));
    mocks.getDocumentMock.mockReturnValue({
      promise: Promise.resolve(pdfDocMock),
    });
    mocks.fileStoreMock.selectedFile = createFile({
      name: 'project-plan.pdf',
      mimeType: 'application/octet-stream',
    });

    const wrapper = mount(RightSidebar, { props: { visible: true } });
    await flushUi();
    await vi.waitFor(() => {
      expect(pdfDocMock.getPage).toHaveBeenCalledWith(1);
    });

    expect(mocks.getDocumentMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('Page 1 / 2');
    expect(wrapper.text()).not.toContain('Browser PDF fallback mode');
  });

  it('falls back to safe PDF mode without auto-embedding when canvas render fails', async () => {
    const pageMock = {
      getViewport: vi.fn(({ scale }: { scale: number }) => ({ width: 640 * scale, height: 800 * scale })),
      render: vi.fn(() => ({
        promise: Promise.reject(new Error('render failed')),
        cancel: vi.fn(),
      })),
      cleanup: vi.fn(),
    };
    const pdfDocMock = {
      numPages: 1,
      getPage: vi.fn().mockResolvedValue(pageMock),
      destroy: vi.fn(),
    };

    mocks.previewFileMock.mockResolvedValue(new Blob(['mock-pdf'], { type: 'application/pdf' }));
    mocks.getDocumentMock.mockReturnValue({
      promise: Promise.resolve(pdfDocMock),
    });
    mocks.fileStoreMock.selectedFile = createFile({
      name: 'broken.pdf',
      mimeType: 'application/octet-stream',
    });

    const wrapper = mount(RightSidebar, { props: { visible: true } });
    await flushUi();
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Browser PDF fallback mode');
    });

    expect(wrapper.text()).toContain('In-app PDF rendering is unavailable in this environment.');
    expect(wrapper.find('iframe[title="PDF preview fallback"]').exists()).toBe(false);
  });

  it('initializes hls.js and Plyr for m3u8 video preview', async () => {
    mocks.previewFileMock.mockResolvedValue(new Blob(['#EXTM3U\n#EXT-X-VERSION:3'], { type: 'application/vnd.apple.mpegurl' }));
    mocks.fileStoreMock.selectedFile = createFile({
      name: 'preview.m3u8',
      mimeType: 'application/octet-stream',
    });

    const wrapper = mount(RightSidebar, { props: { visible: true } });
    await flushUi();
    await vi.waitFor(() => {
      expect(mocks.HlsMock).toHaveBeenCalledTimes(1);
    });

    expect(wrapper.find('video[playsinline]').exists()).toBe(true);
    expect(mocks.hlsLoadSourceMock).toHaveBeenCalledTimes(1);
    expect(mocks.hlsAttachMediaMock).toHaveBeenCalledTimes(1);
    expect(mocks.plyrConstructorMock).toHaveBeenCalledTimes(1);
  });
});
