<script setup lang="ts">
import { ref } from 'vue';
import type { PathItem } from '../../types/file';

defineProps<{
  path: PathItem[];
}>();

const emit = defineEmits(['navigate', 'drop-on-folder']);

const isBeingDraggedOver = ref<string | null>(null);

const onNavigate = (folderId: string | null) => {
  if (folderId) {
    emit('navigate', folderId);
  }
};

const handleDrop = (e: DragEvent, folderId: string | null) => {
  e.preventDefault();
  isBeingDraggedOver.value = null;
  if (!folderId) return;

  const sourceItemIdsJSON = e.dataTransfer?.getData('application/fileflash-item-ids');
  if (!sourceItemIdsJSON) return;
  
  const sourceItemIds = JSON.parse(sourceItemIdsJSON);

  // Prevent dropping into one of the dragged folders
  if (sourceItemIds.includes(folderId)) {
    console.warn("Cannot drop a folder into itself.");
    return;
  }
  
  emit('drop-on-folder', { sourceItemIds, targetFolderId: folderId });
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move';
  }
};

const handleDragEnter = (folderId: string | null) => {
  if (folderId) {
    isBeingDraggedOver.value = folderId;
  }
};

const handleDragLeave = () => {
  isBeingDraggedOver.value = null;
};
</script>

<template>
  <nav aria-label="Breadcrumb" class="breadcrumb">
    <ol>
      <li v-for="(item, index) in path" :key="item.folderId || 'root'">
        <button 
          v-if="index < path.length - 1"
          @click="onNavigate(item.folderId)" 
          class="breadcrumb-link"
          :class="{ 'drag-over': isBeingDraggedOver === item.folderId }"
          @drop="handleDrop($event, item.folderId)"
          @dragover="handleDragOver($event)"
          @dragenter="handleDragEnter(item.folderId)"
          @dragleave="handleDragLeave"
        >
          {{ item.name }}
        </button>
        <span v-else class="breadcrumb-current" aria-current="page">
          {{ item.name }}
        </span>
        <span v-if="index < path.length - 1" class="separator" aria-hidden="true">/</span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.breadcrumb {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
}

.breadcrumb ol {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  list-style: none;
  margin: 0;
  padding: 0;
}

.breadcrumb-link {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: inherit;
  padding: 0;
  transition: color var(--transition-base);
}

.breadcrumb-link:hover {
  color: var(--color-primary);
}

.breadcrumb-link.drag-over {
  background-color: var(--color-primary-light);
  color: var(--color-primary-dark);
  border-radius: var(--border-radius-sm);
  padding: 2px 4px;
}

.breadcrumb-current {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.separator {
  margin: 0 var(--spacing-sm);
  color: var(--color-text-tertiary);
}
</style> 
