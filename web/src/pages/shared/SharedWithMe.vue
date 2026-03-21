<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { acceptSharedItem, deleteShare, getSharedItems, getShares } from '../../api/share';
import { useFileSelection } from '../../composables/useFileSelection';
import type { Share, SharedItem } from '../../types/share';

const activeTab = ref<'received' | 'links'>('received');
const isLoading = ref(false);
const sharedItems = ref<SharedItem[]>([]);
const myShares = ref<Share[]>([]);

const { selectedItems, isSelected, toggleSelection, selectedCount, clearSelection } = useFileSelection();

const hasSelection = computed(() => selectedCount.value > 0 && activeTab.value === 'received');

const loadReceived = async () => {
  const response = await getSharedItems({ page: 1, perPage: 50, sort: 'sharedAt', order: 'desc' });
  sharedItems.value = response.items;
};

const loadLinks = async () => {
  const response = await getShares({ page: 1, perPage: 50 });
  myShares.value = response.items;
};

const loadData = async () => {
  isLoading.value = true;
  try {
    if (activeTab.value === 'received') {
      await loadReceived();
    } else {
      await loadLinks();
    }
  } finally {
    isLoading.value = false;
  }
};

const switchTab = async (tab: 'received' | 'links') => {
  activeTab.value = tab;
  clearSelection();
  await loadData();
};

const acceptOne = async (item: SharedItem) => {
  await acceptSharedItem(item.id);
};

const handleAcceptOne = async (item: SharedItem) => {
  try {
    await acceptOne(item);
    await loadReceived();
  } catch (error) {
    console.error('Failed to accept shared item', error);
  }
};

const handleBatchAccept = async () => {
  if (!selectedItems.value.size) return;

  const ids = Array.from(selectedItems.value);
  await Promise.allSettled(ids.map((id) => acceptSharedItem(id)));
  clearSelection();
  await loadReceived();
};

const handleDeleteShare = async (share: Share) => {
  const confirmed = window.confirm(`Delete share link ${share.shareLink}?`);
  if (!confirmed) return;

  try {
    await deleteShare(share.shareLink);
    myShares.value = myShares.value.filter((entry) => entry.shareLink !== share.shareLink);
  } catch (error) {
    console.error('Failed to delete share link', error);
  }
};

const copyShareLink = async (share: Share) => {
  try {
    await navigator.clipboard.writeText(`${window.location.origin}/share/${share.shareLink}`);
  } catch {
    window.prompt('Copy this link', `${window.location.origin}/share/${share.shareLink}`);
  }
};

onMounted(loadData);
</script>

<template>
  <section class="shared-page">
    <header class="page-header">
      <div>
        <h1>Sharing Center</h1>
        <p>Manage received files and the links you shared with others.</p>
      </div>

      <div class="tabs" role="tablist">
        <button :class="{ active: activeTab === 'received' }" @click="switchTab('received')">Shared with Me</button>
        <button :class="{ active: activeTab === 'links' }" @click="switchTab('links')">My Share Links</button>
      </div>
    </header>

    <div class="shared-card">
      <div v-if="hasSelection" class="batch-bar">
        <span>{{ selectedCount }} selected</span>
        <button class="primary-btn" @click="handleBatchAccept">Accept Selected</button>
      </div>

      <div v-if="isLoading" class="state">Loading...</div>

      <template v-else-if="activeTab === 'received'">
        <div v-if="!sharedItems.length" class="state">No files shared with you.</div>

        <div v-else class="list">
          <div class="list-header">
            <div class="col checkbox" />
            <div class="col name">Name</div>
            <div class="col owner">Shared by</div>
            <div class="col permission">Permission</div>
            <div class="col date">Shared at</div>
            <div class="col action" />
          </div>

          <div
            v-for="item in sharedItems"
            :key="item.id"
            class="list-row"
            :class="{ selected: isSelected(item.id) }"
            @click="toggleSelection(item.id)"
          >
            <div class="col checkbox" @click.stop>
              <input type="checkbox" :checked="isSelected(item.id)" @change.stop="toggleSelection(item.id)" />
            </div>
            <div class="col name">
              <strong>{{ item.name }}</strong>
              <small>{{ item.itemType }}</small>
            </div>
            <div class="col owner">{{ item.sharedBy }}</div>
            <div class="col permission">{{ item.permission }}</div>
            <div class="col date">{{ new Date(item.sharedAt).toLocaleString() }}</div>
            <div class="col action" @click.stop>
              <button class="primary-btn" @click="handleAcceptOne(item)">Accept</button>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div v-if="!myShares.length" class="state">No share links created yet.</div>

        <div v-else class="list">
          <div class="list-header links">
            <div class="col name">Resource</div>
            <div class="col link">Share link</div>
            <div class="col stats">Views / Downloads</div>
            <div class="col date">Created at</div>
            <div class="col action" />
          </div>

          <div v-for="share in myShares" :key="share.shareId" class="list-row links">
            <div class="col name">
              <strong>{{ share.itemInfo.name }}</strong>
              <small>{{ share.itemType }}</small>
            </div>
            <div class="col link"><code>{{ share.shareLink }}</code></div>
            <div class="col stats">{{ share.visitCount || 0 }} / {{ share.downloadCount || 0 }}</div>
            <div class="col date">{{ new Date(share.createdAt).toLocaleString() }}</div>
            <div class="col action action-buttons">
              <button class="secondary-btn" @click="copyShareLink(share)">Copy</button>
              <button class="danger-btn" @click="handleDeleteShare(share)">Delete</button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.shared-page {
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

.tabs {
  display: inline-flex;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-tertiary);
  border-radius: 10px;
  padding: 2px;
}

.tabs button {
  min-width: 130px;
  height: 34px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
}

.tabs button.active {
  background-color: var(--color-bg-primary);
  box-shadow: var(--shadow-sm);
}

.shared-card {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-md);
  overflow: auto;
}

.batch-bar {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: var(--spacing-sm);
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-tertiary);
}

.state {
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-header,
.list-row {
  display: grid;
  grid-template-columns: 46px 1.6fr 1fr 0.8fr 1.2fr 140px;
  align-items: center;
  gap: var(--spacing-sm);
}

.list-header {
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding: 0 8px;
}

.list-row {
  min-height: 50px;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid transparent;
}

.list-row:hover {
  background-color: var(--color-bg-tertiary);
}

.list-row.selected {
  background-color: var(--color-primary-light);
  border-color: rgba(var(--color-primary-rgb), 0.3);
}

.col.name {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.col.name strong,
.col.name small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col.name small {
  color: var(--color-text-tertiary);
}

.list-header.links,
.list-row.links {
  grid-template-columns: 1.4fr 0.9fr 0.8fr 1fr 170px;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.primary-btn,
.secondary-btn,
.danger-btn {
  height: 30px;
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0 10px;
  cursor: pointer;
}

.primary-btn {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
}

.secondary-btn {
  background-color: var(--color-bg-primary);
  border-color: var(--color-border);
}

.danger-btn {
  background-color: var(--color-danger-light);
  border-color: #fca5a5;
  color: var(--color-danger-dark);
}

code {
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  padding: 2px 6px;
  border-radius: 6px;
}

@media (max-width: 960px) {
  .list-header,
  .list-row,
  .list-header.links,
  .list-row.links {
    grid-template-columns: 40px 1fr 0;
  }

  .col.owner,
  .col.permission,
  .col.date,
  .col.stats,
  .col.link,
  .col.action {
    display: none;
  }

  .col.action.action-buttons {
    display: flex;
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}
</style>
