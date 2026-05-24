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
import { useFileDragMove } from '../../composables/useFileDragMove';
import { useFilePreview } from '../../composables/useFilePreview';
import { toggleFileStar } from '../../api/file';
import { toggleFolderStar } from '../../api/folder';
import { useLocaleStore } from '../../store/locale';
import { EmptyState, FileTable, FileToolbar, BulkActionBar, UploadProgressTray } from '../../components/organisms/files';
import Breadcrumb from '../../components/common/Breadcrumb.vue';
import MoveItemDialog from '../../components/common/MoveItemDialog.vue';
import ShareDialog from '../../components/common/ShareDialog.vue';
import ExtractArchiveDialog from './components/ExtractArchiveDialog.vue';
import { eventBus } from '../../utils/eventBus';
import type { ContentItem, FileItem } from '../../types/file';
import { isArchiveFileName } from '../../utils/archive';
import { ui } from '../../utils/ui';

const fileStore = useFileStore();
const localeStore = useLocaleStore();
const t = localeStore.t;
const { items, path, isLoading, currentFolderId } = storeToRefs(fileStore);
const { settings } = storeToRefs(useSettingsStore());
const fileInput = ref<HTMLInputElement | null>(null);
const resumeFileInput = ref<HTMLInputElement | null>(null);

const searchQuery = ref(''); const isSearching = ref(false); const searchResults = ref<ContentItem[]>([]);
const selection = useFileSelection();
const { selectedItems, selectedCount, clear: clearSelection } = selection;
const a = useFileActions(currentFolderId);
const { handleBatchDownload, handleBatchDelete } = useBatchActions(selectedItems, clearSelection);
const {
  uploadTasks,
  isDragging,
  handleDragEnter,
  handleDragLeave,
  handleDragOver,
  handleDrop,
  handleFileSelect,
  cancelUpload,
  resumeUpload,
} = useUpload(currentFolderId);
const { sortedItems, setSort, sortKey, sortDirection } = useFileSorting(items);
const drag = useFileDragMove({ isSelected: selection.isSelected, selectedItems, handleBatchMove: a.handleBatchMove });
const { openPreview } = useFilePreview();

const viewMode = ref<'list' | 'grid'>((localStorage.getItem('fileflash-view-mode') as 'list' | 'grid') || 'list');
watch(viewMode, (v) => localStorage.setItem('fileflash-view-mode', v));

const displayItems = computed(() => isSearching.value
  ? [...searchResults.value].sort((x, y) => x.name.localeCompare(y.name))
  : sortedItems.value);

const isExtractDialogVisible = ref(false); const fileToExtract = ref<FileItem | null>(null);
const pendingResumeTaskId = ref<string | null>(null);

const onSearch = async (query: string) => {
  searchQuery.value = query;
  if (!query) { isSearching.value = false; searchResults.value = []; return; }
  isSearching.value = true;
  try { searchResults.value = await fileStore.searchInFolder(currentFolderId.value || 'root', query); } catch { searchResults.value = []; }
};
const onSearchEvt = ({ query }: { query: string }) => onSearch(query);

const onItemSelect = ({ item, modifiers }: { item: ContentItem; modifiers: { shift: boolean } }) => {
  if (a.renamingItemId.value === item.id) return;
  if (modifiers.shift && selection.lastSelectedId.value) {
    selection.selectRange(item.id, displayItems.value);
  } else {
    selection.toggleAdd(item.id);
  }
};

const onItemActivate = (item: ContentItem) => {
  if (a.renamingItemId.value === item.id) return;
  if (item.itemType === 'folder') {
    isSearching.value = false; searchQuery.value = ''; searchResults.value = [];
    fileStore.navigateToFolder(item.id);
    return;
  }
  if (isArchiveFileName(item.name)) {
    fileToExtract.value = item;
    isExtractDialogVisible.value = true;
    return;
  }
  fileStore.previewFile = item;
  openPreview(item);
};

const onClearSelection = () => selection.clear();

const resolveStarErrorMessage = (error: unknown): string => {
  const maybeResponseMessage = (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
  if (typeof maybeResponseMessage === 'string' && maybeResponseMessage.trim()) {
    return maybeResponseMessage.trim();
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  return t('files.star.toast.unknownError');
};

const onToggleStar = async (item: ContentItem) => {
  const next = !item.isStarred;
  try {
    if (item.itemType === 'file') await toggleFileStar(item.id, next); else await toggleFolderStar(item.id, next);
    const f = fileStore.items.find((e) => e.id === item.id); if (f) f.isStarred = next;
    eventBus.emit('refresh-file-tree');
  } catch (e) {
    const reason = resolveStarErrorMessage(e);
    ui.toast({
      type: 'error',
      message: t('files.star.toast.failed').replace('{reason}', reason),
    });
  }
};
const navigateBC = (id: string) => { isSearching.value = false; searchQuery.value = ''; searchResults.value = []; fileStore.navigateToFolder(id); };

const handleResumeTask = (taskId: string | number) => {
  pendingResumeTaskId.value = String(taskId);
  resumeFileInput.value?.click();
};

const handleResumeFileSelect = async (event: Event) => {
  const taskId = pendingResumeTaskId.value;
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  target.value = '';
  pendingResumeTaskId.value = null;
  if (!taskId || !file) return;
  await resumeUpload(taskId, file);
};

let timer: number | null = null;
watch(() => [settings.value.autoRefreshInterval, currentFolderId.value], () => {
  if (timer !== null) { window.clearInterval(timer); timer = null; }
  const s = Number(settings.value.autoRefreshInterval || 0); if (s <= 0) return;
  timer = window.setInterval(() => fileStore.fetchFolderContents(currentFolderId.value || 'root', { silent: true }), s * 1000);
}, { immediate: true });

onMounted(() => { fileStore.fetchFolderContents('root'); eventBus.on('move-items', drag.onSidebarMove); eventBus.on('search-files', onSearchEvt); });
onUnmounted(() => { eventBus.off('move-items', drag.onSidebarMove); eventBus.off('search-files', onSearchEvt); if (timer !== null) window.clearInterval(timer); });
</script>

<template>
  <div class="page" @dragenter="handleDragEnter" @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop">
    <input ref="fileInput" type="file" multiple hidden @change="handleFileSelect" />
    <input ref="resumeFileInput" type="file" hidden @change="handleResumeFileSelect" />

    <FileToolbar
      :view-mode="viewMode" :sort-key="sortKey" :sort-direction="sortDirection"
      :search-query="searchQuery" :is-searching="isSearching"
      @update:view-mode="viewMode = $event" @update:search-query="onSearch"
      @clear-search="onSearch('')" @sort="setSort"
      @create-folder="a.handleCreateFolder" @upload="fileInput?.click()"
    >
      <template #breadcrumb>
        <Breadcrumb :path="path" @navigate="navigateBC" @drop-on-folder="drag.onBreadcrumbDrop" />
      </template>
    </FileToolbar>

    <UploadProgressTray :tasks="uploadTasks" @cancel="cancelUpload" @resume="handleResumeTask" />

    <div class="page__body">
      <div v-if="isDragging" class="page__drag">{{ t('files.drag.dropToUpload') }}</div>
      <FileTable v-if="displayItems.length > 0"
        :mode="viewMode" :items="displayItems" :selection="selectedItems"
        :renaming-id="a.renamingItemId.value" :rename-value="a.renameInputValue.value"
        :register-rename-input="a.registerRenameInput"
        :sort-key="sortKey" :sort-direction="sortDirection"
        @update:rename-value="a.renameInputValue.value = $event"
        @toggle-select="selection.toggleSelection" @select="onItemSelect" @activate="onItemActivate"
        @clear-selection="onClearSelection" @toggle-star="onToggleStar"
        @download="a.handleDownload" @extract-archive="(f: FileItem) => { fileToExtract = f; isExtractDialogVisible = true; }"
        @start-rename="a.startRename" @cancel-rename="a.cancelRename" @finish-rename="a.finishRename"
        @start-move="a.startMove" @start-share="a.startShare" @delete="a.handleDelete"
        @dragstart="drag.onDragItemStart" @drop-on-folder="drag.onFolderDrop" @sort="setSort"
      />
      <EmptyState v-else-if="isLoading" variant="loading" />
      <EmptyState v-else-if="isSearching" variant="no-results" :query="searchQuery" />
      <EmptyState v-else variant="empty" />
    </div>

    <MoveItemDialog :is-visible="a.isMoveDialogVisible.value" :item-to-move="a.itemToMove.value"
      :item-count="a.moveItemCount.value" :has-active-share="a.moveHasActiveShare.value" :default-share-handling="'keep'"
      @close="a.closeMoveDialog" @confirm="a.handleMoveConfirm" />
    <ShareDialog :is-visible="a.isShareDialogVisible.value" :item-to-share="a.itemToShare.value"
      @close="a.isShareDialogVisible.value = false" />
    <ExtractArchiveDialog :is-visible="isExtractDialogVisible" :file="fileToExtract" :current-folder-id="currentFolderId"
      @close="isExtractDialogVisible = false" />

    <Transition name="bulk-bar">
      <div v-if="selectedCount > 0" class="page__bulk-bar-wrap">
        <BulkActionBar :count="selectedCount"
          @move="a.startMoveForSelection(Array.from(selectedItems))"
          @download="handleBatchDownload" @delete="handleBatchDelete" @clear="clearSelection" />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; height: 100%; min-height: 0; position: relative; }
.page__body { flex: 1; min-height: 0; overflow: auto; position: relative; }
.page__drag {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgb(var(--ac-rgb) / 0.08);
  border: 1px dashed var(--ac); color: var(--ac);
  font-family: var(--font-mono); letter-spacing: 0.18em;
  pointer-events: none; z-index: 5;
}
.page__bulk-bar-wrap {
  position: absolute;
  left: 0; right: 0;
  bottom: 16px;
  display: flex;
  justify-content: center;
  z-index: 20;
  pointer-events: none;
}
.page__bulk-bar-wrap > :deep(.bulk) {
  pointer-events: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}
.bulk-bar-enter-active,
.bulk-bar-leave-active {
  transition:
    transform var(--mo-duration-mid) var(--mo-easing),
    opacity var(--mo-duration-mid) var(--mo-easing);
}
.bulk-bar-enter-from,
.bulk-bar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
