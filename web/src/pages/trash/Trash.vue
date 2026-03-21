<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { clearRecycleBin, getRecycleBin, permanentDelete, restoreItem } from '../../api/recycle';
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
    console.error('Failed to load recycle bin items', error);
  } finally {
    isLoading.value = false;
  }
};

const handleRestore = async (item: RecycleBinItem) => {
  const confirmed = window.confirm(`Restore \"${item.name}\"?`);
  if (!confirmed) return;

  try {
    await restoreItem(item.id, { itemType: item.itemType });
    items.value = items.value.filter((entry) => entry.id !== item.id);
    eventBus.emit('refresh-file-tree');
  } catch (error) {
    console.error('Restore failed', error);
  }
};

const handlePermanentDelete = async (item: RecycleBinItem) => {
  const confirmed = window.confirm(`Permanently delete \"${item.name}\"? This cannot be undone.`);
  if (!confirmed) return;

  try {
    await permanentDelete(item.id, item.itemType);
    items.value = items.value.filter((entry) => entry.id !== item.id);
  } catch (error) {
    console.error('Permanent delete failed', error);
  }
};

const handleClearAll = async () => {
  if (!items.value.length) return;
  const confirmed = window.confirm('Clear entire recycle bin? This cannot be undone.');
  if (!confirmed) return;

  try {
    await clearRecycleBin();
    items.value = [];
  } catch (error) {
    console.error('Clear recycle bin failed', error);
  }
};

onMounted(fetchItems);
</script>

<template>
  <section class="trash-page">
    <header class="page-header">
      <div>
        <h1>Recycle Bin</h1>
        <p>Items are kept for up to 30 days before automatic cleanup.</p>
      </div>
      <button class="clear-btn" :disabled="!items.length" @click="handleClearAll">Clear Bin</button>
    </header>

    <div class="trash-card">
      <div v-if="isLoading" class="state">Loading...</div>

      <div v-else-if="items.length === 0" class="state">Recycle bin is empty.</div>

      <div v-else class="trash-list">
        <div class="list-header">
          <div class="col name">Name</div>
          <div class="col path">Original location</div>
          <div class="col deleted">Deleted at</div>
          <div class="col expire">Expires in</div>
          <div class="col action" />
        </div>

        <div v-for="item in items" :key="item.id" class="list-row">
          <div class="col name name-cell">
            <img :src="getIconForFile(item.name)" alt="" class="icon" />
            <span>{{ item.name }}</span>
          </div>
          <div class="col path">{{ item.originalPath }}</div>
          <div class="col deleted">{{ new Date(item.deletedAt).toLocaleString() }}</div>
          <div class="col expire">{{ item.daysUntilPermanentDelete }} days</div>
          <div class="col action action-cell">
            <button class="secondary-btn" @click="handleRestore(item)">Restore</button>
            <button class="danger-btn" @click="handlePermanentDelete(item)">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trash-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  height: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.page-header p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
}

.clear-btn,
.secondary-btn,
.danger-btn {
  height: 32px;
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0 12px;
  cursor: pointer;
}

.clear-btn,
.secondary-btn {
  background-color: var(--color-bg-primary);
  border-color: var(--color-border);
}

.danger-btn {
  background-color: var(--color-danger-light);
  color: var(--color-danger-dark);
  border-color: #fca5a5;
}

.trash-card {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-md);
  overflow: auto;
}

.state {
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.trash-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-header,
.list-row {
  display: grid;
  grid-template-columns: 1.4fr 1.3fr 1fr 0.7fr 220px;
  gap: var(--spacing-sm);
  align-items: center;
}

.list-header {
  color: var(--color-text-tertiary);
  font-size: 12px;
  padding: 0 8px;
}

.list-row {
  min-height: 48px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 4px 8px;
}

.list-row:hover {
  background-color: var(--color-bg-tertiary);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.name-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon {
  width: 22px;
  height: 22px;
}

.action-cell {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 980px) {
  .list-header,
  .list-row {
    grid-template-columns: 1.3fr 1fr 0.8fr 0;
  }

  .col.action {
    display: none;
  }

  .action-cell {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}
</style>
