<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getRecycleBin, restoreItem, permanentDelete } from '../../api/recycle';
import type { RecycleBinItem } from '../../types/file';
import { getIconForFile } from '../../utils/fileIcons';
import { eventBus } from '../../utils/eventBus';

const items = ref<RecycleBinItem[]>([]);
const isLoading = ref(false);

const fetchItems = async () => {
  isLoading.value = true;
  try {
    const response = await getRecycleBin({});
    items.value = response.items;
  } catch (error) {
    console.error('Failed to fetch recycle bin items:', error);
    alert('Could not load trash items.');
  } finally {
    isLoading.value = false;
  }
};

const handleRestore = async (item: RecycleBinItem) => {
  if (!confirm(`Are you sure you want to restore "${item.name}"?`)) return;
  try {
    await restoreItem(item.id, { itemType: item.itemType });
    items.value = items.value.filter(i => i.id !== item.id);
    eventBus.emit('refresh-file-tree');
    alert('Item restored successfully.');
  } catch (error) {
    console.error('Failed to restore item:', error);
    alert('Could not restore item.');
  }
};

const handlePermanentDelete = async (item: RecycleBinItem) => {
  if (!confirm(`This action is permanent. Are you sure you want to permanently delete "${item.name}"?`)) return;
  try {
    await permanentDelete(item.id, item.itemType);
    items.value = items.value.filter(i => i.id !== item.id);
    alert('Item permanently deleted.');
  } catch (error) {
    console.error('Failed to permanently delete item:', error);
    alert('Could not permanently delete item.');
  }
};

onMounted(() => {
  fetchItems();
});
</script>

<template>
  <div class="trash-page">
    <header class="page-header">
      <h1>Recycle Bin</h1>
      <p>Items in the recycle bin will be permanently deleted after 30 days.</p>
    </header>
    
    <div class="trash-list-container">
      <div v-if="isLoading" class="loading-indicator">Loading...</div>
      
      <div v-else-if="items.length === 0" class="empty-trash">
        <div class="empty-trash-icon">🗑️</div>
        <p>Your recycle bin is empty.</p>
      </div>

      <div v-else class="trash-list">
        <!-- List Header -->
        <div class="list-header">
          <div class="list-cell name">Name</div>
          <div class="list-cell path">Original Location</div>
          <div class="list-cell deleted-at">Date Deleted</div>
          <div class="list-cell expires-in">Expires In</div>
          <div class="list-cell actions"></div>
        </div>
        <!-- List Body -->
        <div v-for="item in items" :key="item.id" class="list-item">
          <div class="list-cell name-cell">
            <img :src="getIconForFile(item.name)" alt="" class="item-icon-small" />
            <span class="item-name">{{ item.name }}</span>
          </div>
          <div class="list-cell path-cell">{{ item.originalPath }}</div>
          <div class="list-cell deleted-at-cell">{{ new Date(item.deletedAt).toLocaleDateString() }}</div>
          <div class="list-cell expires-in-cell">{{ item.daysUntilPermanentDelete }} days</div>
          <div class="list-cell actions-cell">
            <button @click="handleRestore(item)" class="action-btn restore-btn" title="Restore">
              <span>♻️</span>
            </button>
            <button @click="handlePermanentDelete(item)" class="action-btn delete-btn" title="Delete Permanently">
              <span>❌</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trash-page {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.page-header {
  margin-bottom: var(--spacing-lg);
}
.page-header h1 {
    font-size: 1.8rem;
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
}
.page-header p {
    color: var(--color-text-secondary);
    font-size: var(--font-size-base);
}

.trash-list-container {
  flex-grow: 1;
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-md);
  overflow-y: auto;
}

.empty-trash {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-text-secondary);
}
.empty-trash-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
}

.trash-list {
  display: flex;
  flex-direction: column;
}

.list-header, .list-item {
  display: grid;
  grid-template-columns: 2fr 2fr 1fr 1fr 100px;
  gap: var(--spacing-md);
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.list-header {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.list-item:hover {
  background-color: var(--color-bg-tertiary);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-medium);
}
.item-icon-small {
  width: 24px;
  height: 24px;
}
.path-cell {
    color: var(--color-text-secondary);
}
.deleted-at-cell {
    color: var(--color-text-secondary);
}
.expires-in-cell {
    color: var(--color-danger);
}

.actions-cell {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}
.action-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--border-radius-sm);
  padding: var(--spacing-xs);
  cursor: pointer;
  transition: all var(--transition-base);
}
.action-btn:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-border-hover);
}
</style> 