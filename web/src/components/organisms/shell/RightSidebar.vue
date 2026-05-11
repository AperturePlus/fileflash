<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import Hls from 'hls.js';
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from 'pdfjs-dist';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import Viewer from 'viewerjs';
import 'viewerjs/dist/viewer.css';
import { downloadFile, previewFile } from '../../../api/file';
import { useFileStore } from '../../../store/file';

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

defineProps<{ visible: boolean }>();

const fileStore = useFileStore();

const isLoading = ref(false);
const isPdfRendering = ref(false);
const error = ref('');
const textContent = ref('');
const objectUrl = ref('');
const pdfDoc = ref<PDFDocumentProxy | null>(null);
const pdfPage = ref(1);
const pdfTotalPages = ref(0);

const imagePreviewRef = ref<HTMLImageElement | null>(null);
const videoPreviewRef = ref<HTMLVideoElement | null>(null);
const pdfCanvasRef = ref<HTMLCanvasElement | null>(null);

let imageViewer: Viewer | null = null;
let hlsPlayer: Hls | null = null;

const selectedFile = computed(() => {
  if (!fileStore.selectedFile || fileStore.selectedFile.itemType !== 'file') return null;
  return fileStore.selectedFile;
});

const selectedMime = computed(() => selectedFile.value?.mimeType || '');
const isText = computed(() => selectedMime.value.startsWith('text/') || selectedMime.value.includes('json'));
const isPdf = computed(() => selectedMime.value === 'application/pdf');
const isImage = computed(() => selectedMime.value.startsWith('image/'));
const isAudio = computed(() => selectedMime.value.startsWith('audio/'));
const isVideo = computed(() => selectedMime.value.startsWith('video/'));
const isHlsPlaylist = computed(() => {
  const name = selectedFile.value?.name.toLowerCase() || '';
  return selectedMime.value === 'application/vnd.apple.mpegurl' || name.endsWith('.m3u8');
});

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
  if (videoPreviewRef.value) {
    videoPreviewRef.value.removeAttribute('src');
    videoPreviewRef.value.load();
  }
};

const destroyPdfState = () => {
  pdfDoc.value?.destroy();
  pdfDoc.value = null;
  pdfPage.value = 1;
  pdfTotalPages.value = 0;
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

const renderPdfPage = async (pageNumber: number) => {
  if (!pdfDoc.value || !pdfCanvasRef.value) return;
  if (pageNumber < 1 || pageNumber > pdfDoc.value.numPages) return;

  isPdfRendering.value = true;
  try {
    const page = await pdfDoc.value.getPage(pageNumber);
    const unscaledViewport = page.getViewport({ scale: 1 });
    const containerWidth = pdfCanvasRef.value.parentElement?.clientWidth || 640;
    const scale = Math.max(0.5, Math.min(2.4, containerWidth / unscaledViewport.width));
    const viewport = page.getViewport({ scale });

    const canvas = pdfCanvasRef.value;
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Canvas context is unavailable');
    }

    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({
      canvas,
      canvasContext: context,
      viewport,
    }).promise;

    pdfPage.value = pageNumber;
  } catch {
    error.value = 'Unable to render PDF preview.';
  } finally {
    isPdfRendering.value = false;
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
    return;
  }

  video.src = objectUrl.value;
};

const loadPreview = async () => {
  resetState();

  if (!selectedFile.value) {
    return;
  }

  isLoading.value = true;
  try {
    const blob = await previewFile(selectedFile.value.id);
    if (isText.value) {
      textContent.value = await blob.text();
    } else if (isPdf.value) {
      const raw = new Uint8Array(await blob.arrayBuffer());
      pdfDoc.value = await getDocument({ data: raw }).promise;
      pdfTotalPages.value = pdfDoc.value.numPages;
      await nextTick();
      await renderPdfPage(1);
    } else {
      objectUrl.value = URL.createObjectURL(blob);
      await nextTick();
      if (isImage.value) {
        await initImagePreview();
      } else if (isVideo.value) {
        initVideoPreview();
      }
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

const downloadSelectedFile = async () => {
  if (!selectedFile.value) return;

  try {
    const blob = await downloadFile(selectedFile.value.id);
    const object = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = object;
    anchor.download = selectedFile.value.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(object);
  } catch {
    error.value = 'Unable to download this file.';
  }
};

watch(selectedFile, () => {
  loadPreview();
}, { immediate: true });

onUnmounted(() => {
  resetState();
});

const closeSidebar = () => {
  fileStore.selectedFile = null;
};
</script>

<template>
  <aside :class="['right-sidebar', { visible }]">
    <template v-if="selectedFile">
      <header class="sidebar-header">
        <div>
          <h3 class="filename" :title="selectedFile.name">{{ selectedFile.name }}</h3>
          <p class="meta">{{ selectedMime || 'unknown type' }} | {{ formatBytes(selectedFile.size) }}</p>
        </div>
        <button class="close-btn" @click="closeSidebar" aria-label="Close preview panel">x</button>
      </header>

      <div class="sidebar-actions">
        <button class="action-btn" @click="downloadSelectedFile">Download</button>
        <button class="action-btn" @click="loadPreview">Reload Preview</button>
      </div>

      <div class="sidebar-content">
        <div v-if="isLoading" class="state">Loading preview...</div>
        <div v-else-if="error" class="state error">{{ error }}</div>

        <pre v-else-if="isText" class="text-preview">{{ textContent }}</pre>

        <div v-else-if="isImage" class="image-preview">
          <img ref="imagePreviewRef" :src="objectUrl" alt="Image preview" />
        </div>

        <div v-else-if="isPdf" class="pdf-preview">
          <div class="pdf-toolbar">
            <button class="pdf-btn" :disabled="!canPrevPdfPage || isPdfRendering" @click="goToPrevPdfPage">Prev</button>
            <span>Page {{ pdfPage }} / {{ pdfTotalPages || 1 }}</span>
            <button class="pdf-btn" :disabled="!canNextPdfPage || isPdfRendering" @click="goToNextPdfPage">Next</button>
          </div>
          <div class="pdf-canvas-wrap">
            <canvas ref="pdfCanvasRef"></canvas>
          </div>
        </div>

        <div v-else-if="isAudio" class="media-preview">
          <audio :src="objectUrl" controls preload="metadata" />
        </div>

        <div v-else-if="isVideo" class="media-preview">
          <video ref="videoPreviewRef" :src="isHlsPlaylist ? '' : objectUrl" controls preload="metadata" />
        </div>

        <div v-else class="state">Preview is not available for this file type.</div>
      </div>
    </template>

    <div v-else class="sidebar-placeholder">
      <p>Select a file to preview details.</p>
    </div>
  </aside>
</template>

<style scoped>
.right-sidebar {
  width: var(--sidebar-right-width);
  margin-right: calc(-1 * var(--sidebar-right-width));
  border-left: 1px solid var(--border-default);
  background: var(--surface-raised);
  display: flex; flex-direction: column;
  transition: margin-right var(--mo-duration-mid) var(--mo-easing);
}
.right-sidebar.visible { margin-right: 0; }
.sidebar-header { padding: var(--sp-md); border-bottom: 1px solid var(--border-subtle); display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-sm); }
.filename { font-size: var(--text-h2); line-height: var(--leading-snug); margin: 0; word-break: break-all; color: var(--text-primary); }
.meta { margin: 4px 0 0; color: var(--text-dim); font-size: var(--text-small); }
.close-btn, .action-btn, .pdf-btn {
  height: var(--row-h); border-radius: var(--radius-sm); border: 1px solid var(--border-default);
  background: var(--surface-raised); color: var(--text-secondary); cursor: pointer; padding: 0 10px;
  font-family: var(--font-sans); font-size: var(--text-small);
  transition: background-color var(--mo-duration-fast) var(--mo-easing), color var(--mo-duration-fast) var(--mo-easing);
}
.close-btn { width: var(--row-h); padding: 0; }
.close-btn:hover, .action-btn:hover, .pdf-btn:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }
.sidebar-actions { display: flex; gap: 8px; padding: 10px var(--sp-md) 0; }
.sidebar-content { flex: 1; padding: var(--sp-md); overflow: auto; }
.sidebar-placeholder, .state { flex: 1; display: flex; align-items: center; justify-content: center; text-align: center; color: var(--text-dim); padding: var(--sp-lg); }
.state.error { color: var(--status-error); }
.text-preview { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: var(--font-mono); font-size: var(--text-small); line-height: var(--leading-normal); color: var(--text-secondary); background: var(--surface-inset); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: var(--sp-md); }
.image-preview img, .media-preview audio, .media-preview video { width: 100%; border-radius: var(--radius-sm); }
.media-preview video { max-height: 320px; }
.pdf-preview { display: flex; flex-direction: column; gap: 10px; }
.pdf-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--text-secondary); font-size: var(--text-small); }
.pdf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pdf-canvas-wrap { border: 1px solid var(--border-default); border-radius: var(--radius-sm); background: #fff; overflow: auto; }
.pdf-canvas-wrap canvas { display: block; margin: 0 auto; max-width: 100%; height: auto; }
</style>
