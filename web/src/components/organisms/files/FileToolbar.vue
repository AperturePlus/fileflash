<script setup lang="ts">
import { computed } from 'vue';
import { Button, SearchField, SegmentedControl } from '../../molecules';
import type { SegmentedOption } from '../../molecules';
import { useLocaleStore } from '../../../store/locale';

type SortKey = 'name' | 'size' | 'updatedAt';
const SORT_ORDER: SortKey[] = ['name', 'size', 'updatedAt'];

const props = defineProps<{
  viewMode: 'list' | 'grid';
  sortKey: SortKey;
  sortDirection: 'asc' | 'desc';
  searchQuery: string;
  isSearching: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:viewMode', v: 'list' | 'grid'): void;
  (e: 'update:searchQuery', v: string): void;
  (e: 'clear-search'): void;
  (e: 'sort', key: SortKey): void;
  (e: 'create-folder'): void;
  (e: 'upload'): void;
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const viewOptions = computed<SegmentedOption[]>(() => [
  { value: 'list', label: t('files.toolbar.view.list') },
  { value: 'grid', label: t('files.toolbar.view.grid') },
]);

const sortLabelMap = computed<Record<SortKey, string>>(() => ({
  name: t('files.toolbar.sort.name'),
  size: t('files.toolbar.sort.size'),
  updatedAt: t('files.toolbar.sort.updated'),
}));

const nextSortKey = computed<SortKey>(() => {
  const i = SORT_ORDER.indexOf(props.sortKey);
  return SORT_ORDER[(i + 1) % SORT_ORDER.length];
});

function onSortClick() { emit('sort', nextSortKey.value); }
function onViewChange(v: string | number) { emit('update:viewMode', v as 'list' | 'grid'); }
</script>

<template>
  <div class="toolbar">
    <div class="toolbar__left">
      <slot name="breadcrumb" />
      <div v-if="isSearching" class="toolbar__search-tag">
        <span>{{ t('files.toolbar.searchTag') }}: "{{ searchQuery }}"</span>
        <button class="toolbar__clear" @click="emit('clear-search')">{{ t('files.toolbar.clear') }}</button>
      </div>
    </div>

    <div class="toolbar__right">
      <SearchField
        :model-value="searchQuery"
        :placeholder="t('files.toolbar.searchPlaceholder')"
        @update:model-value="emit('update:searchQuery', $event)"
      />

      <SegmentedControl
        :model-value="viewMode"
        :options="viewOptions"
        @update:model-value="onViewChange"
      />

      <button
        data-test="sort"
        class="toolbar__sort"
        @click="onSortClick"
      >
        {{ t('files.toolbar.sort') }} · {{ sortLabelMap[sortKey] }} {{ sortDirection === 'asc' ? '↑' : '↓' }}
      </button>

      <Button data-test="new-folder" icon="folderPlus" variant="ghost" @click="emit('create-folder')">
        {{ t('files.toolbar.newFolder') }}
      </Button>
      <Button data-test="upload" icon="upload" variant="primary" @click="emit('upload')">
        {{ t('files.toolbar.upload') }}
      </Button>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-default);
}
.toolbar__left {
  display: flex; align-items: center; gap: 12px;
  min-width: 0;
}
.toolbar__right {
  display: flex; align-items: center; gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.toolbar__search-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 8px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
}
.toolbar__clear {
  background: transparent;
  border: none;
  color: var(--ac);
  font-family: var(--font-mono);
  letter-spacing: 0.18em;
  font-size: 10px;
  cursor: pointer;
}
.toolbar__sort {
  height: 32px;
  padding: 0 10px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  cursor: pointer;
}
.toolbar__sort:hover { color: var(--text-primary); border-color: var(--ac); }
</style>
