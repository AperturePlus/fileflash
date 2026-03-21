<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useFileStore } from '../../store/file';
import type { ContentItem, FolderItem } from '../../types/file';
import FileTreeNode from '../common/FileTreeNode.vue';
import { eventBus } from '../../utils/eventBus';
import { getStorageStats } from '../../api/user';
import type { StorageStats } from '../../types/user';

defineProps<{ collapsed: boolean }>();

const fileStore = useFileStore();

const rootNode = ref<FolderItem>({
  id: 'root',
  name: 'My Files',
  itemType: 'folder',
  size: 0,
  ownerName: '',
  updatedAt: new Date().toISOString(),
  createdAt: new Date().toISOString(),
  parentFolderId: null,
});

const treeKey = ref(0);
const storage = ref<StorageStats | null>(null);

const storagePercentage = computed(() => {
  if (!storage.value || storage.value.storageLimit === 0) return 0;
  return Math.min(100, Math.round((storage.value.storageUsed / storage.value.storageLimit) * 100));
});

const formatBytes = (bytes: number, decimals = 1) => {
  if (bytes === 0) return '0 B';
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

const handleTreeDrop = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[]; targetFolderId: string; targetFolderName: string }) => {
  eventBus.emit('move-items', {
    sourceItemIds,
    targetFolderId,
    targetFolderName,
  });
};

const handleTreeNavigate = (itemId: string) => {
  const isFolder = itemId === 'root' || !!findFolderInTree([rootNode.value], itemId);
  if (isFolder) {
    fileStore.navigateToFolder(itemId);
    return;
  }

  fileStore.selectedFile = { id: itemId, itemType: 'file' } as ContentItem;
};

function findFolderInTree(nodes: FolderItem[], id: string): FolderItem | null {
  for (const node of nodes) {
    if (node.id === id) return node;
  }
  return null;
}

const refreshTree = () => {
  treeKey.value += 1;
};

onMounted(() => {
  eventBus.on('refresh-file-tree', refreshTree);
  getStorageStats().then((stats) => {
    storage.value = stats;
  });
});

onUnmounted(() => {
  eventBus.off('refresh-file-tree', refreshTree);
});
</script>

<template>
  <aside :class="['left-sidebar', { collapsed }]">
    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li class="nav-item">
          <router-link to="/files" class="nav-link" active-class="active">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
            <span v-if="!collapsed" class="link-text">My Files</span>
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/shared" class="nav-link" active-class="active">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 7a3 3 0 1 0-2.8-4H14a3 3 0 0 0 .2 1l-5.7 3a3 3 0 1 0 0 2l5.7 3a3 3 0 1 0 .7-1.3l-5.7-3a3 3 0 0 0 0-1.4z" /></svg>
            <span v-if="!collapsed" class="link-text">Shared</span>
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/trash" class="nav-link" active-class="active">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3h6l1 2h4v2H4V5h4zm1 6h2v8h-2zm4 0h2v8h-2zM6 7h12l-1 13a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2z" /></svg>
            <span v-if="!collapsed" class="link-text">Recycle Bin</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div v-if="!collapsed" class="tree-panel">
      <div class="panel-title">Workspace Tree</div>
      <div class="tree-scroll-wrapper">
        <FileTreeNode
          :key="treeKey"
          :node="rootNode"
          :level="0"
          @drop-on-folder="handleTreeDrop"
          @navigate="handleTreeNavigate"
        />
      </div>
    </div>

    <div class="sidebar-footer">
      <div v-if="storage" class="storage-card">
        <div class="storage-head">
          <strong v-if="!collapsed">Storage</strong>
          <span>{{ storagePercentage }}%</span>
        </div>
        <div class="progress-track" :aria-valuenow="storagePercentage" aria-valuemin="0" aria-valuemax="100" role="progressbar">
          <div class="progress-fill" :style="{ width: `${storagePercentage}%` }" />
        </div>
        <p v-if="!collapsed" class="storage-meta">
          {{ formatBytes(storage.storageUsed) }} / {{ formatBytes(storage.storageLimit) }}
        </p>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.left-sidebar {
  width: var(--sidebar-left-width);
  background-color: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  transition: width 0.2s ease;
}

.left-sidebar.collapsed {
  width: var(--sidebar-left-collapsed-width);
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-link {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border-radius: var(--border-radius-md);
  color: var(--color-text-secondary);
  transition: var(--transition-base);
}

.nav-link svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  flex-shrink: 0;
}

.nav-link:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.nav-link.active {
  background-color: var(--color-primary-light);
  color: var(--color-primary-dark);
  font-weight: var(--font-weight-semibold);
}

.left-sidebar.collapsed .nav-link {
  justify-content: center;
  padding: 0;
}

.link-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-panel {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--color-divider);
  padding-top: var(--spacing-md);
}

.panel-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-sm);
}

.tree-scroll-wrapper {
  flex: 1;
  overflow: auto;
  padding-right: 4px;
}

.sidebar-footer {
  margin-top: auto;
}

.storage-card {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: 10px;
}

.storage-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.storage-head span {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.progress-track {
  height: 8px;
  border-radius: 999px;
  background-color: var(--color-bg-quaternary);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-primary), #4ea8ff);
}

.storage-meta {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.left-sidebar.collapsed .storage-card {
  padding: 8px;
}

.left-sidebar.collapsed .storage-head strong,
.left-sidebar.collapsed .storage-meta {
  display: none;
}
</style>
