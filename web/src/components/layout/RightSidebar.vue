<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { previewFile } from '../../api/file';
import { useFileStore } from '../../store/file';

defineProps<{ visible: boolean }>();

const fileStore = useFileStore();
const { selectedFile } = storeToRefs(fileStore);

const isLoading = ref(false);
const error = ref('');
const textContent = ref('');
const objectUrl = ref('');

const selectedMime = computed(() => {
  if (!selectedFile.value || selectedFile.value.itemType !== 'file') return '';
  return selectedFile.value.mimeType || '';
});

const isText = computed(() => selectedMime.value.startsWith('text/') || selectedMime.value.includes('json'));
const isPdf = computed(() => selectedMime.value === 'application/pdf');
const isImage = computed(() => selectedMime.value.startsWith('image/'));
const isAudio = computed(() => selectedMime.value.startsWith('audio/'));
const isVideo = computed(() => selectedMime.value.startsWith('video/'));

const formatBytes = (bytes: number | undefined) => {
  if (!bytes) return '--';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const resetState = () => {
  textContent.value = '';
  error.value = '';
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = '';
  }
};

const loadPreview = async () => {
  resetState();

  if (!selectedFile.value || selectedFile.value.itemType !== 'file') {
    return;
  }

  isLoading.value = true;
  try {
    const blob = await previewFile(selectedFile.value.id);
    if (isText.value) {
      textContent.value = await blob.text();
    } else {
      objectUrl.value = URL.createObjectURL(blob);
    }
  } catch {
    error.value = 'Unable to load file preview.';
  } finally {
    isLoading.value = false;
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
    <template v-if="selectedFile && selectedFile.itemType === 'file'">
      <header class="sidebar-header">
        <div>
          <h3 class="filename" :title="selectedFile.name">{{ selectedFile.name }}</h3>
          <p class="meta">{{ selectedMime || 'unknown type' }} · {{ formatBytes(selectedFile.size) }}</p>
        </div>
        <button class="close-btn" @click="closeSidebar" aria-label="Close preview panel">×</button>
      </header>

      <div class="sidebar-content">
        <div v-if="isLoading" class="state">Loading preview...</div>
        <div v-else-if="error" class="state error">{{ error }}</div>

        <pre v-else-if="isText" class="text-preview">{{ textContent }}</pre>

        <div v-else-if="isImage" class="image-preview">
          <img :src="objectUrl" alt="Image preview" />
        </div>

        <div v-else-if="isPdf" class="pdf-preview">
          <iframe :src="objectUrl" title="PDF preview" />
        </div>

        <div v-else-if="isAudio" class="media-preview">
          <audio :src="objectUrl" controls preload="metadata" />
        </div>

        <div v-else-if="isVideo" class="media-preview">
          <video :src="objectUrl" controls preload="metadata" />
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
  border-left: 1px solid var(--color-border);
  background-color: var(--color-bg-secondary);
  display: flex;
  flex-direction: column;
  transition: margin-right 0.2s ease;
}

.right-sidebar.visible {
  margin-right: 0;
  box-shadow: var(--shadow-md);
}

.sidebar-header {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-divider);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-sm);
}

.filename {
  font-size: 15px;
  line-height: 1.35;
  margin: 0;
  word-break: break-all;
}

.meta {
  margin: 4px 0 0;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  cursor: pointer;
}

.sidebar-content {
  flex: 1;
  padding: var(--spacing-md);
  overflow: auto;
}

.sidebar-placeholder,
.state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--spacing-lg);
}

.state.error {
  color: var(--color-danger);
}

.text-preview {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-family-mono);
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-secondary);
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: 12px;
}

.image-preview img,
.media-preview audio,
.media-preview video,
.pdf-preview iframe {
  width: 100%;
  border-radius: var(--border-radius-sm);
}

.media-preview video {
  max-height: 320px;
}

.pdf-preview iframe {
  min-height: 520px;
  border: 1px solid var(--color-border);
  background-color: #fff;
}
</style>
