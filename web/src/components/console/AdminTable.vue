<script setup lang="ts">
defineProps<{
  items: unknown[];
  loading?: boolean;
  totalPages?: number;
  currentPage?: number;
}>();
defineEmits<{ (e: 'page-change', page: number): void }>();
</script>

<template>
  <div class="admin-table">
    <div v-if="loading" class="admin-table__hint">Loading…</div>
    <div v-else-if="!items.length" class="admin-table__hint">No data.</div>
    <div v-else class="admin-table__rows">
      <template v-for="(row, i) in items" :key="i">
        <slot name="row" :row="row" :index="i" />
      </template>
    </div>
    <div v-if="totalPages && totalPages > 1" class="admin-table__pager">
      <button
        v-for="p in totalPages"
        :key="p"
        :class="{ 'is-active': p === currentPage }"
        @click="$emit('page-change', p)"
      >{{ p }}</button>
    </div>
  </div>
</template>

<style scoped>
.admin-table {
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
}
.admin-table__hint {
  padding: var(--sp-xl);
  text-align: center;
  color: var(--text-tertiary);
  background: var(--surface-raised);
  border: 1px dashed var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.admin-table__rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.admin-table__pager {
  display: flex;
  gap: var(--sp-xs);
  margin-top: var(--sp-md);
  justify-content: flex-end;
}
.admin-table__pager button {
  min-width: 28px;
  height: 28px;
  background: var(--surface-raised);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  cursor: pointer;
}
.admin-table__pager button:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
}
.admin-table__pager button.is-active {
  background: var(--ac);
  color: var(--ac-fg);
  border-color: var(--ac);
}
</style>
