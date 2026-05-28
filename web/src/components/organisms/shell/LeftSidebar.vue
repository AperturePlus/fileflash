<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { getStarredFiles } from '../../../api/file';
import { getFolderPath } from '../../../api/folder';
import { useFileStore } from '../../../store/file';
import { useUploadStore } from '../../../store/upload';
import type { ContentItem, FolderItem, PathItem } from '../../../types/file';
import { eventBus } from '../../../utils/eventBus';
import { useLocaleStore } from '../../../store/locale';
import FileTreeNode from '../../common/FileTreeNode.vue';
import Icon from '../../atoms/Icon.vue';
import Text from '../../atoms/Text.vue';
import StorageStatusWidget from './StorageStatusWidget.vue';

defineProps<{ collapsed: boolean }>();

const fileStore = useFileStore();
const uploadStore = useUploadStore();
const router = useRouter();
const localeStore = useLocaleStore();
const t = localeStore.t;
const { activeUploadingCount } = storeToRefs(uploadStore);
const folderPathCache = new Map<string, string>();

const rootNode = ref<FolderItem>({
  id: 'root', name: t('sidebar.myFiles'), itemType: 'folder', size: 0, ownerName: '',
  updatedAt: new Date().toISOString(), createdAt: new Date().toISOString(), parentFolderId: null,
});
const treeKey = ref(0);
const starredItems = ref<ContentItem[]>([]);
const starredPaths = ref<Record<string, string>>({});
const starredLoading = ref(false);

const navItems = computed(() => [
  { to: '/files', label: t('sidebar.myFiles'), icon: 'folder' as const },
  { to: '/shared', label: t('sidebar.shared'), icon: 'share' as const },
  { to: '/agent', label: t('sidebar.agent'), icon: 'more' as const },
  { to: '/trash', label: t('sidebar.recycleBin'), icon: 'trash' as const },
]);

function handleTreeDrop(payload: { sourceItemIds: string[]; targetFolderId: string; targetFolderName: string }) {
  eventBus.emit('move-items', payload);
}

function handleTreeNavigate(itemId: string) {
  const isFolder = itemId === 'root' || !!findFolderInTree([rootNode.value], itemId);
  if (isFolder) { fileStore.navigateToFolder(itemId); return; }
  fileStore.selectedFile = { id: itemId, itemType: 'file' } as ContentItem;
}
function findFolderInTree(nodes: FolderItem[], id: string): FolderItem | null {
  for (const node of nodes) { if (node.id === id) return node; }
  return null;
}
function refreshTree() { treeKey.value += 1; }

function toLocalizedPath(pathItems: PathItem[]): string {
  return pathItems
    .map((item, index) => {
      if (index === 0 || item.folderId === 'root' || item.folderId === null) {
        return t('sidebar.myFiles');
      }
      return item.name;
    })
    .join('/');
}

async function getFolderPathCached(folderId: string): Promise<string> {
  const cached = folderPathCache.get(folderId);
  if (cached) {
    return cached;
  }

  try {
    const path = await getFolderPath(folderId);
    const normalized = toLocalizedPath(path.pathItems);
    folderPathCache.set(folderId, normalized);
    return normalized;
  } catch {
    const fallback = t('sidebar.myFiles');
    folderPathCache.set(folderId, fallback);
    return fallback;
  }
}

async function refreshStarredTree() {
  starredLoading.value = true;
  try {
    const data = await getStarredFiles();
    const items = data.items || [];
    starredItems.value = items;

    const nextPaths: Record<string, string> = {};
    await Promise.all(
      items.map(async (item) => {
        const folderId = item.itemType === 'folder' ? item.id : item.folderId;
        nextPaths[item.id] = await getFolderPathCached(folderId);
      }),
    );
    starredPaths.value = nextPaths;
  } catch {
    starredItems.value = [];
    starredPaths.value = {};
  } finally {
    starredLoading.value = false;
  }
}

function refreshAllTrees() {
  refreshTree();
  void refreshStarredTree();
}

function getStarredPath(item: ContentItem): string {
  return starredPaths.value[item.id] || t('sidebar.myFiles');
}

function handleStarredClick(item: ContentItem) {
  if (item.itemType === 'folder') {
    void router.push('/files');
    fileStore.navigateToFolder(item.id);
    return;
  }
  fileStore.selectedFile = item;
  fileStore.previewFile = item;
}

watch(() => localeStore.locale, () => {
  rootNode.value = { ...rootNode.value, name: t('sidebar.myFiles') };
  folderPathCache.clear();
  void refreshStarredTree();
});

onMounted(() => {
  eventBus.on('refresh-file-tree', refreshAllTrees);
  void refreshStarredTree();
});
onUnmounted(() => { eventBus.off('refresh-file-tree', refreshAllTrees); });
</script>

<template>
  <aside :class="['left-sidebar', { collapsed }]">
    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.to" class="nav-item">
          <router-link :to="item.to" class="nav-link" active-class="active">
            <Icon :name="item.icon" :size="16" />
            <span
              v-if="item.to === '/files' && activeUploadingCount > 0"
              class="upload-indicator"
              :aria-label="t('sidebar.myFiles.uploadingAria')"
              role="status"
            />
            <span v-if="!collapsed" class="link-text">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div v-if="!collapsed" class="tree-panel">
      <section class="tree-section">
        <Text variant="label">{{ t('sidebar.starred') }}</Text>
        <div class="starred-list">
          <button
            v-for="item in starredItems"
            :key="item.id"
            class="starred-row"
            @click="handleStarredClick(item)"
          >
            <Icon :name="item.itemType === 'folder' ? 'folder' : 'file'" :size="16" />
            <span class="starred-meta">
              <span class="starred-name">{{ item.name }}</span>
              <span class="starred-path">{{ getStarredPath(item) }}</span>
            </span>
          </button>
          <div v-if="starredLoading" class="starred-state">Loading...</div>
          <div v-else-if="starredItems.length === 0" class="starred-state">
            {{ t('sidebar.starredEmpty') }}
          </div>
        </div>
      </section>

      <section class="tree-section">
        <Text variant="label">{{ t('sidebar.workspaceTree') }}</Text>
        <div class="tree-scroll">
          <FileTreeNode :key="treeKey" :node="rootNode" :level="0" @drop-on-folder="handleTreeDrop" @navigate="handleTreeNavigate" />
        </div>
      </section>
    </div>

    <StorageStatusWidget :collapsed="collapsed" />
  </aside>
</template>

<style scoped>
.left-sidebar {
  width: var(--sidebar-left-width);
  background: var(--surface-raised);
  border-right: 1px solid var(--border-default);
  flex-shrink: 0; display: flex; flex-direction: column; gap: var(--sp-md);
  padding: var(--sp-md);
  transition: width var(--mo-duration-mid) var(--mo-easing);
}
.left-sidebar.collapsed { width: var(--sidebar-left-collapsed-width); }
.nav-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.nav-link {
  height: var(--row-h); display: flex; align-items: center; gap: 10px;
  padding: 0 10px; border-radius: var(--radius-sm);
  color: var(--text-secondary); text-decoration: none;
  transition: color var(--mo-duration-fast) var(--mo-easing), background-color var(--mo-duration-fast) var(--mo-easing);
}
.nav-link:hover { background: var(--surface-inset); color: var(--text-primary); }
.nav-link.active { background: rgba(var(--ac-rgb), 0.12); color: var(--ac); font-weight: var(--weight-medium); }
.left-sidebar.collapsed .nav-link { justify-content: center; padding: 0; }
.link-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.upload-indicator {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--ac);
  box-shadow: 0 0 0 rgba(var(--ac-rgb), 0.4);
  animation: upload-pulse 1.2s ease-in-out infinite;
}
.tree-panel {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--sp-md);
  gap: var(--sp-md);
}
.tree-section {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
}
.tree-scroll { flex: 1; overflow: auto; padding-right: 4px; }
.starred-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 180px;
  overflow: auto;
  padding-right: 4px;
}
.starred-row {
  height: var(--row-h);
  width: 100%;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  cursor: pointer;
  text-align: left;
}
.starred-row > :first-child {
  flex-shrink: 0;
}
.starred-row:hover {
  background: var(--surface-inset);
  color: var(--text-primary);
}
.starred-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.starred-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
  font-size: 12.5px;
}
.starred-path {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-dim);
  font-size: 11px;
}
.starred-state {
  height: var(--row-h);
  display: flex;
  align-items: center;
  color: var(--text-dim);
  font-size: 11px;
  padding: 0 10px;
}

@keyframes upload-pulse {
  0% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(var(--ac-rgb), 0.5); }
  60% { transform: scale(1); box-shadow: 0 0 0 6px rgba(var(--ac-rgb), 0); }
  100% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(var(--ac-rgb), 0); }
}
[data-motion="reduced"] .upload-indicator {
  animation: none;
}
</style>
