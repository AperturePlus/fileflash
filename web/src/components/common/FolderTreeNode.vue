<script setup lang="ts">
import { ref } from 'vue';
import type { FolderItem } from '../../types/file';
import { getFolderContents } from '../../api/folder';

const props = defineProps<{
  node: FolderItem;
  selectedFolderId: string | null;
}>();

const emit = defineEmits(['select']);

const isExpanded = ref(false);
const children = ref<FolderItem[]>([]);
const isLoading = ref(false);

const toggleExpand = async () => {
  isExpanded.value = !isExpanded.value;
  if (isExpanded.value && children.value.length === 0) {
    isLoading.value = true;
    try {
      const response = await getFolderContents({ folderId: props.node.id });
      children.value = response.items.filter(item => item.itemType === 'folder') as FolderItem[];
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
      @click="$emit('select', node.id)"
    >
      <button class="expand-btn" @click.stop="toggleExpand">
        {{ isExpanded ? '▼' : '►' }}
      </button>
      <span class="node-name">{{ node.name }}</span>
    </div>
    <div v-if="isExpanded" class="node-children">
      <div v-if="isLoading" class="loading-text">Loading...</div>
      <FolderTreeNode
        v-for="child in children"
        :key="child.id"
        :node="child"
        :selected-folder-id="selectedFolderId"
        @select="(id) => $emit('select', id)"
      />
      <div v-if="!isLoading && children.length === 0 && isExpanded" class="no-subfolders-text">
        No subfolders
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
  padding: var(--spacing-xs) 0;
  cursor: pointer;
  border-radius: var(--border-radius-sm);
}
.node-content:hover {
  background-color: var(--color-bg-tertiary);
}
.node-content.selected {
  background-color: var(--color-primary-light);
  font-weight: var(--font-weight-bold);
}
.expand-btn {
  background: none;
  border: none;
  width: 20px;
  cursor: pointer;
  font-size: 0.8em;
  color: var(--color-text-secondary);
}
.node-children {
  border-left: 1px solid var(--color-border);
  margin-left: 10px;
}
.loading-text, .no-subfolders-text {
  padding: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-style: italic;
}
</style> 