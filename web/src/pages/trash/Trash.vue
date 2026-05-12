<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { clearRecycleBin, getRecycleBin, permanentDelete, restoreItem } from '../../api/recycle';
import { Text } from '../../components/atoms';
import { Button } from '../../components/molecules';
import { EmptyState } from '../../components/organisms/files';
import { TrashTable } from '../../components/organisms/trash';
import { useLocaleStore } from '../../store/locale';
import type { RecycleBinItem } from '../../types/file';
import { eventBus } from '../../utils/eventBus';
import { ui } from '../../utils/ui';

const localeStore = useLocaleStore();
const t = localeStore.t;
const items = ref<RecycleBinItem[]>([]);
const isLoading = ref(false);

const fetchItems = async () => {
  isLoading.value = true;
  try { items.value = (await getRecycleBin({})).items; }
  catch (e) { console.error('Failed to load recycle bin items', e); }
  finally { isLoading.value = false; }
};

const handleRestore = async (item: RecycleBinItem) => {
  const ok = await ui.confirm({
    title: t('trash.confirm.restore.title'),
    message: t('trash.confirm.restore.message').replace('{itemName}', item.name),
    confirmText: t('trash.confirm.restore.confirm'),
  });
  if (!ok) return;
  try {
    await restoreItem(item.id, { itemType: item.itemType });
    items.value = items.value.filter((e) => e.id !== item.id);
    eventBus.emit('refresh-file-tree');
    ui.toast({ type: 'success', message: t('trash.toast.restored').replace('{itemName}', item.name) });
  } catch (e) {
    console.error('Restore failed', e);
    ui.toast({ type: 'error', message: t('trash.toast.restoreFailed') });
  }
};

const handlePermanentDelete = async (item: RecycleBinItem) => {
  const ok = await ui.confirm({
    title: t('trash.confirm.delete.title'),
    message: t('trash.confirm.delete.message').replace('{itemName}', item.name),
    confirmText: t('trash.confirm.delete.confirm'),
    danger: true,
  });
  if (!ok) return;
  try {
    await permanentDelete(item.id, item.itemType);
    items.value = items.value.filter((e) => e.id !== item.id);
    ui.toast({ type: 'success', message: t('trash.toast.deleted').replace('{itemName}', item.name) });
  } catch (e) {
    console.error('Permanent delete failed', e);
    ui.toast({ type: 'error', message: t('trash.toast.deleteFailed') });
  }
};

const handleClearAll = async () => {
  if (!items.value.length) return;
  const ok = await ui.confirm({
    title: t('trash.confirm.clear.title'),
    message: t('trash.confirm.clear.message'),
    confirmText: t('trash.confirm.clear.confirm'),
    danger: true,
  });
  if (!ok) return;
  try {
    await clearRecycleBin();
    items.value = [];
    ui.toast({ type: 'success', message: t('trash.toast.cleared') });
  } catch (e) {
    console.error('Clear recycle bin failed', e);
    ui.toast({ type: 'error', message: t('trash.toast.clearFailed') });
  }
};

onMounted(fetchItems);
</script>

<template>
  <section class="page">
    <header class="page__header">
      <div>
        <Text variant="h1" as="h1">{{ t('trash.page.title') }}</Text>
        <Text variant="small" as="p">{{ t('trash.page.description') }}</Text>
      </div>
      <Button variant="danger" :disabled="!items.length" @click="handleClearAll">{{ t('trash.page.clearBin') }}</Button>
    </header>

    <EmptyState v-if="isLoading" variant="loading" />
    <EmptyState v-else-if="!items.length" variant="empty" :message="t('trash.page.empty')" />
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
