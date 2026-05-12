<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import MoveItemDialog from '../../../components/common/MoveItemDialog.vue';
import { requestArchiveExtract, requestArchivePreview } from '../../../api/file';
import { getFolderPath } from '../../../api/folder';
import { getJob } from '../../../api/job';
import { useFileStore } from '../../../store/file';
import { eventBus } from '../../../utils/eventBus';
import type {
  ArchiveExtractRequest,
  BackgroundJob,
  FileItem,
  JobResultArchiveExtract,
  JobResultArchivePreview,
} from '../../../types/file';

interface Props {
  isVisible: boolean;
  file: FileItem | null;
  currentFolderId: string | null;
}

const props = defineProps<Props>();
const emit = defineEmits(['close']);

const fileStore = useFileStore();

const error = ref('');

const previewJob = ref<BackgroundJob<JobResultArchivePreview> | null>(null);
const previewResult = ref<JobResultArchivePreview | null>(null);
const isPreviewLoading = ref(false);

const extractJob = ref<BackgroundJob<JobResultArchiveExtract> | null>(null);
const isExtracting = ref(false);

const destinationFolderId = ref<string>('root');
const destinationFolderName = ref<string>('My Files');
const isFolderPickerVisible = ref(false);

const createSubfolder = ref(true);
const subfolderName = ref('');
const conflictStrategy = ref<'rename' | 'overwrite' | 'skip'>('rename');

let pollToken = 0;

const selectedFileName = computed(() => props.file?.name || '');

const formatBytes = (bytes: number | undefined) => {
  if (bytes === undefined || bytes === null) return '--';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(Math.max(bytes, 1)) / Math.log(k));
  const value = bytes / Math.pow(k, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[Math.min(i, units.length - 1)]}`;
};

const defaultSubfolderName = (fileName: string) => {
  const lower = (fileName || '').toLowerCase();
  if (lower.endsWith('.tar.gz')) {
    return fileName.slice(0, -'.tar.gz'.length);
  }
  if (lower.endsWith('.tgz')) {
    return fileName.slice(0, -'.tgz'.length);
  }
  const lastDot = fileName.lastIndexOf('.');
  return lastDot > 0 ? fileName.slice(0, lastDot) : fileName;
};

const resolveFolderName = async (folderId: string): Promise<string> => {
  if (folderId === 'root') return 'My Files';
  try {
    const response = await getFolderPath(folderId);
    const items = response.pathItems || [];
    const last = items[items.length - 1];
    if (last?.name) return last.name;
  } catch {
    // fall through
  }
  return folderId;
};

const handleFolderPicked = async (payload: string | { targetFolderId: string }) => {
  const folderId = typeof payload === 'string' ? payload : payload.targetFolderId;
  destinationFolderId.value = folderId;
  isFolderPickerVisible.value = false;
  destinationFolderName.value = await resolveFolderName(folderId);
};

const resetState = () => {
  error.value = '';
  previewJob.value = null;
  previewResult.value = null;
  isPreviewLoading.value = false;
  extractJob.value = null;
  isExtracting.value = false;
  isFolderPickerVisible.value = false;
  pollToken += 1;
};

const closeDialog = () => {
  emit('close');
};

const pollJobUntilDone = async <T,>(
  jobId: string,
  onUpdate: (job: BackgroundJob<T>) => void,
): Promise<BackgroundJob<T>> => {
  const token = pollToken;
  const intervalMs = 900;
  const timeoutMs = 120000;
  const startedAt = Date.now();

  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (token !== pollToken) {
      throw new Error('Polling cancelled');
    }
    if (Date.now() - startedAt > timeoutMs) {
      throw new Error('Job polling timeout');
    }

    const job = await getJob<T>(jobId);
    onUpdate(job);

    if (job.status === 'succeeded' || job.status === 'failed' || job.status === 'canceled') {
      return job;
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
};

const loadPreview = async () => {
  if (!props.file) return;

  isPreviewLoading.value = true;
  error.value = '';
  previewResult.value = null;

  try {
    const job = await requestArchivePreview(props.file.id);
    previewJob.value = job;

    const done = await pollJobUntilDone<JobResultArchivePreview>(job.jobId, (updated) => {
      previewJob.value = updated as any;
    });

    if (done.status !== 'succeeded') {
      error.value = done.errorMessage || 'Archive preview failed.';
      return;
    }
    previewResult.value = done.result;
  } catch (e: any) {
    error.value = e?.message || 'Failed to request archive preview.';
  } finally {
    isPreviewLoading.value = false;
  }
};

const startExtract = async () => {
  if (!props.file) return;

  isExtracting.value = true;
  error.value = '';

  try {
    const req: ArchiveExtractRequest = {
      targetFolderId: destinationFolderId.value,
      createSubfolder: createSubfolder.value,
      conflictStrategy: conflictStrategy.value,
    };
    if (createSubfolder.value) {
      const name = subfolderName.value.trim();
      if (name) req.subfolderName = name;
    }

    const job = await requestArchiveExtract(props.file.id, req);
    extractJob.value = job;

    const done = await pollJobUntilDone<JobResultArchiveExtract>(job.jobId, (updated) => {
      extractJob.value = updated as any;
    });

    if (done.status !== 'succeeded') {
      error.value = done.errorMessage || 'Archive extraction failed.';
      return;
    }

    const nextFolderId = done.result.extractedFolderId || destinationFolderId.value;
    fileStore.navigateToFolder(nextFolderId);
    eventBus.emit('refresh-file-tree');
    closeDialog();
  } catch (e: any) {
    error.value = e?.message || 'Failed to request archive extraction.';
  } finally {
    isExtracting.value = false;
  }
};

watch(
  () => props.isVisible,
  (visible) => {
    if (!visible) {
      resetState();
      return;
    }

    resetState();
    destinationFolderId.value = props.currentFolderId || 'root';
    createSubfolder.value = true;
    subfolderName.value = defaultSubfolderName(selectedFileName.value);
    conflictStrategy.value = 'rename';
    loadPreview();
    resolveFolderName(destinationFolderId.value).then((name) => {
      destinationFolderName.value = name;
    });
  },
);

onUnmounted(() => {
  pollToken += 1;
});
</script>

<template>
  <transition name="modal-fade">
    <div v-if="isVisible" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-dialog">
        <header class="modal-header">
          <h3 class="modal-title">Extract '{{ file?.name }}'</h3>
          <button class="modal-close" @click="closeDialog">&times;</button>
        </header>

        <div class="modal-body">
          <div v-if="error" class="error-banner">{{ error }}</div>

          <section class="section">
            <h4 class="section-title">Preview</h4>

            <div v-if="isPreviewLoading" class="state">Loading preview...</div>

            <div v-else-if="previewResult" class="preview">
              <div class="preview-summary">
                <span>{{ previewResult.summary.fileCount }} files</span>
                <span>{{ previewResult.summary.dirCount }} folders</span>
                <span>{{ formatBytes(previewResult.summary.totalUncompressedBytes) }}</span>
                <span v-if="previewResult.summary.truncated" class="hint">truncated</span>
              </div>

              <div class="entries">
                <div v-for="entry in previewResult.entries" :key="entry.path" class="entry">
                  <span class="entry-path">{{ entry.isDir ? 'DIR' : 'FILE' }} {{ entry.path }}</span>
                  <span v-if="!entry.isDir" class="entry-size">{{ formatBytes(entry.size) }}</span>
                </div>
              </div>
            </div>

            <div v-else class="state">No preview available.</div>
          </section>

          <section class="section">
            <h4 class="section-title">Destination</h4>

            <div class="row">
              <div class="row-label">Folder</div>
              <div class="row-value" :title="destinationFolderId">{{ destinationFolderName }}</div>
              <button class="btn btn-secondary" type="button" @click="isFolderPickerVisible = true">Choose...</button>
            </div>

            <label class="checkbox">
              <input v-model="createSubfolder" type="checkbox" />
              <span>Create subfolder</span>
            </label>

            <div v-if="createSubfolder" class="row">
              <div class="row-label">Subfolder</div>
              <input v-model="subfolderName" class="text-input" type="text" placeholder="Extracted" />
            </div>

            <div class="row">
              <div class="row-label">Conflict</div>
              <select v-model="conflictStrategy" class="select-input">
                <option value="rename">Rename</option>
                <option value="overwrite">Overwrite</option>
                <option value="skip">Skip</option>
              </select>
            </div>
          </section>
        </div>

        <footer class="modal-footer">
          <button class="btn btn-secondary" type="button" @click="closeDialog">Cancel</button>
          <button class="btn btn-primary" type="button" :disabled="isExtracting || !file" @click="startExtract">
            {{ isExtracting ? 'Extracting...' : 'Extract' }}
          </button>
        </footer>
      </div>

      <MoveItemDialog
        :is-visible="isFolderPickerVisible"
        :item-to-move="file"
        :enable-share-handling="false"
        tree-variant="modern"
        title="Select destination folder"
        prompt="Choose a folder to extract into:"
        confirm-text="Select"
        @close="isFolderPickerVisible = false"
        @confirm="handleFolderPicked"
      />
    </div>
  </transition>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1900;
}

.modal-dialog {
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-xl);
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.75rem;
  line-height: 1;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 0;
}

.modal-body {
  padding: var(--spacing-lg);
  max-height: 70vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.error-banner {
  border: 1px solid #fca5a5;
  background: rgba(239, 68, 68, 0.08);
  color: var(--color-danger-dark);
  padding: 10px 12px;
  border-radius: var(--border-radius-md);
}

.section-title {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 0.95rem;
}

.state {
  color: var(--color-text-tertiary);
}

.preview-summary {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-size: 12px;
}

.hint {
  color: var(--color-text-tertiary);
}

.entries {
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-primary);
  max-height: 240px;
  overflow: auto;
}

.entry {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}
.entry:last-child {
  border-bottom: none;
}

.entry-path {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-size {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
}

.row {
  display: grid;
  grid-template-columns: 110px 1fr auto;
  gap: 10px;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.row-label {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.row-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-primary);
}

.checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: var(--spacing-sm) 0;
  color: var(--color-text-secondary);
}

.text-input,
.select-input {
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  padding: 0 10px;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  background-color: var(--color-bg-tertiary);
  border-bottom-left-radius: var(--border-radius-lg);
  border-bottom-right-radius: var(--border-radius-lg);
}

.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--border-radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-base);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
  border-color: var(--color-primary);
}

.btn-secondary {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active .modal-dialog,
.modal-fade-leave-active .modal-dialog {
  transition: transform 0.2s ease;
}
.modal-fade-enter-from .modal-dialog,
.modal-fade-leave-to .modal-dialog {
  transform: translateY(-10px) scale(0.98);
}
</style>
