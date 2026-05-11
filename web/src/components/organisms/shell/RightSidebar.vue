<script setup lang="ts">
import { computed } from 'vue';
import { useFileStore } from '../../../store/file';
import FileDetailPanel from '../files/FileDetailPanel.vue';

defineProps<{ visible: boolean }>();

const fileStore = useFileStore();

const fileForPreview = computed(() => {
  if (!fileStore.selectedFile || fileStore.selectedFile.itemType !== 'file') return null;
  return fileStore.selectedFile;
});

const closeSidebar = () => {
  fileStore.selectedFile = null;
};
</script>

<template>
  <aside :class="['right-sidebar', { visible }]">
    <FileDetailPanel :file="fileForPreview" @close="closeSidebar" />
  </aside>
</template>

<style scoped>
.right-sidebar {
  width: var(--sidebar-right-width);
  margin-right: calc(-1 * var(--sidebar-right-width));
  border-left: 1px solid var(--border-default);
  background: var(--surface-raised);
  display: flex;
  flex-direction: column;
  transition: margin-right var(--mo-duration-mid) var(--mo-easing);
}

.right-sidebar.visible {
  margin-right: 0;
}
</style>
