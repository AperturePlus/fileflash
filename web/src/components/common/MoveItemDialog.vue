<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import type { ContentItem, FolderItem } from '../../types/file';
import { getFolderContents } from '../../api/folder';
import FolderTreeNode from './FolderTreeNode.vue';
import FileTreeNode from './FileTreeNode.vue';
import { useLocaleStore } from '../../store/locale';
import { ui } from '../../utils/ui';

interface Props {
  isVisible: boolean;
  itemToMove: ContentItem | null;
  itemCount?: number;
  hasActiveShare?: boolean;
  defaultShareHandling?: 'keep' | 'revoke';
  enableShareHandling?: boolean;
  title?: string;
  prompt?: string;
  confirmText?: string;
  rootLabel?: string;
  treeVariant?: 'legacy' | 'modern';
}
const props = defineProps<Props>();
const localeStore = useLocaleStore();
const t = localeStore.t;

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'confirm', payload: { targetFolderId: string; shareHandling: 'keep' | 'revoke' }): void;
}>();

const rootFolders = ref<FolderItem[]>([]);
const isLoading = ref(false);
const selectedFolderId = ref<string | null>(null);
const shareHandling = ref<'keep' | 'revoke'>('keep');

const modalTitle = computed(() => {
  if (props.title) return props.title;
  const count = props.itemCount || (props.itemToMove ? 1 : 0);
  if (count <= 1 && props.itemToMove) {
    return t('move.dialog.title.single').replace('{itemName}', props.itemToMove.name);
  }
  if (count > 1) return t('move.dialog.title.multiple').replace('{count}', String(count));
  return t('move.dialog.title.default');
});

const promptText = computed(() => props.prompt || t('move.dialog.prompt'));
const confirmButtonText = computed(() => props.confirmText || t('move.dialog.confirm'));
const rootText = computed(() => props.rootLabel || t('move.dialog.root'));
const showShareHandling = computed(() => props.enableShareHandling !== false && Boolean(props.hasActiveShare));
const treeVariant = computed(() => props.treeVariant || 'legacy');

const fetchRootFolders = async () => {
  if (rootFolders.value.length > 0) return; // Don't re-fetch if already loaded
  isLoading.value = true;
  try {
    const response = await getFolderContents({ folderId: 'root' });
    let actualItems = response.items;

    // 特殊处理 root 文件夹的情况 - 与 store 中的逻辑保持一致
    if (actualItems.length === 1 && actualItems[0].name === 'root' && actualItems[0].itemType === 'folder') {
      // 如果请求 root 返回的是包含单个 root 文件夹的数组，则获取该文件夹的内容
      const rootFolderId = actualItems[0].id.toString();
      const rootContentsResponse = await getFolderContents({ folderId: rootFolderId });
      actualItems = rootContentsResponse.items;
    }

    rootFolders.value = actualItems.filter(item => item.itemType === 'folder') as FolderItem[];
  } catch (error) {
    console.error('Failed to load root folders:', error);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchRootFolders();
});

watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    selectedFolderId.value = null;
    shareHandling.value = props.defaultShareHandling || 'keep';
  }
});

const handleSelectFolder = (folderId: string) => {
  selectedFolderId.value = folderId;
};

const handleConfirm = () => {
  if (!selectedFolderId.value) {
    ui.toast({ type: 'warning', message: t('move.dialog.selectDestinationWarning') });
    return;
  }
  emit('confirm', {
    targetFolderId: selectedFolderId.value,
    shareHandling: showShareHandling.value ? shareHandling.value : 'keep',
  });
};

const handleModernTreeNavigate = (itemId: string) => {
  const folder = rootFolders.value.find((entry) => entry.id === itemId);
  if (folder) {
    handleSelectFolder(folder.id);
  }
};

const handleModernTreeSelectFolder = (folderId: string) => {
  handleSelectFolder(folderId);
};

</script>

<template>
  <transition name="modal-fade">
    <div v-if="isVisible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog">
        <header class="modal-header">
          <h3 class="modal-title">{{ modalTitle }}</h3>
          <button class="modal-close" @click="$emit('close')">&times;</button>
        </header>
        <div class="modal-body">
          <p class="prompt">{{ promptText }}</p>
          <div v-if="showShareHandling" class="share-options">
            <div class="share-label">{{ t('move.dialog.shareHandling.title') }}</div>
            <label>
              <input v-model="shareHandling" type="radio" value="keep" />
              <span>{{ t('move.dialog.shareHandling.keep') }}</span>
            </label>
            <label>
              <input v-model="shareHandling" type="radio" value="revoke" />
              <span>{{ t('move.dialog.shareHandling.revoke') }}</span>
            </label>
          </div>
          <div class="folder-tree-container">
            <div v-if="isLoading" class="loading-indicator">{{ t('move.dialog.loading') }}</div>
            <div v-else-if="rootFolders.length === 0" class="empty-state">{{ t('move.dialog.empty') }}</div>
            <div v-else>
              <div 
                class="root-folder-item" 
                :class="{ 'selected': selectedFolderId === 'root' }"
                @click="handleSelectFolder('root')"
              >
                {{ rootText }}
              </div>
              <template v-if="treeVariant === 'legacy'">
                <FolderTreeNode
                  v-for="folder in rootFolders"
                  :key="folder.id"
                  :node="folder"
                  :selected-folder-id="selectedFolderId"
                  @select="handleSelectFolder"
                />
              </template>
              <template v-else>
                <FileTreeNode
                  v-for="folder in rootFolders"
                  :key="`modern-${folder.id}`"
                  :node="folder"
                  :level="0"
                  :select-folders="true"
                  :selected-node-id="selectedFolderId"
                  @navigate="handleModernTreeNavigate"
                  @select-folder="handleModernTreeSelectFolder"
                />
              </template>
            </div>
          </div>
        </div>
        <footer class="modal-footer">
          <button class="btn btn-secondary" @click="$emit('close')">{{ t('move.dialog.cancel') }}</button>
          <button class="btn btn-primary" @click="handleConfirm" :disabled="!selectedFolderId">{{ confirmButtonText }}</button>
        </footer>
      </div>
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
  z-index: 2000;
}

.modal-dialog {
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-xl);
  width: 100%;
  max-width: 480px;
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
  max-height: 60vh;
  overflow-y: auto;
}

.prompt {
  margin-bottom: var(--spacing-md);
  color: var(--color-text-secondary);
}

.share-options {
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background: var(--color-bg-primary);
  padding: 10px 12px;
  margin-bottom: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.share-label {
  color: var(--color-text-secondary);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.share-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-primary);
  cursor: pointer;
}

.folder-tree-container {
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  min-height: 250px;
  max-height: 400px;
  overflow-y: auto;
  padding: var(--spacing-sm);
  background-color: var(--color-bg-primary);
}

.root-folder-item {
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  border-radius: var(--border-radius-md);
  font-weight: var(--font-weight-medium);
}
.root-folder-item:hover {
  background-color: var(--color-bg-tertiary);
}
.root-folder-item.selected {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
}

.loading-indicator, .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: var(--color-text-tertiary);
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
.btn-primary:hover:not(:disabled) {
    background-color: var(--color-primary-hover);
}
.btn-secondary {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}
.btn-secondary:hover:not(:disabled) {
    background-color: var(--color-bg-tertiary);
    border-color: var(--color-border-hover);
}

.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
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
