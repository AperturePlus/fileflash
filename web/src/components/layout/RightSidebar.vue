<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useFileStore } from '../../store/file';
import { storeToRefs } from 'pinia';
import { previewFile } from '../../api/file';
import type { FileItem } from '../../types/file';

const fileStore = useFileStore();
const { selectedFile } = storeToRefs(fileStore);

const fileContent = ref<string | null>(null);
const fileUrl = ref<string | null>(null);
const isLoading = ref(false);
const error = ref<string | null>(null);

const isTextFile = computed(() => {
  const file = selectedFile.value;
  if (!file || file.itemType !== 'file') return false;
  const mime = file.mimeType;
  return mime && (mime.startsWith('text/') || mime === 'application/json');
});

const isPdfFile = computed(() => {
  const file = selectedFile.value;
  if (!file || file.itemType !== 'file') return false;
  return file.mimeType === 'application/pdf';
});

watch(selectedFile, async (newFile) => {
  // Reset state
  fileContent.value = null;
  fileUrl.value = null;
  error.value = null;

  if (newFile && newFile.itemType === 'file') {
    isLoading.value = true;
    try {
      const blob = await previewFile(newFile.id);
      
      if (isPdfFile.value) {
        // For PDF, create a URL to use in an iframe/embed
        if (fileUrl.value) URL.revokeObjectURL(fileUrl.value);
        fileUrl.value = URL.createObjectURL(blob);
      } else if (isTextFile.value) {
        // For text-based files, read the content as a string
        fileContent.value = await blob.text();
      }
      
    } catch (e) {
      error.value = 'Could not load file preview.';
      console.error(e);
    } finally {
      isLoading.value = false;
    }
  }
}, { immediate: true });

const closeSidebar = () => {
  fileStore.selectedFile = null;
};
</script>

<template>
  <aside :class="['right-sidebar', { visible: !!selectedFile }]">
    <div v-if="selectedFile" class="sidebar-header">
      <h3 class="filename" :title="selectedFile.name">{{ selectedFile.name }}</h3>
      <button @click="closeSidebar" class="close-btn" aria-label="Close details">×</button>
    </div>
    <div class="sidebar-content">
      <div v-if="isLoading" class="centered-message">Loading preview...</div>
      <div v-else-if="error" class="centered-message error-message">{{ error }}</div>
      
      <div v-else-if="selectedFile">
        <!-- Text/JSON Preview -->
        <pre v-if="isTextFile" class="text-preview">{{ fileContent }}</pre>
        
        <!-- PDF Preview -->
        <div v-else-if="isPdfFile" class="pdf-preview">
          <iframe :src="fileUrl!" title="PDF Preview" frameborder="0"></iframe>
        </div>

        <!-- Fallback for unsupported types -->
        <div v-else class="centered-message">
          <p>No preview available for this file type.</p>
          <small v-if="selectedFile.itemType === 'file'">{{ selectedFile.mimeType }}</small>
        </div>
      </div>

       <div v-else class="centered-message">
        <p>Select a file to see its details.</p>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.right-sidebar {
  width: var(--sidebar-right-width);
  background-color: var(--color-bg-secondary);
  border-left: 1px solid var(--color-border);
  flex-shrink: 0;
  margin-right: calc(-1 * var(--sidebar-right-width));
  transition: margin-right var(--transition-base), background-color var(--transition-base), border-color var(--transition-base);
  z-index: 900;
  display: flex;
  flex-direction: column;
}

.right-sidebar.visible {
  margin-right: 0;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.05);
}

.sidebar-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-divider);
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filename {
  font-size: 1.1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: var(--spacing-md);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.sidebar-content {
  padding: var(--spacing-lg);
  flex-grow: 1;
  overflow-y: auto;
}

.centered-message {
  text-align: center;
  margin-top: 2rem;
  color: var(--color-text-secondary);
}

.error-message {
  color: var(--color-danger);
}

.text-preview {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: var(--font-family-mono);
  font-size: 0.875rem;
  background-color: var(--color-bg-tertiary);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
}

.pdf-preview {
  width: 100%;
  height: 100%;
}

.pdf-preview iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style> 