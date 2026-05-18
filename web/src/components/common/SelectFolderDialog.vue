<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { getFolderContents } from '../../api/folder';
import { useLocaleStore } from '../../store/locale';
import type { FolderItem } from '../../types/file';
import FolderTreeNode from './FolderTreeNode.vue';
import { ui } from '../../utils/ui';

interface Props {
  isVisible: boolean;
  title?: string;
  confirmText?: string;
}

const props = defineProps<Props>();
const emit = defineEmits(['close', 'confirm']);
const localeStore = useLocaleStore();
const t = localeStore.t;

const rootFolders = ref<FolderItem[]>([]);
const isLoading = ref(false);
const selectedFolderId = ref<string | null>(null);

const fetchRootFolders = async () => {
  if (rootFolders.value.length > 0) return;
  isLoading.value = true;
  try {
    const response = await getFolderContents({ folderId: 'root' });
    let actualItems = response.items;

    if (actualItems.length === 1 && actualItems[0].name === 'root' && actualItems[0].itemType === 'folder') {
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

onMounted(fetchRootFolders);

watch(() => props.isVisible, (visible) => {
  if (visible) {
    selectedFolderId.value = null;
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
  emit('confirm', selectedFolderId.value);
};
</script>

<template>
  <transition name="modal-fade">
    <div v-if="isVisible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog">
        <header class="modal-header">
          <h3 class="modal-title">{{ title || t('move.dialog.title.default') }}</h3>
          <button class="modal-close" @click="$emit('close')">&times;</button>
        </header>
        <div class="modal-body">
          <p class="prompt">{{ t('move.dialog.prompt') }}</p>
          <div class="folder-tree-container">
            <div v-if="isLoading" class="loading-indicator">{{ t('move.dialog.loading') }}</div>
            <div v-else-if="rootFolders.length === 0" class="empty-state">{{ t('move.dialog.empty') }}</div>
            <div v-else>
              <div
                class="root-folder-item"
                :class="{ 'selected': selectedFolderId === 'root' }"
                @click="handleSelectFolder('root')"
              >
                {{ t('move.dialog.root') }}
              </div>
              <FolderTreeNode
                v-for="folder in rootFolders"
                :key="folder.id"
                :node="folder"
                :selected-folder-id="selectedFolderId"
                @select="handleSelectFolder"
              />
            </div>
          </div>
        </div>
        <footer class="modal-footer">
          <button class="btn btn-secondary" @click="$emit('close')">{{ t('move.dialog.cancel') }}</button>
          <button class="btn btn-primary" @click="handleConfirm" :disabled="!selectedFolderId">
            {{ confirmText || t('move.dialog.confirm') }}
          </button>
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

.loading-indicator,
.empty-state {
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

