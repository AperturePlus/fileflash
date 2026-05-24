<script setup lang="ts">
defineProps<{
  value: string;
  tone?: 'positive' | 'warning' | 'danger' | 'neutral';
}>();
</script>

<template>
  <span class="status-badge" :class="tone ? `is-${tone}` : 'is-neutral'">{{ value }}</span>
</template>

<style scoped>
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: lowercase;
  border: 1px solid;
}
.status-badge.is-neutral  { color: var(--text-secondary); border-color: var(--border-default); background: transparent; }
.status-badge.is-positive { color: var(--status-success); border-color: var(--status-success); background: rgba(var(--status-success-rgb), 0.08); }
.status-badge.is-warning  { color: var(--status-warning); border-color: var(--status-warning); background: rgba(var(--status-warning-rgb), 0.08); }
.status-badge.is-danger   { color: var(--status-error);   border-color: var(--status-error);   background: rgba(var(--status-error-rgb), 0.08); }
</style>
