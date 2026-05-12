<script setup lang="ts">
import { Text } from '../../atoms';
import { Button } from '../../molecules';
import { getIconForFile } from '../../../utils/fileIcons';
import type { RecycleBinItem } from '../../../types/file';

defineProps<{ items: RecycleBinItem[] }>();

defineEmits<{
  (e: 'restore', item: RecycleBinItem): void;
  (e: 'permanent-delete', item: RecycleBinItem): void;
}>();

const formatTime = (s: string) => new Date(s).toLocaleString();
</script>

<template>
  <div class="trash-table" role="table">
    <div class="trash-table__head" role="row">
      <Text variant="label" as="div" class="trash-table__cell">Name</Text>
      <Text variant="label" as="div" class="trash-table__cell">Original Location</Text>
      <Text variant="label" as="div" class="trash-table__cell">Deleted At</Text>
      <Text variant="label" as="div" class="trash-table__cell">Expires In</Text>
      <div class="trash-table__cell trash-table__cell--action" />
    </div>

    <div v-for="item in items" :key="item.id" class="trash-table__row" role="row">
      <div class="trash-table__cell trash-table__cell--name">
        <img :src="getIconForFile(item.name)" alt="" class="trash-table__icon" />
        <Text variant="body" as="span" class="trash-table__name">{{ item.name }}</Text>
      </div>

      <div class="trash-table__cell trash-table__cell--path">{{ item.originalPath }}</div>
      <div class="trash-table__cell trash-table__cell--mono">{{ formatTime(item.deletedAt) }}</div>
      <div
        class="trash-table__cell trash-table__cell--mono"
        :class="{ 'trash-table__cell--warning': item.daysUntilPermanentDelete <= 7 }"
      >
        {{ item.daysUntilPermanentDelete }} days
      </div>

      <div class="trash-table__cell trash-table__cell--action">
        <Button size="sm" variant="ghost" @click="$emit('restore', item)">Restore</Button>
        <Button size="sm" variant="danger" @click="$emit('permanent-delete', item)">Delete</Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trash-table { display: flex; flex-direction: column; }
.trash-table__head,
.trash-table__row {
  display: grid;
  grid-template-columns: 1.5fr 1.3fr 1fr 0.7fr 180px;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  min-height: var(--row-h);
}
.trash-table__head {
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-raised);
  min-height: 32px;
}
.trash-table__row {
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-base);
}
.trash-table__row:hover { background: var(--surface-inset); }
.trash-table__cell { min-width: 0; }
.trash-table__cell--name {
  display: flex; align-items: center; gap: 10px;
  overflow: hidden;
}
.trash-table__icon { width: 18px; height: 18px; flex: none; }
.trash-table__name {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1; min-width: 0;
}
.trash-table__cell--path,
.trash-table__cell--mono {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: var(--text-data);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.trash-table__cell--warning { color: var(--status-warning); }
.trash-table__cell--action {
  display: flex; justify-content: flex-end; gap: 6px;
}
</style>
