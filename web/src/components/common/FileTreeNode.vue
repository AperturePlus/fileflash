<script setup lang="ts">
import { ref, computed } from 'vue';
import type { ContentItem } from '../../types/file';
import { getFolderContents } from '../../api/folder';
import { getIconForFile } from '../../utils/fileIcons';
import folderIcon from '../../assets/generic/folder.svg';

const props = defineProps<{
  node: ContentItem;
  level: number;
}>();

const emit = defineEmits(['drop-on-folder', 'navigate']);

const isExpanded = ref(false);
const isLoading = ref(false);
const children = ref<ContentItem[]>([]);
const isDragOver = ref(false);

const isFolder = computed(() => props.node.itemType === 'folder');

const toggleExpand = async () => {
  if (!isFolder.value) return;
  isExpanded.value = !isExpanded.value;
  if (isExpanded.value && children.value.length === 0) {
    isLoading.value = true;
    try {
      const response = await getFolderContents({ folderId: props.node.id });
      let actualItems = response.items;

      // 特殊处理 root 节点：如果当前是 root 节点且返回的 items 中只有一个名为 'root' 的文件夹，则获取该文件夹的内容
      if (props.node.id === 'root' && 
          actualItems.length === 1 && 
          actualItems[0].name === 'root' && 
          actualItems[0].itemType === 'folder') {
        const actualFolderId = actualItems[0].id.toString();
        const actualResponse = await getFolderContents({ folderId: actualFolderId });
        actualItems = actualResponse.items;
      }

      children.value = actualItems;
    } catch (error) {
      console.error('Failed to load folder children:', error);
    } finally {
      isLoading.value = false;
    }
  }
};

const handleDragStart = (e: DragEvent) => {
    if (e.dataTransfer) {
        e.dataTransfer.setData('application/fileflash-item-ids', JSON.stringify([props.node.id]));
        e.dataTransfer.effectAllowed = 'move';
    }
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  isDragOver.value = false;

  if (!isFolder.value) return;
  
  const sourceItemIdsJSON = e.dataTransfer?.getData('application/fileflash-item-ids');
  if (!sourceItemIdsJSON) return;
  const sourceItemIds = JSON.parse(sourceItemIdsJSON);

  if (sourceItemIds.includes(props.node.id)) return;
  
  emit('drop-on-folder', { 
    sourceItemIds, 
    targetFolderId: props.node.id,
    targetFolderName: props.node.name 
  });
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  if (e.dataTransfer && isFolder.value) {
    e.dataTransfer.dropEffect = 'move';
  } else if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'none';
  }
};

const handleClick = () => {
  if (isFolder.value) {
    toggleExpand();
  } else {
    emit('navigate', props.node.id)
  }
}
</script>

<template>
  <div class="tree-node">
    <div 
      class="node-content"
      :class="{ 'drag-over': isDragOver, 'folder': isFolder }"
      :style="{ 'padding-left': `${level * 20}px` }"
      @click.stop="handleClick"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @dragstart="handleDragStart"
      :draggable="true"
      @dragenter="isFolder && (isDragOver = true)"
      @dragleave="isDragOver = false"
    >
      <span v-if="isFolder" class="arrow" :class="{ expanded: isExpanded }">
        {{ isExpanded ? 'v' : '>' }}
      </span>
      <span v-else class="arrow-placeholder"></span>
      <img :src="isFolder ? folderIcon : getIconForFile(node.name)" alt="" class="icon" />
      <span class="name">{{ node.name }}</span>
    </div>
    <div v-if="isExpanded" class="node-children">
      <div v-if="isLoading" class="loading-text" :style="{ 'padding-left': `${(level + 1) * 20}px` }">Loading...</div>
      <FileTreeNode
        v-for="childNode in children"
        :key="childNode.id"
        :node="childNode"
        :level="level + 1"
        @drop-on-folder="(data) => emit('drop-on-folder', data)"
        @navigate="(fileId) => emit('navigate', fileId)"
      />
    </div>
  </div>
</template>

<style scoped>
.node-content {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: var(--border-radius-md);
  transition: background-color 0.2s;
  border: 1px solid transparent;
}
.icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}
.node-content:hover {
  background-color: var(--color-bg-tertiary);
}
.node-content.drag-over {
    background-color: var(--color-primary-light);
    border: 1px dashed var(--color-primary);
}
.arrow {
  width: 20px;
  text-align: center;
  margin-right: 4px;
}
/* .arrow.expanded {
  transform: rotate(90deg);
} */
.name {
  margin-left: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1; /* Allow name to shrink */
  min-width: 0; /* Important for flex shrink to work */
}
.node-children {
  /* margin-left: 20px; */ /* Padding is handled by level */
}
.loading-text {
    padding: 4px 8px;
    color: var(--color-text-secondary);
}
.arrow-placeholder {
  width: 20px;
  flex-shrink: 0;
}
.node-content.folder {
  cursor: pointer;
}
</style> 



