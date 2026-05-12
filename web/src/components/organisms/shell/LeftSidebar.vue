<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useFileStore } from '../../../store/file';
import type { ContentItem, FolderItem } from '../../../types/file';
import { eventBus } from '../../../utils/eventBus';
import { useLocaleStore } from '../../../store/locale';
import FileTreeNode from '../../common/FileTreeNode.vue';
import Icon from '../../atoms/Icon.vue';
import Text from '../../atoms/Text.vue';
import StorageStatusWidget from './StorageStatusWidget.vue';

defineProps<{ collapsed: boolean }>();

const fileStore = useFileStore();
const localeStore = useLocaleStore();
const t = localeStore.t;

const rootNode = ref<FolderItem>({
  id: 'root', name: t('sidebar.myFiles'), itemType: 'folder', size: 0, ownerName: '',
  updatedAt: new Date().toISOString(), createdAt: new Date().toISOString(), parentFolderId: null,
});
const treeKey = ref(0);

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

watch(() => localeStore.locale, () => {
  rootNode.value = { ...rootNode.value, name: t('sidebar.myFiles') };
});

onMounted(() => { eventBus.on('refresh-file-tree', refreshTree); });
onUnmounted(() => { eventBus.off('refresh-file-tree', refreshTree); });
</script>

<template>
  <aside :class="['left-sidebar', { collapsed }]">
    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.to" class="nav-item">
          <router-link :to="item.to" class="nav-link" active-class="active">
            <Icon :name="item.icon" :size="16" />
            <span v-if="!collapsed" class="link-text">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div v-if="!collapsed" class="tree-panel">
      <Text variant="label">Workspace</Text>
      <div class="tree-scroll">
        <FileTreeNode :key="treeKey" :node="rootNode" :level="0" @drop-on-folder="handleTreeDrop" @navigate="handleTreeNavigate" />
      </div>
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
.tree-panel { min-height: 0; flex: 1; display: flex; flex-direction: column; border-top: 1px solid var(--border-subtle); padding-top: var(--sp-md); gap: var(--sp-sm); }
.tree-scroll { flex: 1; overflow: auto; padding-right: 4px; }
</style>
