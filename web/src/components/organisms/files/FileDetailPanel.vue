<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy, type RenderTask } from 'pdfjs-dist';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import Viewer from 'viewerjs';
import 'viewerjs/dist/viewer.css';
import { downloadFile, previewFile } from '../../../api/file';
import { getPreviewCapabilities } from '../../../utils/preview';
import { useLocaleStore } from '../../../store/locale';
import type { FileItem } from '../../../types/file';

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

type BlobLoader = (fileId: string) => Promise<Blob>;

const props = withDefaults(defineProps<{
  file: FileItem | null;
  previewLoader?: BlobLoader;
  downloadLoader?: BlobLoader;
  showDownload?: boolean;
}>(), {
  previewLoader: previewFile,
  downloadLoader: downloadFile,
  showDownload: true,
});

const localeStore = useLocaleStore();
const t = localeStore.t;

const isLoading = ref(false);
const isPdfRendering = ref(false);
const error = ref('');
const textContent = ref('');
const objectUrl = ref('');
const pdfDoc = ref<PDFDocumentProxy | null>(null);
const pdfPage = ref(1);
const pdfTotalPages = ref(0);
const pdfFallbackMode = ref(false);
const pdfLastKnownWidth = ref(0);

const imagePreviewRef = ref<HTMLImageElement | null>(null);
const pdfCanvasRef = ref<HTMLCanvasElement | null>(null);
const pdfCanvasWrapRef = ref<HTMLDivElement | null>(null);

let imageViewer: Viewer | null = null;
let pdfRenderTask: RenderTask | null = null;
let pdfResizeObserver: ResizeObserver | null = null;
let pdfRenderToken = 0;

const previewCapabilities = computed(() =>
  getPreviewCapabilities(props.file?.mimeType, props.file?.name),
);
const selectedMime = computed(() => previewCapabilities.value.mimeType);
const isText = computed(() => previewCapabilities.value.isText);
const isPdf = computed(() => previewCapabilities.value.isPdf);
const isImage = computed(() => previewCapabilities.value.isImage);
const isAudio = computed(() => previewCapabilities.value.isAudio);

const formatBytes = (bytes: number | undefined) => {
  if (!bytes) return '--';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const canPrevPdfPage = computed(() => pdfPage.value > 1);
const canNextPdfPage = computed(() => pdfPage.value < pdfTotalPages.value);

const pdfPageLabel = computed(() =>
  t('files.preview.pdf.page')
    .replace('{page}', String(pdfPage.value))
    .replace('{total}', String(pdfTotalPages.value || 1)),
);

const destroyImageViewer = () => {
  if (imageViewer) {
    imageViewer.destroy();
    imageViewer = null;
  }
};

const destroyPdfResizeObserver = () => {
  if (pdfResizeObserver) {
    pdfResizeObserver.disconnect();
    pdfResizeObserver = null;
  }
  pdfLastKnownWidth.value = 0;
};

const destroyPdfState = () => {
  pdfRenderToken += 1;
  if (pdfRenderTask) {
    try {
      pdfRenderTask.cancel();
    } catch {
      // Ignore cancellation errors during teardown.
    }
    pdfRenderTask = null;
  }

  destroyPdfResizeObserver();
  pdfDoc.value?.destroy();
  pdfDoc.value = null;
  pdfPage.value = 1;
  pdfTotalPages.value = 0;
  pdfFallbackMode.value = false;

  const canvas = pdfCanvasRef.value;
  if (!canvas) return;
  const context = canvas.getContext('2d');
  context?.clearRect(0, 0, canvas.width, canvas.height);
};

const resetState = () => {
  textContent.value = '';
  error.value = '';
  destroyImageViewer();
  destroyPdfState();

  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = '';
  }
};

const setupPdfResizeObserver = () => {
  destroyPdfResizeObserver();
  if (!pdfCanvasWrapRef.value || !pdfDoc.value || typeof ResizeObserver === 'undefined') return;

  pdfLastKnownWidth.value = pdfCanvasWrapRef.value.clientWidth;
  pdfResizeObserver = new ResizeObserver((entries) => {
    if (!entries.length || !pdfDoc.value || pdfFallbackMode.value) return;

    const width = entries[0].contentRect.width;
    if (!width || Math.abs(width - pdfLastKnownWidth.value) < 4) return;

    pdfLastKnownWidth.value = width;
    void renderPdfPage(pdfPage.value);
  });
  pdfResizeObserver.observe(pdfCanvasWrapRef.value);
};

const renderPdfPage = async (pageNumber: number) => {
  if (!pdfDoc.value || !pdfCanvasRef.value) return;
  if (pageNumber < 1 || pageNumber > pdfDoc.value.numPages) return;

  pdfRenderToken += 1;
  const renderToken = pdfRenderToken;

  if (pdfRenderTask) {
    try {
      pdfRenderTask.cancel();
    } catch {
      // Ignore cancellation errors from an in-flight task.
    }
    pdfRenderTask = null;
  }

  isPdfRendering.value = true;
  pdfFallbackMode.value = false;

  try {
    const page = await pdfDoc.value.getPage(pageNumber);
    if (renderToken !== pdfRenderToken) return;

    const canvas = pdfCanvasRef.value;
    if (!canvas) return;
    const unscaledViewport = page.getViewport({ scale: 1 });
    const containerWidth = pdfCanvasWrapRef.value?.clientWidth || canvas.parentElement?.clientWidth || 640;
    const scale = Math.max(0.5, Math.min(2.4, containerWidth / unscaledViewport.width));
    const viewport = page.getViewport({ scale });

    canvas.width = viewport.width;
    canvas.height = viewport.height;

    pdfRenderTask = page.render({
      canvas,
      viewport,
    });

    await pdfRenderTask.promise;
    if (renderToken !== pdfRenderToken) return;

    pdfPage.value = pageNumber;
    page.cleanup();
    pdfRenderTask = null;
  } catch {
    if (renderToken === pdfRenderToken) {
      pdfFallbackMode.value = true;
      pdfRenderTask = null;
      if (!objectUrl.value) {
        error.value = t('files.preview.pdf.renderFailed');
      }
    }
  } finally {
    if (renderToken === pdfRenderToken) {
      isPdfRendering.value = false;
    }
  }
};

const initImagePreview = async () => {
  if (!isImage.value || !imagePreviewRef.value) return;
  destroyImageViewer();

  imageViewer = new Viewer(imagePreviewRef.value, {
    inline: true,
    navbar: false,
    title: false,
    backdrop: false,
    button: false,
    toolbar: {
      zoomIn: true,
      zoomOut: true,
      oneToOne: true,
      reset: true,
      prev: false,
      next: false,
      rotateLeft: true,
      rotateRight: true,
      flipHorizontal: false,
      flipVertical: false,
    },
    zoomOnWheel: true,
    movable: true,
    scalable: false,
    transition: false,
  });
};

const loadPreview = async () => {
  resetState();

  if (!props.file) {
    return;
  }

  isLoading.value = true;
  try {
    const blob = await props.previewLoader(props.file.id);

    if (isText.value) {
      textContent.value = await blob.text();
      return;
    }

    objectUrl.value = URL.createObjectURL(blob);

    if (isPdf.value) {
      try {
        const raw = new Uint8Array(await blob.arrayBuffer());
        pdfDoc.value = await getDocument({
          data: raw,
          disableWorker: true,
        } as Parameters<typeof getDocument>[0]).promise;
        pdfTotalPages.value = pdfDoc.value.numPages;
        isLoading.value = false;
        await nextTick();
        setupPdfResizeObserver();
        await renderPdfPage(1);
      } catch {
        isLoading.value = false;
        pdfFallbackMode.value = true;
      }
      return;
    }

    isLoading.value = false;
    await nextTick();
    if (isImage.value) {
      await initImagePreview();
    }
  } catch {
    error.value = t('files.preview.detail.loadFailed');
  } finally {
    isLoading.value = false;
  }
};

const goToPrevPdfPage = async () => {
  if (!canPrevPdfPage.value) return;
  await renderPdfPage(pdfPage.value - 1);
};

const goToNextPdfPage = async () => {
  if (!canNextPdfPage.value) return;
  await renderPdfPage(pdfPage.value + 1);
};

const openPdfInNewTab = () => {
  if (!objectUrl.value) return;
  window.open(objectUrl.value, '_blank', 'noopener,noreferrer');
};

const downloadSelectedFile = async () => {
  if (!props.file) return;

  try {
    const blob = await props.downloadLoader(props.file.id);
    const object = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = object;
    anchor.download = props.file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(object);
  } catch {
    error.value = t('files.preview.detail.downloadFailed');
  }
};

watch(() => props.file, () => {
  void loadPreview();
}, { immediate: true });

onUnmounted(() => {
  resetState();
});
</script>

<template>
  <div class="detail">
    <template v-if="file">
      <header class="detail__header">
        <div>
          <h3 class="detail__filename" :title="file.name">{{ file.name }}</h3>
          <p class="detail__meta">{{ selectedMime || t('files.preview.detail.unknownType') }} | {{ formatBytes(file.size) }}</p>
        </div>
      </header>

      <div class="detail__actions">
        <button v-if="showDownload" class="detail__action" @click="downloadSelectedFile">{{ t('files.preview.detail.download') }}</button>
        <button class="detail__action" @click="loadPreview">{{ t('files.preview.detail.reload') }}</button>
      </div>

      <div class="detail__content">
        <div v-if="isLoading" class="detail__state">{{ t('files.preview.detail.loading') }}</div>
        <div v-else-if="error" class="detail__state detail__state--error">{{ error }}</div>

        <pre v-else-if="isText" class="detail__text">{{ textContent }}</pre>

        <div v-else-if="isImage" class="detail__image">
          <img ref="imagePreviewRef" :src="objectUrl" :alt="t('files.preview.image.alt')" />
        </div>

        <div v-else-if="isPdf" class="detail__pdf">
          <div class="detail__pdf-toolbar">
            <button
              class="detail__pdf-btn"
              :disabled="!canPrevPdfPage || isPdfRendering || pdfFallbackMode"
              @click="goToPrevPdfPage"
            >
              {{ t('files.preview.pdf.prev') }}
            </button>
            <span v-if="!pdfFallbackMode">{{ pdfPageLabel }}</span>
            <span v-else>{{ t('files.preview.pdf.fallbackMode') }}</span>
            <button
              class="detail__pdf-btn"
              :disabled="!canNextPdfPage || isPdfRendering || pdfFallbackMode"
              @click="goToNextPdfPage"
            >
              {{ t('files.preview.pdf.next') }}
            </button>
          </div>

          <div v-if="pdfFallbackMode" class="detail__pdf-fallback">
            <p class="detail__pdf-fallback-note">{{ t('files.preview.pdf.fallbackNote') }}</p>
            <div class="detail__pdf-fallback-actions">
              <button class="detail__pdf-btn" @click="loadPreview">{{ t('files.preview.pdf.retryRender') }}</button>
              <button class="detail__pdf-btn" @click="openPdfInNewTab">{{ t('files.preview.pdf.openNewTab') }}</button>
            </div>
          </div>
          <div v-else ref="pdfCanvasWrapRef" class="detail__pdf-canvas">
            <canvas ref="pdfCanvasRef" />
          </div>
        </div>

        <div v-else-if="isAudio" class="detail__media">
          <audio :src="objectUrl" controls preload="metadata" />
        </div>

        <div v-else class="detail__state">{{ t('files.preview.detail.notAvailable') }}</div>
      </div>
    </template>

    <div v-else class="detail__placeholder">
      <p>{{ t('files.preview.detail.placeholder') }}</p>
    </div>
  </div>
</template>

<style scoped>
.detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail__header {
  padding: var(--sp-md);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-sm);
}

.detail__filename {
  font-size: var(--text-h2);
  line-height: var(--leading-snug);
  margin: 0;
  word-break: break-all;
  color: var(--text-primary);
}

.detail__meta {
  margin: 4px 0 0;
  color: var(--text-dim);
  font-size: var(--text-small);
}

.detail__action,
.detail__pdf-btn {
  height: var(--row-h);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0 10px;
  font-family: var(--font-sans);
  font-size: var(--text-small);
  transition: background-color var(--mo-duration-fast) var(--mo-easing), color var(--mo-duration-fast) var(--mo-easing);
}

.detail__action:hover,
.detail__pdf-btn:hover:not(:disabled) {
  background: var(--surface-inset);
  color: var(--text-primary);
}

.detail__actions {
  display: flex;
  gap: 8px;
  padding: 10px var(--sp-md) 0;
}

.detail__content {
  flex: 1;
  padding: var(--sp-md);
  overflow: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.detail__placeholder,
.detail__state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-dim);
  padding: var(--sp-lg);
}

.detail__state--error {
  color: var(--status-error);
}

.detail__text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: var(--text-small);
  line-height: var(--leading-normal);
  color: var(--text-secondary);
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  padding: var(--sp-md);
}

.detail__image {
  flex: 1;
  min-height: 320px;
  position: relative;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  overflow: hidden;
}
.detail__image img {
  display: none;
}

.detail__media audio {
  width: 100%;
}

.detail__pdf {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail__pdf-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: var(--text-small);
}

.detail__pdf-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail__pdf-canvas {
  border: 1px solid var(--border-default);
  background: #fff;
  overflow: auto;
}

.detail__pdf-canvas canvas {
  display: block;
  margin: 0 auto;
  max-width: 100%;
  height: auto;
}

.detail__pdf-fallback {
  border: 1px solid var(--border-default);
  overflow: hidden;
  background: var(--surface-inset);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail__pdf-fallback-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-small);
  line-height: var(--leading-normal);
}

.detail__pdf-fallback-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
