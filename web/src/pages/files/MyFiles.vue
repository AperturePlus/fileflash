<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useFileStore } from '../../store/file';
import { useFileSelection } from '../../composables/useFileSelection';
import { useFileActions } from '../../composables/useFileActions';
import { useBatchActions } from '../../composables/useBatchActions';
import { useUpload } from '../../composables/useUpload';
import { useFileSorting } from '../../composables/useFileSorting';
import { toggleFileStar } from '../../api/file';
import { toggleFolderStar } from '../../api/folder';
import Breadcrumb from '../../components/common/Breadcrumb.vue';
import DropdownMenu from '../../components/common/DropdownMenu.vue';
import MoveItemDialog from '../../components/common/MoveItemDialog.vue';
import ShareDialog from '../../components/common/ShareDialog.vue';
import { eventBus } from '../../utils/eventBus';
import { getIconForFile } from '../../utils/fileIcons';
import type { ContentItem, FileItem, FolderItem } from '../../types/file';

const fileStore = useFileStore();
const { items, path, isLoading, currentFolderId } = storeToRefs(fileStore);
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
  renameInput,
  itemToMove,
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

const displayItems = computed(() => {
  if (isSearching.value) {
    return [...searchResults.value].sort((a, b) => a.name.localeCompare(b.name));
  }
  return sortedItems.value;
});

const handleSidebarMove = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[]; targetFolderId: string; targetFolderName: string }) => {
  const canMove = window.confirm(`Move ${sourceItemIds.length} item(s) to \"${targetFolderName}\"?`);
  if (!canMove) return;
  handleBatchMove(sourceItemIds, targetFolderId);
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
  const canMove = window.confirm(`Move ${sourceItemIds.length} item(s) to this folder?`);
  if (!canMove) return;
  handleBatchMove(sourceItemIds, targetFolderId);
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

  const canMove = window.confirm(`Move ${sourceIds.length} item(s) into \"${folder.name}\"?`);
  if (!canMove) return;

  handleBatchMove(sourceIds, folder.id);
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

onMounted(() => {
  fileStore.fetchFolderContents('root');
  eventBus.on('move-items', handleSidebarMove);
  eventBus.on('search-files', handleSearch);
});

onUnmounted(() => {
  eventBus.off('move-items', handleSidebarMove);
  eventBus.off('search-files', handleSearch);
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
          <button class="secondary-btn" @click="handleBatchDownload">Download</button>
          <button class="danger-btn" @click="handleBatchDelete">Delete</button>
        </div>

        <div class="view-switcher" role="tablist" aria-label="View mode">
          <button :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'">Grid</button>
          <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">List</button>
        </div>

        <button class="secondary-btn" @click="setSort('name')">
          Sort: {{ sortKey }} {{ sortDirection === 'asc' ? '↑' : '↓' }}
        </button>

        <button class="secondary-btn" @click="handleCreateFolder">New Folder</button>
        <button class="primary-btn" @click="triggerFileInput">Upload</button>
      </div>
    </header>

    <MoveItemDialog
      :is-visible="isMoveDialogVisible"
      :item-to-move="itemToMove"
      @close="closeMoveDialog"
      @confirm="handleMoveConfirm"
    />

    <ShareDialog :is-visible="isShareDialogVisible" :item-to-share="itemToShare" @close="isShareDialogVisible = false" />

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

      <div v-else-if="viewMode === 'list'" class="file-list">
        <div class="list-header">
          <div class="col checkbox" />
          <button class="col name" @click="setSort('name')">Name</button>
          <button class="col size" @click="setSort('size')">Size</button>
          <button class="col time" @click="setSort('updatedAt')">Updated</button>
          <div class="col actions" />
        </div>

        <div
          v-for="item in displayItems"
          :key="`list-${item.id}`"
          class="list-row"
          :class="{ selected: isSelected(item.id) }"
          draggable="true"
          @dragstart="handleDragItemStart($event, item)"
          @click="handleItemClick(item)"
          @drop.prevent="item.itemType === 'folder' && handleFolderDrop($event, item as FolderItem)"
          @dragover.prevent
        >
          <div class="col checkbox" @click.stop>
            <input type="checkbox" :checked="isSelected(item.id)" @change.stop="toggleSelection(item.id)" />
          </div>

          <div class="col name name-cell">
            <img v-if="item.itemType === 'folder'" src="../../assets/generic/folder.svg" alt="Folder" class="icon" />
            <img v-else :src="getIconForFile(item.name)" alt="File" class="icon" />

            <input
              v-if="renamingItemId === item.id"
              ref="renameInput"
              v-model="renameInputValue"
              class="rename-input"
              @blur="finishRename"
              @keydown.enter.prevent="finishRename"
              @keydown.esc.prevent="cancelRename"
            />
            <span v-else>{{ item.name }}</span>

            <button class="star-btn" :class="{ active: item.isStarred }" @click.stop="handleToggleStar(item)">`r`n              Star`r`n            </button>
          </div>

          <div class="col size">{{ item.itemType === 'file' ? `${(item.size / 1024).toFixed(1)} KB` : '--' }}</div>
          <div class="col time">{{ new Date(item.updatedAt).toLocaleString() }}</div>

          <div class="col actions" @click.stop>
            <DropdownMenu>
              <template #trigger>
                <button class="menu-btn">...</button>
              </template>
              <template #content>
                <div class="item-menu">
                  <button v-if="item.itemType === 'file'" @click="handleDownload(item as FileItem)">Download</button>
                  <button @click="startRename(item)">Rename</button>
                  <button @click="startMove(item)">Move</button>
                  <button @click="startShare(item)">Share</button>
                  <button @click="handleToggleStar(item)">{{ item.isStarred ? 'Unstar' : 'Star' }}</button>
                  <button class="danger" @click="handleDelete(item)">Delete</button>
                </div>
              </template>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <div v-else class="file-grid">
        <div
          v-for="item in displayItems"
          :key="`grid-${item.id}`"
          class="grid-card"
          :class="{ selected: isSelected(item.id) }"
          draggable="true"
          @dragstart="handleDragItemStart($event, item)"
          @click="handleItemClick(item)"
          @drop.prevent="item.itemType === 'folder' && handleFolderDrop($event, item as FolderItem)"
          @dragover.prevent
        >
          <div class="grid-check" @click.stop>
            <input type="checkbox" :checked="isSelected(item.id)" @change.stop="toggleSelection(item.id)" />
          </div>

          <button class="star-btn floating" :class="{ active: item.isStarred }" @click.stop="handleToggleStar(item)">Star</button>

          <img v-if="item.itemType === 'folder'" src="../../assets/generic/folder.svg" alt="Folder" class="grid-icon" />
          <img v-else :src="getIconForFile(item.name)" alt="File" class="grid-icon" />

          <div class="grid-name">
            <input
              v-if="renamingItemId === item.id"
              ref="renameInput"
              v-model="renameInputValue"
              class="rename-input"
              @blur="finishRename"
              @keydown.enter.prevent="finishRename"
              @keydown.esc.prevent="cancelRename"
            />
            <span v-else>{{ item.name }}</span>
          </div>

          <div class="grid-actions" @click.stop>
            <DropdownMenu>
              <template #trigger>
                <button class="menu-btn">...</button>
              </template>
              <template #content>
                <div class="item-menu">
                  <button v-if="item.itemType === 'file'" @click="handleDownload(item as FileItem)">Download</button>
                  <button @click="startRename(item)">Rename</button>
                  <button @click="startMove(item)">Move</button>
                  <button @click="startShare(item)">Share</button>
                  <button @click="handleToggleStar(item)">{{ item.isStarred ? 'Unstar' : 'Star' }}</button>
                  <button class="danger" @click="handleDelete(item)">Delete</button>
                </div>
              </template>
            </DropdownMenu>
          </div>
        </div>
      </div>
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

.file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-header,
.list-row {
  display: grid;
  grid-template-columns: 44px 1.6fr 0.8fr 1.1fr 56px;
  align-items: center;
  gap: var(--spacing-sm);
}

.list-header {
  padding: 0 8px;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.list-header button {
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  color: inherit;
}

.list-row {
  min-height: 46px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 4px 8px;
}

.list-row:hover {
  background-color: var(--color-bg-tertiary);
}

.list-row.selected {
  background-color: var(--color-primary-light);
  border-color: rgba(var(--color-primary-rgb), 0.3);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.name-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.star-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-text-quaternary);
  cursor: pointer;
}

.star-btn.active {
  color: #f59e0b;
}

.star-btn:hover {
  border-color: var(--color-border);
}

.menu-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  cursor: pointer;
}

.item-menu {
  min-width: 140px;
  display: flex;
  flex-direction: column;
  padding: 6px;
}

.item-menu button {
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  padding: 0 8px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.item-menu button:hover {
  background-color: var(--color-bg-tertiary);
}

.item-menu button.danger {
  color: var(--color-danger);
}

.rename-input {
  width: 100%;
  border: 1px solid var(--color-primary);
  border-radius: 6px;
  padding: 2px 6px;
  background-color: var(--color-bg-primary);
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: var(--spacing-md);
}

.grid-card {
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background-color: var(--color-bg-primary);
  padding: 12px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.grid-card:hover {
  box-shadow: var(--shadow-sm);
}

.grid-card.selected {
  border-color: rgba(var(--color-primary-rgb), 0.6);
  background-color: var(--color-primary-light);
}

.grid-check {
  position: absolute;
  top: 8px;
  left: 8px;
}

.grid-icon {
  width: 62px;
  height: 62px;
  object-fit: contain;
  margin-top: 8px;
}

.grid-name {
  width: 100%;
  text-align: center;
  word-break: break-word;
  min-height: 40px;
}

.grid-actions {
  align-self: flex-end;
}

.star-btn.floating {
  position: absolute;
  top: 8px;
  right: 8px;
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

  .list-header,
  .list-row {
    grid-template-columns: 40px 1fr 90px 0;
  }

  .col.time,
  .col.actions {
    display: none;
  }
}
</style>



