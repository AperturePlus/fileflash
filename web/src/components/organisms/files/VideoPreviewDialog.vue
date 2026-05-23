<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { downloadFile, previewFile } from '../../../api/file';
import { getPreviewCapabilities } from '../../../utils/preview';
import { useLocaleStore } from '../../../store/locale';
import { useVideoPlayer } from '../../../composables/useVideoPlayer';
import type { FileItem } from '../../../types/file';

const props = defineProps<{ file: FileItem | null }>();
const emit = defineEmits<{ (e: 'close'): void }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const isOpen = computed(() => props.file !== null);
const videoRef = ref<HTMLVideoElement | null>(null);
const isLoading = ref(false);
const error = ref('');
const objectUrl = ref('');

const { mount: mountVideo, destroy: destroyVideo } = useVideoPlayer(videoRef);

const capabilities = computed(() =>
  getPreviewCapabilities(props.file?.mimeType, props.file?.name),
);

const formatBytes = (bytes: number | undefined) => {
  if (!bytes) return '--';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const reset = () => {
  destroyVideo();
  error.value = '';
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = '';
  }
};

const load = async () => {
  reset();
  if (!props.file) return;

  isLoading.value = true;
  try {
    const blob = await previewFile(props.file.id);
    objectUrl.value = URL.createObjectURL(blob);
    isLoading.value = false;
    await nextTick();
    mountVideo({
      source: objectUrl.value,
      isHls: capabilities.value.isHls,
      onFatalError: (msg) => {
        error.value = msg;
      },
    });
  } catch {
    error.value = t('files.preview.video.loadFailed');
  } finally {
    isLoading.value = false;
  }
};

const downloadCurrent = async () => {
  if (!props.file) return;
  try {
    const blob = await downloadFile(props.file.id);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = props.file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  } catch {
    error.value = t('files.preview.video.downloadFailed');
  }
};

const onKey = (ev: KeyboardEvent) => {
  if (ev.key === 'Escape' && isOpen.value) {
    ev.stopPropagation();
    emit('close');
  }
};

const onOverlayClick = (ev: MouseEvent) => {
  if (ev.target === ev.currentTarget) emit('close');
};

onMounted(() => {
  document.addEventListener('keydown', onKey);
});
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey);
  reset();
});

watch(() => props.file, () => {
  void load();
}, { immediate: true });
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="video-preview-dialog__overlay"
      role="presentation"
      @click="onOverlayClick"
    >
      <div
        class="video-preview-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="t('files.preview.title')"
        tabindex="-1"
      >
        <header class="video-preview-dialog__header">
          <div class="video-preview-dialog__meta">
            <h3 class="video-preview-dialog__filename" :title="file?.name ?? ''">
              {{ file?.name }}
            </h3>
            <p class="video-preview-dialog__sub">
              {{ capabilities.mimeType || t('files.preview.video.mimeFallback') }} | {{ formatBytes(file?.size) }}
            </p>
          </div>
          <div class="video-preview-dialog__actions">
            <button class="video-preview-dialog__btn" @click="downloadCurrent">{{ t('files.preview.detail.download') }}</button>
            <button
              class="video-preview-dialog__close"
              :aria-label="t('files.preview.close')"
              @click="emit('close')"
            >
              &times;
            </button>
          </div>
        </header>

        <div class="video-preview-dialog__stage">
          <div v-if="isLoading" class="video-preview-dialog__state">{{ t('files.preview.video.loading') }}</div>
          <div v-else-if="error" class="video-preview-dialog__state video-preview-dialog__state--error">
            {{ error }}
          </div>
          <video
            v-show="!isLoading && !error"
            ref="videoRef"
            controls
            preload="metadata"
            playsinline
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.video-preview-dialog__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.video-preview-dialog {
  position: relative;
  width: min(1600px, 96vw);
  height: min(900px, 92vh);
  background: #000;
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  outline: none;
}
.video-preview-dialog__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-sm);
  padding: 10px var(--sp-md);
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-base);
}
.video-preview-dialog__meta {
  min-width: 0;
  flex: 1;
}
.video-preview-dialog__filename {
  margin: 0;
  font-size: var(--text-h2);
  line-height: var(--leading-snug);
  color: var(--text-primary);
  word-break: break-all;
}
.video-preview-dialog__sub {
  margin: 4px 0 0;
  color: var(--text-dim);
  font-size: var(--text-small);
  font-family: var(--font-mono);
}
.video-preview-dialog__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.video-preview-dialog__btn {
  height: var(--row-h);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0 10px;
  font-family: var(--font-sans);
  font-size: var(--text-small);
}
.video-preview-dialog__btn:hover {
  background: var(--surface-inset);
  color: var(--text-primary);
}
.video-preview-dialog__close {
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}
.video-preview-dialog__close:hover {
  background: var(--surface-inset);
  color: var(--text-primary);
}
.video-preview-dialog__stage {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  overflow: hidden;
}
.video-preview-dialog__stage :deep(.plyr) {
  width: 100%;
  height: 100%;
  max-height: 100%;
}
.video-preview-dialog__stage :deep(.plyr video) {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.video-preview-dialog__stage video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.video-preview-dialog__state {
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.video-preview-dialog__state--error {
  color: var(--status-error);
}
</style>
