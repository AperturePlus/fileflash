<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { clearRecycleBin, getRecycleBin, permanentDelete, restoreItem } from '../../api/recycle';
import { Text } from '../../components/atoms';
import { Button } from '../../components/molecules';
import { EmptyState } from '../../components/organisms/files';
import { TrashTable } from '../../components/organisms/trash';
import type { RecycleBinItem } from '../../types/file';
import { eventBus } from '../../utils/eventBus';
import { ui } from '../../utils/ui';

const items = ref<RecycleBinItem[]>([]);
const isLoading = ref(false);

const fetchItems = async () => {
  isLoading.value = true;
  try { items.value = (await getRecycleBin({})).items; }
  catch (e) { console.error('Failed to load recycle bin items', e); }
  finally { isLoading.value = false; }
};

const handleRestore = async (item: RecycleBinItem) => {
  const ok = await ui.confirm({ title: 'Restore Item', message: `Restore "${item.name}"?`, confirmText: 'Restore' });
  if (!ok) return;
  try {
    await restoreItem(item.id, { itemType: item.itemType });
    items.value = items.value.filter((e) => e.id !== item.id);
    eventBus.emit('refresh-file-tree');
    ui.toast({ type: 'success', message: `Restored "${item.name}".` });
  } catch (e) { console.error('Restore failed', e); ui.toast({ type: 'error', message: 'Restore failed.' }); }
};

const handlePermanentDelete = async (item: RecycleBinItem) => {
  const ok = await ui.confirm({ title: 'Permanent Delete', message: `Permanently delete "${item.name}"? This cannot be undone.`, confirmText: 'Delete', danger: true });
  if (!ok) return;
  try {
    await permanentDelete(item.id, item.itemType);
    items.value = items.value.filter((e) => e.id !== item.id);
    ui.toast({ type: 'success', message: `Deleted "${item.name}".` });
  } catch (e) { console.error('Permanent delete failed', e); ui.toast({ type: 'error', message: 'Permanent delete failed.' }); }
};

const handleClearAll = async () => {
  if (!items.value.length) return;
  const ok = await ui.confirm({ title: 'Clear Recycle Bin', message: 'Clear entire recycle bin? This cannot be undone.', confirmText: 'Clear', danger: true });
  if (!ok) return;
  try { await clearRecycleBin(); items.value = []; ui.toast({ type: 'success', message: 'Recycle bin cleared.' }); }
  catch (e) { console.error('Clear recycle bin failed', e); ui.toast({ type: 'error', message: 'Clear recycle bin failed.' }); }
};

onMounted(fetchItems);
</script>

<template>
  <section class="page">
    <header class="page__header">
      <div>
        <Text variant="h1" as="h1">Recycle Bin</Text>
        <Text variant="small" as="p">Items are kept for up to 30 days before automatic cleanup.</Text>
      </div>
      <Button variant="danger" :disabled="!items.length" @click="handleClearAll">Clear Bin</Button>
    </header>

    <EmptyState v-if="isLoading" variant="loading" />
    <EmptyState v-else-if="!items.length" variant="empty" message="Recycle bin is empty." />
    <TrashTable v-else :items="items" @restore="handleRestore" @permanent-delete="handlePermanentDelete" />
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; height: 100%; min-height: 0; }
.page__header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
}
</style>
