<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useFileStore } from '../../store/file';
import type { FolderItem, ContentItem } from '../../types/file';
import { getFolderContents } from '../../api/folder';
import FileTreeNode from '../common/FileTreeNode.vue';
import { eventBus } from '../../utils/eventBus';
import { getStorageStats } from '../../api/user';
import type { StorageStats } from '../../types/user';

const props = defineProps<{
  collapsed: boolean;
}>();

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

const isLoading = ref(false); // Kept for potential future use
const treeKey = ref(0);
const storage = ref<StorageStats | null>(null);

const handleTreeDrop = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[], targetFolderId: string, targetFolderName: string }) => {
  eventBus.emit('move-items', {
    sourceItemIds,
    targetFolderId,
    targetFolderName
  });
};

const handleTreeNavigate = (itemId: string) => {
    const item = { id: itemId, itemType: 'file' }; // Simplified for now
    
    if (itemId === 'root' || findFolderInTree([rootNode.value], itemId)) {
        fileStore.navigateToFolder(itemId);
    } else {
        fileStore.selectedFile = item as ContentItem;
    }
}

// Helper to find folder name for confirmation dialog
function findFolderInTree(nodes: FolderItem[], id: string): FolderItem | null {
  for (const node of nodes) {
    if (node.id === id) return node;
  }
  return null;
}

const refreshTree = () => {
  treeKey.value++;
};

const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

onMounted(() => {
  eventBus.on('refresh-file-tree', refreshTree);
  getStorageStats().then(stats => storage.value = stats);
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
          <router-link to="/" class="nav-link" active-class="active">
            <span>🗂️</span>
            <span v-if="!collapsed" class="link-text">My Files</span>
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/shared" class="nav-link" active-class="active">
            <span>🤝</span>
            <span v-if="!collapsed" class="link-text">Shared with Me</span>
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/trash" class="nav-link" active-class="active">
            <span>🗑️</span>
            <span v-if="!collapsed" class="link-text">Trash</span>
          </router-link>
        </li>
      </ul>
    </nav>
    
    <hr v-if="!collapsed" class="divider">

    <div v-if="!collapsed" class="file-tree-container">
      <h4 class="tree-header">Workspace</h4>
       <div v-if="isLoading">Loading...</div>
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
       <div v-if="storage" class="storage-status">
        <span class="icon">💾</span>
        <div v-if="!collapsed" class="details">
          <p>Storage</p>
          <progress :value="storage.storageUsed" :max="storage.storageLimit"></progress>
          <span>{{ formatBytes(storage.storageUsed) }} / {{ formatBytes(storage.storageLimit) }} Used</span>
        </div>
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
  transition: width var(--transition-base), background-color var(--transition-base), border-color var(--transition-base);
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md);
}

.left-sidebar.collapsed {
  width: var(--sidebar-left-collapsed-width);
}

.sidebar-nav {
  /* styles for nav links */
}
.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.nav-item {
  margin-bottom: var(--spacing-xs);
}
.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm);
  border-radius: var(--border-radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-base);
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
.link-text {
  white-space: nowrap;
  opacity: 1;
  transition: opacity 0.3s;
}
.left-sidebar.collapsed .link-text {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.divider {
  border: none;
  border-top: 1px solid var(--color-divider);
  margin: var(--spacing-lg) 0;
}

.file-tree-container {
  flex-grow: 1;
  overflow-y: hidden; /* Hide vertical scroll on container */
  display: flex;
  flex-direction: column;
}

.sidebar-footer {
  margin-top: auto; /* Pushes footer to the bottom */
  padding-top: var(--spacing-md);
}

.tree-scroll-wrapper {
    flex-grow: 1;
    overflow: auto; /* Allow both vertical and horizontal scrolling */
    padding-bottom: var(--spacing-lg); /* Ensure space at the bottom */
}

.tree-header {
  margin-bottom: var(--spacing-md);
  font-size: 0.9rem;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.storage-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
}
.collapsed .storage-status {
    justify-content: center;
}
.icon {
  font-size: 1.5rem;
}
.details {
  width: 100%;
}
.details p {
  margin: 0 0 var(--spacing-xs);
  font-weight: var(--font-weight-medium);
  font-size: .875rem;
}
.details progress {
  width: 100%;
  height: 8px;
  border-radius: 4px;
}
.details span {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
</style>