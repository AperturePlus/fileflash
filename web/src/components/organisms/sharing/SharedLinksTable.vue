<script setup lang="ts">
import { Text } from '../../atoms';
import { Button, Tag } from '../../molecules';
import type { Share } from '../../../types/share';

defineProps<{ items: Share[] }>();

defineEmits<{
  (e: 'copy', share: Share): void;
  (e: 'delete', share: Share): void;
}>();

const formatTime = (s: string) => new Date(s).toLocaleString();
</script>

<template>
  <div class="links-table" role="table">
    <div class="links-table__head" role="row">
      <Text variant="label" as="div" class="links-table__cell">Resource</Text>
      <Text variant="label" as="div" class="links-table__cell">Share Link</Text>
      <Text variant="label" as="div" class="links-table__cell">Visits / Downloads</Text>
      <Text variant="label" as="div" class="links-table__cell">Created At</Text>
      <div class="links-table__cell links-table__cell--action" />
    </div>

    <div v-for="share in items" :key="share.shareId" class="links-table__row" role="row">
      <div class="links-table__cell links-table__cell--name">
        <Text variant="body" as="span" class="links-table__name">{{ share.itemInfo.name }}</Text>
        <Tag>{{ share.itemType }}</Tag>
      </div>

      <div class="links-table__cell">
        <code class="links-table__code">{{ share.shareLink }}</code>
      </div>

      <div class="links-table__cell links-table__cell--mono">
        {{ share.visitCount || 0 }} / {{ share.downloadCount || 0 }}
      </div>

      <div class="links-table__cell links-table__cell--mono">{{ formatTime(share.createdAt) }}</div>

      <div class="links-table__cell links-table__cell--action">
        <Button size="sm" variant="ghost" @click="$emit('copy', share)">Copy</Button>
        <Button size="sm" variant="danger" @click="$emit('delete', share)">Delete</Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.links-table { display: flex; flex-direction: column; }
.links-table__head,
.links-table__row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 0.9fr 1.1fr 160px;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  min-height: var(--row-h);
}
.links-table__head {
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-raised);
  min-height: 32px;
}
.links-table__row {
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-base);
}
.links-table__row:hover { background: var(--surface-inset); }
.links-table__cell { min-width: 0; }
.links-table__cell--name {
  display: flex; align-items: center; gap: 10px;
  overflow: hidden;
}
.links-table__name {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1; min-width: 0;
}
.links-table__cell--mono {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: var(--text-data);
  color: var(--text-secondary);
}
.links-table__cell--action {
  display: flex; justify-content: flex-end; gap: 6px;
}
.links-table__code {
  font-family: var(--font-mono);
  font-size: var(--text-data);
  color: var(--text-primary);
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  padding: 2px 8px;
  white-space: nowrap;
}
</style>
