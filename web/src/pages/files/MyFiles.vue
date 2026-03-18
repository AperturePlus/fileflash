<script setup lang="ts">
import { onMounted, ref, onUnmounted, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useFileStore } from '../../store/file';
import { useFileSelection } from '../../composables/useFileSelection';
import { useFileActions } from '../../composables/useFileActions';
import { useBatchActions } from '../../composables/useBatchActions';
import { useUpload } from '../../composables/useUpload';
import { useFileSorting } from '../../composables/useFileSorting';
import Breadcrumb from '../../components/common/Breadcrumb.vue';
import DropdownMenu from '../../components/common/DropdownMenu.vue';
import MoveItemDialog from '../../components/common/MoveItemDialog.vue';
import ShareDialog from '../../components/common/ShareDialog.vue';
import type { FolderItem, FileItem, ContentItem } from '../../types/file';
import { eventBus } from '../../utils/eventBus';
import { getIconForFile } from '../../utils/fileIcons';

const fileStore = useFileStore();
const { items, path, isLoading, currentFolderId } = storeToRefs(fileStore);
const fileInput = ref<HTMLInputElement | null>(null);

// 搜索相关状态
const searchQuery = ref('');
const isSearching = ref(false);
const searchResults = ref<ContentItem[]>([]);

// --- Composables ---
const { selectedItems, isSelected, toggleSelection, selectedCount, clearSelection } = useFileSelection();
const { 
  renamingItemId, renameInputValue, renameInput,
  itemToMove, isMoveDialogVisible, itemToShare, isShareDialogVisible,
  startRename, cancelRename, finishRename, handleDelete, 
  startMove, closeMoveDialog, handleMoveConfirm,
  /* startShare, */ handleDownload, handleCreateFolder, handleBatchMove
} = useFileActions(currentFolderId);
const { handleBatchDownload, handleBatchDelete } = useBatchActions(selectedItems, clearSelection);
const {
  uploadTasks, isDragging, handleDragEnter, handleDragLeave,
  handleDragOver, handleDrop, handleFileSelect
} = useUpload(currentFolderId);
const { sortedItems, setSort } = useFileSorting(items);

// 显示的项目列表（根据是否在搜索状态决定显示什么）
const displayItems = computed(() => {
  let sourceItems;
  if (isSearching.value) {
    sourceItems = [...searchResults.value].sort((a, b) => a.name.localeCompare(b.name));
  } else {
    sourceItems = sortedItems.value;
  }
  
  return sourceItems;
});


// --- Component Logic ---
onMounted(() => {
  fileStore.fetchFolderContents('root');
  eventBus.on('move-items', handleSidebarMove);
  eventBus.on('search-files', handleSearch);
});

onUnmounted(() => {
  eventBus.off('move-items', handleSidebarMove);
  eventBus.off('search-files', handleSearch);
});

const handleSidebarMove = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[], targetFolderId: string, targetFolderName: string }) => {
  if (confirm(`Are you sure you want to move ${sourceItemIds.length} item(s) to "${targetFolderName}"?`)) {
    handleBatchMove(sourceItemIds, targetFolderId);
  }
};

const handleSearch = async ({ query }: { query: string }) => {
  searchQuery.value = query;
  
  if (!query) {
    // 如果搜索查询为空，恢复正常的文件夹视图
    isSearching.value = false;
    searchResults.value = [];
    return;
  }
  
  isSearching.value = true;
  try {
    // 使用当前文件夹进行搜索
    const response = await fileStore.searchInFolder(currentFolderId.value || 'root', query);
    searchResults.value = response;
  } catch (error) {
    console.error('Search failed:', error);
    searchResults.value = [];
  }
};

const triggerFileInput = () => fileInput.value?.click();

const handleBreadcrumbNavigation = (folderId: string) => {
  // 清除搜索状态当通过面包屑导航时
  if (isSearching.value) {
    isSearching.value = false;
    searchQuery.value = '';
    searchResults.value = [];
  }
  fileStore.navigateToFolder(folderId);
};

const handleBreadcrumbDrop = ({ sourceItemIds, targetFolderId }: { sourceItemIds: string[], targetFolderId: string }) => {
  const filesToMove = fileStore.items.filter(i => sourceItemIds.includes(i.id));
  const targetFolder = fileStore.path.find(p => p.folderId === targetFolderId);

  if (!targetFolder) return;
  
  if (confirm(`Are you sure you want to move ${filesToMove.length} item(s) to "${targetFolder.name}"?`)) {
    handleBatchMove(sourceItemIds, targetFolderId);
  }
};

const handleItemClick = (item: ContentItem) => {
  if (renamingItemId.value === item.id) return;
  
  if (item.itemType === 'folder') {
    // 清除搜索状态当导航到文件夹时
    if (isSearching.value) {
      isSearching.value = false;
      searchQuery.value = '';
      searchResults.value = [];
    }
    fileStore.navigateToFolder(item.id);
  } else {
    // A regular click on a file now selects it for preview
    fileStore.selectedFile = item;
  }
};

const handleDragItemStart = (e: DragEvent, item: ContentItem) => {
  if (e.dataTransfer) {
    // If the dragged item is part of a selection, drag all selected items
    const itemsToDrag = isSelected(item.id) 
      ? Array.from(selectedItems.value) 
      : [item.id];

    e.dataTransfer.setData('application/fileflash-item-ids', JSON.stringify(itemsToDrag));
    e.dataTransfer.effectAllowed = 'move';
  }
};

const handleFolderDrop = (e: DragEvent, targetFolder: FolderItem) => {
  e.preventDefault();
  e.stopPropagation();
  const sourceItemIdsJSON = e.dataTransfer?.getData('application/fileflash-item-ids');
  if (!sourceItemIdsJSON) return;
  
  const sourceItemIds = JSON.parse(sourceItemIdsJSON);
  
  // Prevent dropping a folder into itself
  if (sourceItemIds.includes(targetFolder.id)) return;

  const filesToMove = fileStore.items.filter(i => sourceItemIds.includes(i.id));

  if (confirm(`Are you sure you want to move ${filesToMove.length} item(s) into "${targetFolder.name}"?`)) {
    handleBatchMove(sourceItemIds, targetFolder.id);
  }
};

type ViewMode = 'grid' | 'list';
const viewMode = ref<ViewMode>('grid');

</script>

<template>
  <div class="my-files-page">
    <input type="file" ref="fileInput" @change="handleFileSelect" style="display: none" multiple />
    <header class="page-header">
      <div class="header-left">
        <Breadcrumb 
          :path="path" 
          @navigate="handleBreadcrumbNavigation"
          @drop-on-folder="handleBreadcrumbDrop"
        />
        <div v-if="isSearching" class="search-indicator">
          <span class="search-icon">🔍</span>
          <span>搜索结果: "{{ searchQuery }}"</span>
          <button @click="handleSearch({ query: '' })" class="clear-search-btn">✕</button>
        </div>
      </div>
      <div class="header-actions">
        <div v-if="selectedCount > 0" class="batch-actions">
          <span>{{ selectedCount }} selected</span>
          <button @click="handleBatchDownload" class="batch-action-btn">Download</button>
          <button @click="handleBatchDelete" class="batch-action-btn danger">Delete</button>
        </div>
        <div class="view-switcher">
          <button @click="viewMode = 'grid'" :class="{ active: viewMode === 'grid' }">Grid</button>
          <button @click="viewMode = 'list'" :class="{ active: viewMode === 'list' }">List</button>
        </div>
        <button class="action-btn" @click="handleCreateFolder">
          <span>+ New Folder</span>
        </button>
        <button class="upload-btn" @click="triggerFileInput">
          <span>⬆️ Upload</span>
        </button>
      </div>
    </header>

    <MoveItemDialog
      :is-visible="isMoveDialogVisible"
      :item-to-move="itemToMove"
      @close="closeMoveDialog"
      @confirm="handleMoveConfirm"
    />

    <ShareDialog
      :is-visible="isShareDialogVisible"
      :item-to-share="itemToShare"
      @close="isShareDialogVisible = false"
    />

    <!-- Upload Progress Section -->
    <div v-if="uploadTasks.length > 0" class="upload-progress-area">
      <h4>Uploading...</h4>
      <div v-for="task in uploadTasks" :key="task.id" class="upload-task">
        <span class="task-name">{{ task.name }}</span>
        <div class="progress-bar-container">
          <div 
            class="progress-bar" 
            :style="{ width: task.progress.percentage + '%' }"
          ></div>
        </div>
        <span class="task-percentage">{{ task.progress.percentage }}%</span>
      </div>
    </div>
    
    <div 
      class="file-display-area"
      @dragenter="handleDragEnter"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <!-- Drag and Drop Overlay -->
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-overlay-content">
          <span>⬆️</span>
          <p>Drop files here to upload</p>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-indicator">
        Loading...
      </div>
      
      <!-- 搜索结果为空的状态 -->
      <div v-else-if="isSearching && searchResults.length === 0" class="empty-search-state">
        <div class="empty-content">
          <span class="empty-icon">🔍</span>
          <h3>未找到匹配的文件</h3>
          <p>尝试使用不同的关键词进行搜索</p>
        </div>
      </div>
      
      <!-- 空文件夹状态 -->
      <div v-else-if="!isSearching && displayItems.length === 0" class="empty-folder-state">
        <div class="empty-content">
          <span class="empty-icon">📁</span>
          <h3>文件夹为空</h3>
          <p>点击上传按钮添加文件，或创建新文件夹</p>
        </div>
      </div>
      <!-- List View -->
      <div v-if="viewMode === 'list' && !isLoading" class="file-list">
       <!-- List Header -->
      <div class="list-header">
        <div class="list-cell select-all"></div>
        <button class="list-cell name" @click="setSort('name')">Name</button>
        <button class="list-cell size" @click="setSort('size')">Size</button>
        <button class="list-cell modified" @click="setSort('updatedAt')">Last Modified</button>
        <div class="list-cell actions"></div>
      </div>
      <!-- List Body -->
      <div 
        v-for="(item, index) in displayItems" 
        :key="`list-${item.id}-${index}`"
        class="list-item"
        :class="{ 'checkbox-selected': isSelected(item.id) }"
        @click="handleItemClick(item)"
        draggable="true"
        @dragstart="handleDragItemStart($event, item)"
        @drop.prevent="item.itemType === 'folder' && handleFolderDrop($event, item as FolderItem)"
        @dragover.prevent="item.itemType === 'folder' && $event.dataTransfer && ($event.dataTransfer.dropEffect = 'move')"
      >
        <div class="list-cell select-cell" @click.stop>
          <input 
            type="checkbox" 
            :checked="isSelected(item.id)"
            @change.stop="toggleSelection(item.id)"
            class="list-checkbox"
          />
        </div>
        <div class="list-cell name-cell">
          <img v-if="item.itemType === 'folder'" src="../../assets/generic/folder.svg" alt="" class="item-icon-small" />
          <img v-else :src="getIconForFile(item.name)" alt="" class="item-icon-small" />
          <span v-if="renamingItemId !== item.id" class="item-name">{{ item.name }}</span>
          <input 
            v-else
            ref="renameInput"
            v-model="renameInputValue"
            class="rename-input"
            @blur="finishRename"
            @keydown.enter.prevent="finishRename"
            @keydown.esc.prevent="cancelRename"
          />
        </div>
        <div class="list-cell size-cell">{{ item.size ? (item.size / 1024).toFixed(1) + ' KB' : '--' }}</div>
        <div class="list-cell modified-cell">{{ new Date(item.updatedAt).toLocaleDateString() }}</div>
        <div class="list-cell actions-cell" @click.stop>
          <DropdownMenu>
            <template #trigger>
              <button class="kebab-btn"><span>⋮</span></button>
            </template>
            <template #content>
               <div class="dropdown-content">
                <button v-if="item.itemType === 'file'" @click="handleDownload(item as FileItem)" class="dropdown-item">
                  <span class="dropdown-item-icon">⬇️</span>
                  <span>Download</span>
                </button>
                <template v-if="!item.permission || item.permission === 'owner' || item.permission === 'write'">
                  <button @click="startRename(item)" class="dropdown-item">
                    <span class="dropdown-item-icon">✏️</span>
                    <span>Rename</span>
                  </button>
                  <button @click="startMove(item)" class="dropdown-item">
                    <span class="dropdown-item-icon">➡️</span>
                    <span>Move</span>
                  </button>
                </template>
                <!-- Share功能暂时禁用 - 后端未实现
                <button @click="startShare(item)" class="dropdown-item">
                  <span class="dropdown-item-icon">🤝</span>
                  <span>Share</span>
                </button>
                -->
                <button v-if="!item.permission || item.permission === 'owner' || item.permission === 'write'" @click="handleDelete(item)" class="dropdown-item danger">
                  <span class="dropdown-item-icon">🗑️</span>
                  <span>Delete</span>
                </button>
              </div>
            </template>
          </DropdownMenu>
        </div>
      </div>
    </div>
    
    <!-- Grid View -->
    <div v-if="viewMode === 'grid' && !isLoading" class="file-grid">
      <div 
        v-for="(item, index) in displayItems" 
        :key="`grid-${item.id}-${index}`"
        class="grid-item"
        :class="{ 'checkbox-selected': isSelected(item.id) }"
        @click="handleItemClick(item)"
        draggable="true"
        @dragstart="handleDragItemStart($event, item)"
        @drop.prevent="item.itemType === 'folder' && handleFolderDrop($event, item as FolderItem)"
        @dragover.prevent="item.itemType === 'folder' && $event.dataTransfer && ($event.dataTransfer.dropEffect = 'move')"
      >
        <div class="checkbox-container" :class="{ 'always-visible': isSelected(item.id) }" @click.stop>
          <input 
            type="checkbox" 
            class="item-checkbox" 
            :checked="isSelected(item.id)"
            @change.stop="toggleSelection(item.id)"
          />
        </div>
        <img v-if="item.itemType === 'folder'" src="../../assets/generic/folder.svg" alt="Folder" class="item-icon" />
        <img v-else :src="getIconForFile(item.name)" alt="File" class="item-icon" />
        <div class="item-name-wrapper">
          <span v-if="renamingItemId !== item.id" class="item-name">{{ item.name }}</span>
          <input
            v-else
            ref="renameInput"
            v-model="renameInputValue"
            class="rename-input"
            @blur="finishRename"
            @keydown.enter.prevent="finishRename"
            @keydown.esc.prevent="cancelRename"
          />
        </div>
        
        <div class="item-actions" @click.stop>
          <DropdownMenu>
            <template #trigger>
              <button class="kebab-btn">
                <span>⋮</span>
              </button>
            </template>
            <template #content>
              <div class="dropdown-content">
                 <button v-if="item.itemType === 'file'" @click="handleDownload(item as FileItem)" class="dropdown-item">
                  <span class="dropdown-item-icon">⬇️</span>
                  <span>Download</span>
                </button>
                <template v-if="!item.permission || item.permission === 'owner' || item.permission === 'write'">
                  <button @click="startRename(item)" class="dropdown-item">
                    <span class="dropdown-item-icon">✏️</span>
                    <span>Rename</span>
                  </button>
                  <button @click="startMove(item)" class="dropdown-item">
                    <span class="dropdown-item-icon">➡️</span>
                    <span>Move</span>
                  </button>
                </template>
                 <!-- Share功能暂时禁用 - 后端未实现
                 <button @click="startShare(item)" class="dropdown-item">
                  <span class="dropdown-item-icon">🤝</span>
                  <span>Share</span>
                </button>
                -->
                <button v-if="!item.permission || item.permission === 'owner' || item.permission === 'write'" @click="handleDelete(item)" class="dropdown-item danger">
                  <span class="dropdown-item-icon">🗑️</span>
                  <span>Delete</span>
                </button>
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
/* Styles are mostly the same, just adjusted the header */
.my-files-page {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  flex-shrink: 0;
  gap: var(--spacing-md);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.search-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-primary-light);
  border-radius: var(--border-radius-md);
  font-size: 0.875rem;
  color: var(--color-primary-dark);
}

.search-icon {
  font-size: 1rem;
}

.clear-search-btn {
  background: none;
  border: none;
  color: var(--color-primary-dark);
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  font-size: 0.875rem;
  transition: background-color var(--transition-base);
}

.clear-search-btn:hover {
  background-color: rgba(var(--color-primary-rgb), 0.2);
}

.empty-search-state,
.empty-folder-state {
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.empty-content {
  text-align: center;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
  opacity: 0.5;
}

.empty-content h3 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
  font-weight: var(--font-weight-semibold);
}

.empty-content p {
  margin: 0;
  font-size: 0.875rem;
  opacity: 0.8;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}
.batch-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-secondary);
}
.batch-actions span {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}
.batch-action-btn {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius-sm);
  border: 1px solid transparent;
  background-color: transparent;
  cursor: pointer;
  transition: all var(--transition-base);
}
.batch-action-btn:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-border-hover);
}
.batch-action-btn.danger {
  color: var(--color-danger);
}
.batch-action-btn.danger:hover {
  background-color: var(--color-danger-light);
  color: var(--color-danger-dark);
  border-color: var(--color-danger);
}

.action-btn {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-base);
}

.action-btn:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-border-hover);
}

.file-display-area {
  position: relative;
  flex-grow: 1;
  display: flex; /* To make the children (grid/list) take up space */
  flex-direction: column;
}

.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(var(--color-primary-rgb), 0.1);
  border: 2px dashed var(--color-primary);
  border-radius: var(--border-radius-lg);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10;
  pointer-events: none; /* Allow drop events to pass through */
}

.drag-overlay-content {
  text-align: center;
  color: var(--color-primary);
}

.drag-overlay-content span {
  font-size: 3rem;
}

.drag-overlay-content p {
  font-size: 1.2rem;
  font-weight: var(--font-weight-bold);
  margin-top: var(--spacing-md);
}

.file-grid {
  flex-grow: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--spacing-lg);
  overflow-y: auto;
}
.grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  transition: background-color var(--transition-base);
  cursor: pointer;
  height: fit-content;
  position: relative;
  border: 1px solid transparent; /* Add border for smooth transition */
}
.grid-item:hover {
  background-color: var(--color-bg-tertiary);
}
.grid-item.selected {
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary);
}
.grid-item.checkbox-selected {
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary);
}
.upload-btn {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
  border: none;
  border-radius: var(--border-radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background-color var(--transition-base);
}
.upload-btn:hover {
  background-color: var(--color-primary-hover);
}
.item-icon {
  width: 64px;
  height: 64px;
  margin-bottom: var(--spacing-sm);
  object-fit: contain;
}
.item-name {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  text-align: center;
  word-break: break-all;
}
.item-name-wrapper {
  width: 100%;
  text-align: center;
}
.rename-input {
  width: 100%;
  padding: var(--spacing-xs);
  font-size: 0.875rem;
  border-radius: var(--border-radius-sm);
  border: 1px solid var(--color-primary);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  text-align: center;
  box-sizing: border-box;
}
.upload-progress-area {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-md);
  box-shadow: var(--shadow-sm);
}
.upload-task {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-sm);
}
.task-name {
  flex-grow: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.progress-bar-container {
  width: 200px;
  height: 8px;
  background-color: var(--color-bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background-color: var(--color-primary);
  transition: width 0.3s ease;
}
.task-percentage {
  font-size: 0.875rem;
  font-weight: var(--font-weight-medium);
  width: 40px;
  text-align: right;
}
.checkbox-container {
  position: absolute;
  top: var(--spacing-sm);
  left: var(--spacing-sm);
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--transition-base);
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
.item-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}
/* 强制显示被勾选的复选框 */
.checkbox-container.always-visible {
  opacity: 1 !important;
  background-color: rgba(var(--color-primary-rgb), 0.1);
}
/* 鼠标悬停时显示 */
.grid-item:hover .checkbox-container {
  opacity: 1;
}
/* 项目被选中时显示 */
.grid-item.selected .checkbox-container,
.grid-item.checkbox-selected .checkbox-container {
  opacity: 1;
  background-color: rgba(var(--color-primary-rgb), 0.1);
}

.item-actions {
  position: absolute;
  bottom: var(--spacing-sm);
  right: var(--spacing-sm);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.grid-item:hover .item-actions,
.grid-item.selected .item-actions,
.grid-item.checkbox-selected .item-actions {
  opacity: 1;
}

.kebab-btn {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.2rem;
  line-height: 1;
}

.dark-theme .kebab-btn {
  background: rgba(var(--color-bg-tertiary), 0.7);
}

.dropdown-content {
  padding: var(--spacing-xs);
  min-width: 160px; /* Give the dropdown a bit more width */
  background-color: var(--color-bg-primary);
  border-radius: var(--border-radius-md);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}
/* dropdown item */
.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  width: 100%;
  text-align: left;
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  font-size: var(--font-size-base);
  cursor: pointer;
  white-space: nowrap; /* Prevent text from wrapping */
  border-radius: var(--border-radius-sm);
  transition: background-color 0.2s, color 0.2s;
}
.dropdown-item:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}
.dropdown-item.danger:hover {
  background-color: #fee2e2;
  color: #b91c1c;
}
.dark-theme .dropdown-item.danger:hover {
    background-color: #3f1a1a;
    color: #fca5a5;
}
.dropdown-item-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2em;
}
.dropdown-item.danger {
  color: #ef4444;
}

/* List View Styles */
.file-list {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.list-header, .list-item {
  display: grid;
  grid-template-columns: 40px 1fr 120px 200px 50px;
  gap: var(--spacing-md);
  align-items: center;
  padding: 0 var(--spacing-md);
}
.list-header {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}
.list-header button {
    background: none;
    border: none;
    cursor: pointer;
    font-weight: inherit;
    color: inherit;
    text-align: left;
}

.view-switcher {
  display: flex;
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
  padding: 2px;
}
.view-switcher button {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: none;
  background-color: transparent;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
}
.view-switcher button.active {
  background-color: var(--color-bg-secondary);
  box-shadow: var(--shadow-sm);
}

.list-item {
  border-radius: var(--border-radius-md);
  transition: background-color var(--transition-base);
  padding: var(--spacing-sm) var(--spacing-md);
}
.list-item:hover {
  background-color: var(--color-bg-tertiary);
}
.list-item.selected {
  background-color: var(--color-primary-light);
}
.list-item.checkbox-selected {
  background-color: var(--color-primary-light);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}
.item-icon-small {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
.actions-cell {
  display: flex;
  justify-content: flex-end;
}

/* 列表视图中的复选框始终可见 */
.list-checkbox {
  width: 18px;
  height: 18px;
}
</style> 