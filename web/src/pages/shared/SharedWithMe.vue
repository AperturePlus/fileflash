<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { Text } from '../../components/atoms';
import { SegmentedControl } from '../../components/molecules';
import { EmptyState } from '../../components/organisms/files';
import { SharedReceivedTable, SharedLinksTable, SharedBatchBar } from '../../components/organisms/sharing';
import { useSharingCenter, type SharedTab } from '../../composables/useSharingCenter';
import { useLocaleStore } from '../../store/locale';

const localeStore = useLocaleStore();
const t = localeStore.t;
const s = useSharingCenter();
const tabOptions = computed(() => [
  { value: 'received', label: t('sharing.tab.sharedWithMe') },
  { value: 'links', label: t('sharing.tab.myShareLinks') },
]);
onMounted(s.loadData);
</script>

<template>
  <section class="page">
    <header class="page__header">
      <div>
        <Text variant="h1" as="h1">{{ t('sharing.page.title') }}</Text>
        <Text variant="small" as="p">{{ t('sharing.page.description') }}</Text>
      </div>
      <SegmentedControl :model-value="s.activeTab.value" :options="tabOptions"
        @update:model-value="(v) => s.switchTab(v as SharedTab)" />
    </header>

    <EmptyState v-if="s.isLoading.value" variant="loading" />
    <template v-else-if="s.activeTab.value === 'received'">
      <EmptyState v-if="!s.sharedItems.value.length" variant="empty" :message="t('sharing.empty.received')" />
      <SharedReceivedTable v-else :items="s.sharedItems.value" :selection="s.selection.selectedItems.value"
        @toggle="s.selection.toggleSelection" @toggle-all="s.toggleAll" @accept="s.acceptOne" />
    </template>
    <template v-else>
      <EmptyState v-if="!s.myShares.value.length" variant="empty" :message="t('sharing.empty.links')" />
      <SharedLinksTable
        v-else
        :items="s.myShares.value"
        @copy="s.copyShare"
        @delete="s.removeShare"
        @regenerate-password="s.regenerateAndShowPassword"
      />
    </template>

    <Transition name="bulk-bar">
      <div v-if="s.showBatch.value" class="page__bulk-bar-wrap">
        <SharedBatchBar :count="s.selection.selectedCount.value" @accept="s.acceptSelected" @clear="s.selection.clear" />
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; height: 100%; min-height: 0; position: relative; }
.page__header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
}
.page__bulk-bar-wrap {
  position: absolute; left: 0; right: 0; bottom: 16px;
  display: flex; justify-content: center;
  z-index: 20; pointer-events: none;
}
.page__bulk-bar-wrap > :deep(.shared-batch) {
  pointer-events: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}
.bulk-bar-enter-active, .bulk-bar-leave-active {
  transition: transform var(--mo-duration-mid) var(--mo-easing), opacity var(--mo-duration-mid) var(--mo-easing);
}
.bulk-bar-enter-from, .bulk-bar-leave-to { opacity: 0; transform: translateY(12px); }
</style>
