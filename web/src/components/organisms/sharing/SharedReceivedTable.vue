<script setup lang="ts">
import { computed } from 'vue';
import { Checkbox, Text } from '../../atoms';
import { Button, Tag } from '../../molecules';
import type { SharedItem } from '../../../types/share';
import { useLocaleStore } from '../../../store/locale';

const props = defineProps<{
  items: SharedItem[];
  selection: Set<string>;
}>();

const emit = defineEmits<{
  (e: 'toggle', id: string): void;
  (e: 'toggle-all', next: boolean): void;
  (e: 'accept', item: SharedItem): void;
}>();

const allSelected = computed(() => props.items.length > 0 && props.items.every((i) => props.selection.has(i.id)));
const someSelected = computed(() => props.items.some((i) => props.selection.has(i.id)) && !allSelected.value);

const localeStore = useLocaleStore();
const t = localeStore.t;

const formatTime = (s: string) => new Date(s).toLocaleString();
const formatItemType = (itemType: SharedItem['itemType']) =>
  t(itemType === 'folder' ? 'sharing.itemType.folder' : 'sharing.itemType.file');
const formatPermission = (permission: SharedItem['permission']) => {
  return permission === 'write' ? t('sharing.permission.write') : t('sharing.permission.read');
};

const onHeaderToggle = () => emit('toggle-all', !allSelected.value);
</script>

<template>
  <div class="shared-table" role="table">
    <div class="shared-table__head" role="row">
      <div class="shared-table__cell shared-table__cell--check">
        <Checkbox :model-value="allSelected" :data-indeterminate="someSelected" @update:model-value="onHeaderToggle" />
      </div>
      <Text variant="label" as="div" class="shared-table__cell">{{ t('sharing.table.received.name') }}</Text>
      <Text variant="label" as="div" class="shared-table__cell">{{ t('sharing.table.received.sharedBy') }}</Text>
      <Text variant="label" as="div" class="shared-table__cell">{{ t('sharing.table.received.permission') }}</Text>
      <Text variant="label" as="div" class="shared-table__cell">{{ t('sharing.table.received.sharedAt') }}</Text>
      <div class="shared-table__cell shared-table__cell--action" />
    </div>

    <div
      v-for="item in items"
      :key="item.id"
      class="shared-table__row"
      :class="{ 'shared-table__row--selected': selection.has(item.id) }"
      role="row"
      @click="emit('toggle', item.id)"
    >
      <div class="shared-table__cell shared-table__cell--check" @click.stop>
        <Checkbox :model-value="selection.has(item.id)" @update:model-value="emit('toggle', item.id)" />
      </div>

      <div class="shared-table__cell shared-table__cell--name">
        <Text variant="body" as="span" class="shared-table__name">{{ item.name }}</Text>
        <Tag>{{ formatItemType(item.itemType) }}</Tag>
      </div>

      <div class="shared-table__cell">
        <Text variant="body" as="span">{{ item.sharedBy }}</Text>
      </div>

      <div class="shared-table__cell">
        <Tag>{{ formatPermission(item.permission) }}</Tag>
      </div>

      <div class="shared-table__cell shared-table__cell--mono">{{ formatTime(item.sharedAt) }}</div>

      <div class="shared-table__cell shared-table__cell--action" @click.stop>
        <Button size="sm" variant="primary" @click="emit('accept', item)">{{ t('sharing.table.received.accept') }}</Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shared-table { display: flex; flex-direction: column; }
.shared-table__head,
.shared-table__row {
  display: grid;
  grid-template-columns: 44px 1.6fr 1fr 0.7fr 1.2fr 120px;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  min-height: var(--row-h);
}
.shared-table__head {
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-raised);
  min-height: 32px;
}
.shared-table__row {
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-base);
  cursor: default;
}
.shared-table__row:hover { background: var(--surface-inset); }
.shared-table__row--selected {
  background: rgb(var(--ac-rgb) / 0.10);
  box-shadow: inset 2px 0 0 var(--ac);
}
.shared-table__cell { min-width: 0; }
.shared-table__cell--name {
  display: flex; align-items: center; gap: 10px;
  overflow: hidden;
}
.shared-table__name {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1; min-width: 0;
}
.shared-table__cell--mono {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: var(--text-data);
  color: var(--text-secondary);
}
.shared-table__cell--action {
  display: flex; justify-content: flex-end;
}
</style>
