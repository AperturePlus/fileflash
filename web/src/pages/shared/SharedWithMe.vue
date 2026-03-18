<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { SharedItem } from '../../types/share';
// import { getSharedItems } from '../../api/share'; // 临时禁用
// import { copyFile } from '../../api/file'; // 临时禁用
// import { copyFolder } from '../../api/folder'; // 临时禁用
import { useFileSelection } from '../../composables/useFileSelection';

const sharedItems = ref<SharedItem[]>([]);
const isLoading = ref(false);

const { selectedItems, isSelected, toggleSelection, selectedCount, clearSelection } = useFileSelection();

onMounted(async () => {
  isLoading.value = true;
  try {
    // 临时禁用 - 后端share API尚未实现
    // const response = await getSharedItems({});
    // sharedItems.value = response.items;
    sharedItems.value = []; // 临时返回空数组
    console.log('SharedWithMe API temporarily disabled - backend not implemented');
  } catch (error) {
    console.error('Failed to fetch shared items:', error);
  } finally {
    isLoading.value = false;
  }
});

const handleBatchAdd = async () => {
  if (selectedCount.value === 0) return;

  const itemsToAdd = sharedItems.value.filter(item => selectedItems.value.has(item.id));
  
  // Using Promise.allSettled to attempt all copies even if some fail
  const results = await Promise.allSettled(
    itemsToAdd.map(item => handleAddItemToMyFiles(item, false)) // Pass a flag to prevent individual alerts
  );

  const successfulAdds = results.filter(r => r.status === 'fulfilled').length;
  alert(`${successfulAdds} item(s) added to your files successfully.`);
  
  clearSelection();
  // No need to refresh data from server as the shared list itself doesn't change
};

// Modified to handle batch calls without alerting each time
const handleAddItemToMyFiles = async (item: SharedItem, showAlert = true) => {
  try {
    if (item.itemType === 'file') {
      await copyFile(item.id, { targetFolderId: 'root', newName: `(Shared) ${item.name}` });
    } else {
      await copyFolder(item.id, { targetParentId: 'root', newName: `(Shared) ${item.name}` });
    }
    if (showAlert) {
      alert(`'${item.name}' has been added to your files.`);
    }
  } catch (error) {
    console.error('Failed to add item to my files:', error);
    if (showAlert) {
      alert('Failed to add item.');
    }
    // Re-throw the error for Promise.allSettled to catch it as a rejection
    throw error;
  }
};
</script>

<template>
  <div class="shared-with-me-page">
    <header class="page-header">
      <h1>Shared with Me</h1>
      <div v-if="selectedCount > 0" class="batch-actions">
        <span>{{ selectedCount }} selected</span>
        <button @click="handleBatchAdd" class="batch-action-btn">Add to My Files</button>
      </div>
    </header>
    <div v-if="isLoading" class="loading-indicator">Loading shared items...</div>
    <div v-else-if="sharedItems.length === 0" class="empty-state">
      <p>No items have been shared with you yet.</p>
    </div>
    <div v-else class="shared-list">
      <div class="list-header">
        <div class="list-cell select-all">
          <!-- Master checkbox could go here in the future -->
        </div>
        <div class="list-cell name">Name</div>
        <div class="list-cell shared-by">Shared By</div>
        <div class="list-cell permission">My Permission</div>
        <div class="list-cell size">Size</div>
        <div class="list-cell shared-at">Shared Date</div>
        <div class="list-cell actions"></div>
      </div>
      <div 
        v-for="item in sharedItems" 
        :key="item.id" 
        class="list-item"
        :class="{ selected: isSelected(item.id) }"
        @click="toggleSelection(item.id)"
      >
        <div class="list-cell select-cell">
          <input 
            type="checkbox" 
            :checked="isSelected(item.id)"
            @click.stop="toggleSelection(item.id)"
            class="item-checkbox"
          />
        </div>
        <div class="list-cell name-cell">
          <img v-if="item.itemType === 'folder'" src="../../assets/generic/folder.svg" alt="" class="item-icon-small" />
          <img v-else src="../../assets/generic/file.svg" alt="" class="item-icon-small" />
          <span class="item-name">{{ item.name }}</span>
        </div>
        <div class="list-cell shared-by-cell">{{ item.sharedBy }}</div>
        <div class="list-cell permission-cell">{{ item.permission }}</div>
        <div class="list-cell size-cell">{{ item.size ? (item.size / 1024).toFixed(1) + ' KB' : '--' }}</div>
        <div class="list-cell shared-at-cell">{{ new Date(item.sharedAt).toLocaleDateString() }}</div>
        <div class="list-cell actions-cell" @click.stop>
          <button @click="handleAddItemToMyFiles(item)" class="action-btn">
            Add to My Files
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shared-with-me-page {
  padding: var(--spacing-lg);
}
.page-header {
  margin-bottom: var(--spacing-lg);
}
.loading-indicator, .empty-state {
  text-align: center;
  margin-top: 4rem;
  color: var(--color-text-secondary);
}
.shared-list {
  display: flex;
  flex-direction: column;
}
.list-header, .list-item {
  display: grid;
  grid-template-columns: 40px 2fr 1fr 1fr 1fr 1fr 1fr;
  gap: var(--spacing-md);
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
}
.list-header {
  border-bottom: 1px solid var(--color-border);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}
.list-item {
  border-radius: var(--border-radius-md);
  cursor: pointer;
}
.list-item:hover {
  background-color: var(--color-bg-tertiary);
}
.list-item.selected {
  background-color: var(--color-primary-light);
}
.list-item .item-checkbox {
  opacity: 1; /* Always visible in this view */
}
.name-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}
.item-icon-small {
  width: 24px;
  height: 24px;
}
.actions-cell {
  text-align: right;
}
.action-btn {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
  border: none;
  border-radius: var(--border-radius-md);
  padding: var(--spacing-xs) var(--spacing-sm);
  cursor: pointer;
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
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
  cursor: pointer;
  transition: all var(--transition-base);
}
</style> 