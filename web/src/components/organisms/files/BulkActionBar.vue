<script setup lang="ts">
import { MonoNumber } from '../../atoms';
import { Button } from '../../molecules';

defineProps<{ count: number }>();
defineEmits<{
  (e: 'move'): void;
  (e: 'download'): void;
  (e: 'delete'): void;
  (e: 'clear'): void;
}>();
</script>

<template>
  <div v-if="count > 0" class="bulk">
    <div class="bulk__count">
      <MonoNumber :value="count" accent />
      <span class="bulk__label">SELECTED</span>
    </div>
    <div class="bulk__actions">
      <Button data-test="bulk-move" variant="ghost" @click="$emit('move')">MOVE</Button>
      <Button data-test="bulk-download" variant="ghost" @click="$emit('download')">DOWNLOAD</Button>
      <Button data-test="bulk-delete" variant="danger" @click="$emit('delete')">DELETE</Button>
      <Button data-test="bulk-clear" variant="ghost" @click="$emit('clear')">CLEAR</Button>
    </div>
  </div>
</template>

<style scoped>
.bulk {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px;
  padding: 8px 12px;
  background: rgb(var(--ac-rgb) / 0.10);
  border: 1px solid var(--ac);
  color: var(--text-primary);
}
.bulk__count {
  display: inline-flex; align-items: baseline; gap: 8px;
}
.bulk__label {
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
}
.bulk__actions {
  display: inline-flex; align-items: center; gap: 6px;
}
</style>
