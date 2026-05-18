<script setup lang="ts">
import { ref } from 'vue';
import type { FolderItem } from '../../../types/file';
import { getFolderContents } from '../../../api/folder';
import { useLocaleStore } from '../../../store/locale';

const props = defineProps<{
  node: FolderItem;
  selectedFolderId: string | null;
}>();

const emit = defineEmits(['select']);
const localeStore = useLocaleStore();
const t = localeStore.t;

const isExpanded = ref(false);
const children = ref<FolderItem[]>([]);
const isLoading = ref(false);

const toggleExpand = async () => {
  isExpanded.value = !isExpanded.value;
  if (isExpanded.value && children.value.length === 0) {
    isLoading.value = true;
    try {
      const response = await getFolderContents({ folderId: props.node.id });
      children.value = response.items.filter((item) => item.itemType === 'folder') as FolderItem[];
    } catch (error) {
      console.error('Failed to load subfolders:', error);
    } finally {
      isLoading.value = false;
    }
  }
};
</script>

<template>
  <div class="tree-node">
    <div
      class="node-content"
      :class="{ selected: selectedFolderId === node.id }"
      @click="emit('select', node.id)"
    >
      <button class="expand-btn" @click.stop="toggleExpand">
        {{ isExpanded ? '▼' : '►' }}
      </button>
      <span class="node-name">{{ node.name }}</span>
    </div>
    <div v-if="isExpanded" class="node-children">
      <div v-if="isLoading" class="loading-text">{{ t('files.folder.loading') }}</div>
      <FolderTreeNode
        v-for="child in children"
        :key="child.id"
        :node="child"
        :selected-folder-id="selectedFolderId"
        @select="(id) => emit('select', id)"
      />
      <div v-if="!isLoading && children.length === 0 && isExpanded" class="no-subfolders-text">
        {{ t('files.folder.noSubfolders') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.tree-node {
  padding-left: 20px;
}
.node-content {
  display: flex;
  align-items: center;
  padding: var(--sp-xs) 0;
  cursor: pointer;
}
.node-content:hover {
  background: var(--surface-inset);
}
.node-content.selected {
  background: rgb(var(--ac-rgb) / 0.12);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}
.expand-btn {
  background: none;
  border: none;
  width: 20px;
  cursor: pointer;
  font-size: 0.8em;
  color: var(--text-secondary);
}
.node-name {
  color: var(--text-primary);
  font-size: 13px;
}
.node-children {
  border-left: 1px solid var(--border-default);
  margin-left: 10px;
}
.loading-text,
.no-subfolders-text {
  padding: var(--sp-sm);
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
}
</style>
