<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import Hls from 'hls.js';
import Plyr from 'plyr';
import 'plyr/dist/plyr.css';
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy, type RenderTask } from 'pdfjs-dist';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import Viewer from 'viewerjs';
import 'viewerjs/dist/viewer.css';
import { downloadFile, previewFile } from '../../../api/file';
import { getPreviewCapabilities } from '../../../utils/preview';
import type { FileItem } from '../../../types/file';

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

const props = defineProps<{ file: FileItem | null }>();
const emit = defineEmits<{ (e: 'close'): void }>();

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
const videoPreviewRef = ref<HTMLVideoElement | null>(null);
const pdfCanvasRef = ref<HTMLCanvasElement | null>(null);
const pdfCanvasWrapRef = ref<HTMLDivElement | null>(null);

let imageViewer: Viewer | null = null;
let hlsPlayer: Hls | null = null;
let plyrPlayer: Plyr | null = null;
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
const isVideo = computed(() => previewCapabilities.value.isVideo);
const isHlsPlaylist = computed(() => previewCapabilities.value.isHls);

const formatBytes = (bytes: number | undefined) => {
  if (!bytes) return '--';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const canPrevPdfPage = computed(() => pdfPage.value > 1);
const canNextPdfPage = computed(() => pdfPage.value < pdfTotalPages.value);

const destroyImageViewer = () => {
  if (imageViewer) {
    imageViewer.destroy();
    imageViewer = null;
  }
};

const destroyVideoPlayer = () => {
  if (hlsPlayer) {
    hlsPlayer.destroy();
    hlsPlayer = null;
  }
  if (plyrPlayer) {
    plyrPlayer.destroy();
    plyrPlayer = null;
  }
  if (videoPreviewRef.value) {
    videoPreviewRef.value.removeAttribute('src');
    videoPreviewRef.value.load();
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
  destroyVideoPlayer();
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
        error.value = 'Unable to render PDF preview.';
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
    inline: false,
    navbar: false,
    title: false,
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
  });
};

const initVideoPreview = () => {
  if (!isVideo.value || !videoPreviewRef.value || !objectUrl.value) return;
  destroyVideoPlayer();

  const video = videoPreviewRef.value;
  if (isHlsPlaylist.value && Hls.isSupported()) {
    hlsPlayer = new Hls({
      enableWorker: true,
      lowLatencyMode: true,
    });
    hlsPlayer.loadSource(objectUrl.value);
    hlsPlayer.attachMedia(video);
    hlsPlayer.on(Hls.Events.ERROR, (_event: string, data: { fatal: boolean }) => {
      if (data.fatal) {
        error.value = 'Unable to play this HLS stream.';
      }
    });
  } else {
    video.src = objectUrl.value;
  }

  plyrPlayer = new Plyr(video, {
    controls: [
      'play-large',
      'play',
      'progress',
      'current-time',
      'mute',
      'volume',
      'settings',
      'pip',
      'fullscreen',
    ],
    settings: ['speed'],
    speed: {
      selected: 1,
      options: [0.75, 1, 1.25, 1.5, 2],
    },
    keyboard: {
      focused: true,
      global: false,
    },
  });
};

const loadPreview = async () => {
  resetState();

  if (!props.file) {
    return;
  }

  isLoading.value = true;
  try {
    const blob = await previewFile(props.file.id);

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
        }).promise;
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
    } else if (isVideo.value) {
      initVideoPreview();
    }
  } catch {
    error.value = 'Unable to load file preview.';
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
    const blob = await downloadFile(props.file.id);
    const object = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = object;
    anchor.download = props.file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(object);
  } catch {
    error.value = 'Unable to download this file.';
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
          <p class="detail__meta">{{ selectedMime || 'unknown type' }} | {{ formatBytes(file.size) }}</p>
        </div>
        <button class="detail__close" @click="emit('close')" aria-label="Close preview panel">x</button>
      </header>

      <div class="detail__actions">
        <button class="detail__action" @click="downloadSelectedFile">Download</button>
        <button class="detail__action" @click="loadPreview">Reload Preview</button>
      </div>

      <div class="detail__content">
        <div v-if="isLoading" class="detail__state">Loading preview...</div>
        <div v-else-if="error" class="detail__state detail__state--error">{{ error }}</div>

        <pre v-else-if="isText" class="detail__text">{{ textContent }}</pre>

        <div v-else-if="isImage" class="detail__image">
          <img ref="imagePreviewRef" :src="objectUrl" alt="Image preview" />
        </div>

        <div v-else-if="isPdf" class="detail__pdf">
          <div class="detail__pdf-toolbar">
            <button
              class="detail__pdf-btn"
              :disabled="!canPrevPdfPage || isPdfRendering || pdfFallbackMode"
              @click="goToPrevPdfPage"
            >
              Prev
            </button>
            <span v-if="!pdfFallbackMode">Page {{ pdfPage }} / {{ pdfTotalPages || 1 }}</span>
            <span v-else>Browser PDF fallback mode</span>
            <button
              class="detail__pdf-btn"
              :disabled="!canNextPdfPage || isPdfRendering || pdfFallbackMode"
              @click="goToNextPdfPage"
            >
              Next
            </button>
          </div>

          <div v-if="pdfFallbackMode" class="detail__pdf-fallback">
            <p class="detail__pdf-fallback-note">In-app PDF rendering is unavailable in this environment.</p>
            <div class="detail__pdf-fallback-actions">
              <button class="detail__pdf-btn" @click="loadPreview">Retry render</button>
              <button class="detail__pdf-btn" @click="openPdfInNewTab">Open in new tab</button>
            </div>
          </div>
          <div v-else ref="pdfCanvasWrapRef" class="detail__pdf-canvas">
            <canvas ref="pdfCanvasRef" />
          </div>
        </div>

        <div v-else-if="isAudio" class="detail__media">
          <audio :src="objectUrl" controls preload="metadata" />
        </div>

        <div v-else-if="isVideo" class="detail__media detail__media--video">
          <video ref="videoPreviewRef" controls preload="metadata" playsinline />
        </div>

        <div v-else class="detail__state">Preview is not available for this file type.</div>
      </div>
    </template>

    <div v-else class="detail__placeholder">
      <p>Select a file to preview details.</p>
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

.detail__close,
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

.detail__close {
  width: var(--row-h);
  padding: 0;
}

.detail__close:hover,
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

.detail__image img,
.detail__media audio,
.detail__media video {
  width: 100%;
}

.detail__media--video {
  border: 1px solid var(--border-default);
  padding: 8px;
  background: var(--surface-inset);
}

.detail__media video {
  max-height: 320px;
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
