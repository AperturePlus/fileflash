<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useFileStore } from '../../store/file';
import { useSettingsStore } from '../../store/settings';
import { useFileSelection } from '../../composables/useFileSelection';
import { useFileActions } from '../../composables/useFileActions';
import { useBatchActions } from '../../composables/useBatchActions';
import { useUpload } from '../../composables/useUpload';
import { useFileSorting } from '../../composables/useFileSorting';
import { toggleFileStar } from '../../api/file';
import { toggleFolderStar } from '../../api/folder';
import Breadcrumb from '../../components/common/Breadcrumb.vue';
import MoveItemDialog from '../../components/common/MoveItemDialog.vue';
import ShareDialog from '../../components/common/ShareDialog.vue';
import ExtractArchiveDialog from './components/ExtractArchiveDialog.vue';
import FileItemsView from './components/FileItemsView.vue';
import { eventBus } from '../../utils/eventBus';
import { ui } from '../../utils/ui';
import type { ContentItem, FileItem, FolderItem } from '../../types/file';

const fileStore = useFileStore();
const settingsStore = useSettingsStore();
const { items, path, isLoading, currentFolderId } = storeToRefs(fileStore);
const { settings } = storeToRefs(settingsStore);
const fileInput = ref<HTMLInputElement | null>(null);

const searchQuery = ref('');
const isSearching = ref(false);
const searchResults = ref<ContentItem[]>([]);

const {
  selectedItems,
  isSelected,
  toggleSelection,
  selectedCount,
  clearSelection,
} = useFileSelection();

const {
  renamingItemId,
  renameInputValue,
  itemToMove,
  moveItemCount,
  moveHasActiveShare,
  isMoveDialogVisible,
  itemToShare,
  isShareDialogVisible,
  startRename,
  cancelRename,
  finishRename,
  handleDelete,
  handleDownload,
  handleCreateFolder,
  startMove,
  startMoveForSelection,
  closeMoveDialog,
  handleMoveConfirm,
  startShare,
  handleBatchMove,
} = useFileActions(currentFolderId);

const { handleBatchDownload, handleBatchDelete } = useBatchActions(selectedItems, clearSelection);

const {
  uploadTasks,
  isDragging,
  handleDragEnter,
  handleDragLeave,
  handleDragOver,
  handleDrop,
  handleFileSelect,
} = useUpload(currentFolderId);

const { sortedItems, setSort, sortKey, sortDirection } = useFileSorting(items);

const viewMode = ref<'grid' | 'list'>((localStorage.getItem('fileflash-view-mode') as 'grid' | 'list') || 'grid');

watch(viewMode, (value) => {
  localStorage.setItem('fileflash-view-mode', value);
});

let autoRefreshTimer: number | null = null;

const resetAutoRefreshTimer = () => {
  if (autoRefreshTimer !== null) {
    window.clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }

  const seconds = Number(settings.value.autoRefreshInterval || 0);
  if (seconds <= 0) {
    return;
  }

  autoRefreshTimer = window.setInterval(() => {
    const folderId = currentFolderId.value || 'root';
    fileStore.fetchFolderContents(folderId);
  }, seconds * 1000);
};

watch(
  () => [settings.value.autoRefreshInterval, currentFolderId.value],
  () => {
    resetAutoRefreshTimer();
  },
  { immediate: true },
);

const displayItems = computed(() => {
  if (isSearching.value) {
    return [...searchResults.value].sort((a, b) => a.name.localeCompare(b.name));
  }
  return sortedItems.value;
});

const handleSidebarMove = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[]; targetFolderId: string; targetFolderName: string }) => {
  const canMove = ui.confirm({
    title: 'Move Items',
    message: `Move ${sourceItemIds.length} item(s) to "${targetFolderName}"?`,
    confirmText: 'Move',
  });
  canMove.then((confirmed) => {
    if (!confirmed) return;
    handleBatchMove(sourceItemIds, targetFolderId, 'keep');
  });
};

const handleSearch = async ({ query }: { query: string }) => {
  searchQuery.value = query;

  if (!query) {
    isSearching.value = false;
    searchResults.value = [];
    return;
  }

  isSearching.value = true;
  try {
    searchResults.value = await fileStore.searchInFolder(currentFolderId.value || 'root', query);
  } catch {
    searchResults.value = [];
  }
};

const triggerFileInput = () => fileInput.value?.click();

const navigateByBreadcrumb = (folderId: string) => {
  isSearching.value = false;
  searchQuery.value = '';
  searchResults.value = [];
  fileStore.navigateToFolder(folderId);
};

const handleBreadcrumbDrop = ({ sourceItemIds, targetFolderId }: { sourceItemIds: string[]; targetFolderId: string }) => {
  ui.confirm({
    title: 'Move Items',
    message: `Move ${sourceItemIds.length} item(s) to this folder?`,
    confirmText: 'Move',
  }).then((confirmed) => {
    if (!confirmed) return;
    handleBatchMove(sourceItemIds, targetFolderId, 'keep');
  });
};

const handleItemClick = (item: ContentItem) => {
  if (renamingItemId.value === item.id) return;

  if (item.itemType === 'folder') {
    isSearching.value = false;
    searchQuery.value = '';
    searchResults.value = [];
    fileStore.navigateToFolder(item.id);
    return;
  }

  fileStore.selectedFile = item;
};

const handleDragItemStart = (e: DragEvent, item: ContentItem) => {
  if (!e.dataTransfer) return;
  const ids = isSelected(item.id) ? Array.from(selectedItems.value) : [item.id];
  e.dataTransfer.setData('application/fileflash-item-ids', JSON.stringify(ids));
  e.dataTransfer.effectAllowed = 'move';
};

const handleFolderDrop = (e: DragEvent, folder: FolderItem) => {
  e.preventDefault();
  const raw = e.dataTransfer?.getData('application/fileflash-item-ids');
  if (!raw) return;

  const sourceIds: string[] = JSON.parse(raw);
  if (sourceIds.includes(folder.id)) return;

  ui.confirm({
    title: 'Move Items',
    message: `Move ${sourceIds.length} item(s) into "${folder.name}"?`,
    confirmText: 'Move',
  }).then((confirmed) => {
    if (!confirmed) return;
    handleBatchMove(sourceIds, folder.id, 'keep');
  });
};

const handleToggleStar = async (item: ContentItem) => {
  const targetValue = !Boolean(item.isStarred);

  try {
    if (item.itemType === 'file') {
      await toggleFileStar(item.id, targetValue);
    } else {
      await toggleFolderStar(item.id, targetValue);
    }

    const target = fileStore.items.find((entry) => entry.id === item.id);
    if (target) target.isStarred = targetValue;
  } catch (error) {
    console.error('Failed to update star status', error);
  }
};

const clearSearch = () => {
  handleSearch({ query: '' });
};

const isExtractDialogVisible = ref(false);
const fileToExtract = ref<FileItem | null>(null);

const handleExtractArchive = (file: FileItem) => {
  fileToExtract.value = file;
  isExtractDialogVisible.value = true;
};

onMounted(() => {
  fileStore.fetchFolderContents('root');
  eventBus.on('move-items', handleSidebarMove);
  eventBus.on('search-files', handleSearch);
});

onUnmounted(() => {
  eventBus.off('move-items', handleSidebarMove);
  eventBus.off('search-files', handleSearch);
  if (autoRefreshTimer !== null) {
    window.clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
});
</script>

<template>
  <div class="my-files-page">
    <input ref="fileInput" type="file" style="display: none" multiple @change="handleFileSelect" />

    <header class="page-header">
      <div class="header-left">
        <Breadcrumb :path="path" @navigate="navigateByBreadcrumb" @drop-on-folder="handleBreadcrumbDrop" />

        <div v-if="isSearching" class="search-tag">
          <span>Search: "{{ searchQuery }}"</span>
          <button class="text-btn" @click="clearSearch">Clear</button>
        </div>
      </div>

      <div class="header-actions">
        <div v-if="selectedCount > 0" class="batch-actions">
          <span>{{ selectedCount }} selected</span>
          <button class="secondary-btn" @click="startMoveForSelection(Array.from(selectedItems))">Move</button>
          <button class="secondary-btn" @click="handleBatchDownload">Download</button>
          <button class="danger-btn" @click="handleBatchDelete">Delete</button>
        </div>

        <div class="view-switcher" role="tablist" aria-label="View mode">
          <button :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'">Grid</button>
          <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">List</button>
        </div>

        <button class="secondary-btn" @click="setSort('name')">
          Sort: {{ sortKey }} {{ sortDirection === 'asc' ? 'ASC' : 'DESC' }}
        </button>

        <button class="secondary-btn" @click="handleCreateFolder">New Folder</button>
        <button class="primary-btn" @click="triggerFileInput">Upload</button>
      </div>
    </header>

    <MoveItemDialog
      :is-visible="isMoveDialogVisible"
      :item-to-move="itemToMove"
      :item-count="moveItemCount"
      :has-active-share="moveHasActiveShare"
      :default-share-handling="'keep'"
      @close="closeMoveDialog"
      @confirm="handleMoveConfirm"
    />

    <ShareDialog :is-visible="isShareDialogVisible" :item-to-share="itemToShare" @close="isShareDialogVisible = false" />

    <ExtractArchiveDialog
      :is-visible="isExtractDialogVisible"
      :file="fileToExtract"
      :current-folder-id="currentFolderId"
      @close="isExtractDialogVisible = false"
    />

    <div v-if="uploadTasks.length" class="upload-progress-area">
      <h4>Upload Queue</h4>
      <div v-for="task in uploadTasks" :key="task.id" class="upload-task">
        <span class="task-name">{{ task.name }}</span>
        <div class="progress-track"><div class="progress-fill" :style="{ width: `${task.progress.percentage}%` }" /></div>
        <span class="task-percent">{{ task.progress.percentage }}%</span>
      </div>
    </div>

    <div class="file-display-area" @dragenter="handleDragEnter" @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop">
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-overlay-content">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m0-12l4 4m-4-4l-4 4M4 15v5h16v-5" /></svg>
          <p>Drop files to upload</p>
        </div>
      </div>

      <div v-if="isLoading" class="state">Loading...</div>

      <div v-else-if="displayItems.length === 0" class="state">
        <p v-if="isSearching">No matching result.</p>
        <p v-else>This folder is empty. Upload files or create a folder.</p>
      </div>

      <FileItemsView
        v-else
        :view-mode="viewMode"
        :display-items="displayItems"
        :renaming-item-id="renamingItemId"
        :rename-input-value="renameInputValue"
        :is-selected="isSelected"
        @update:rename-input-value="renameInputValue = $event"
        @toggle-selection="toggleSelection"
        @item-click="handleItemClick"
        @drag-item-start="({ event, item }) => handleDragItemStart(event, item)"
        @folder-drop="({ event, folder }) => handleFolderDrop(event, folder)"
        @toggle-star="handleToggleStar"
        @finish-rename="finishRename"
        @cancel-rename="cancelRename"
        @sort="setSort"
        @download="handleDownload"
        @start-rename="startRename"
        @start-move="startMove"
        @start-share="startShare"
        @extract-archive="handleExtractArchive"
        @delete="handleDelete"
      />
    </div>
  </div>
</template>

<style scoped>
.my-files-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.header-left {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.search-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--color-text-secondary);
}

.text-btn,
.primary-btn,
.secondary-btn,
.danger-btn {
  height: 34px;
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0 12px;
  cursor: pointer;
}

.text-btn,
.secondary-btn {
  background-color: var(--color-bg-primary);
  border-color: var(--color-border);
}

.primary-btn {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
}

.danger-btn {
  background-color: var(--color-danger-light);
  border-color: #fca5a5;
  color: var(--color-danger-dark);
}

.batch-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 4px 8px;
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 10px;
}

.view-switcher {
  display: inline-flex;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background-color: var(--color-bg-tertiary);
  padding: 2px;
}

.view-switcher button {
  width: 64px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}

.view-switcher button.active {
  background-color: var(--color-bg-primary);
  box-shadow: var(--shadow-sm);
}

.upload-progress-area {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-md);
}

.upload-progress-area h4 {
  margin-bottom: var(--spacing-sm);
}

.upload-task {
  display: grid;
  grid-template-columns: 220px 1fr 52px;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 8px;
}

.task-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-text-secondary);
}

.progress-track {
  height: 8px;
  border-radius: 999px;
  background-color: var(--color-bg-quaternary);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), #4ea8ff);
}

.task-percent {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.file-display-area {
  position: relative;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-md);
  overflow: auto;
}

.drag-overlay {
  position: absolute;
  inset: 10px;
  border: 2px dashed var(--color-primary);
  border-radius: var(--border-radius-md);
  background-color: rgba(var(--color-primary-rgb), 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 5;
}

.drag-overlay-content {
  text-align: center;
  color: var(--color-primary-dark);
}

.drag-overlay-content svg {
  width: 42px;
  height: 42px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
}

.state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .upload-task {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>



