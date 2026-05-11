<script setup lang="ts">
withDefaults(defineProps<{
  tone?: 'success' | 'warning' | 'error' | 'info' | 'accent';
}>(), { tone: 'success' });
</script>

<template>
  <span class="ff-badge" :class="`ff-badge--${tone}`">
    <slot />
  </span>
</template>

<style scoped>
.ff-badge {
  display: inline-flex; align-items: center;
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
}
.ff-badge--success { color: var(--status-success); border-color: rgba(var(--status-success-rgb), 0.45); background: rgba(var(--status-success-rgb), 0.12); }
.ff-badge--warning { color: var(--status-warning); border-color: rgba(var(--status-warning-rgb), 0.45); background: rgba(var(--status-warning-rgb), 0.12); }
.ff-badge--error   { color: var(--status-error);   border-color: rgba(var(--status-error-rgb), 0.45);   background: rgba(var(--status-error-rgb), 0.12); }
.ff-badge--info    { color: var(--status-info);    border-color: rgba(var(--status-info-rgb), 0.45);    background: rgba(var(--status-info-rgb), 0.12); }
.ff-badge--accent  { color: var(--ac);              border-color: rgba(var(--ac-rgb), 0.45);              background: rgba(var(--ac-rgb), 0.12); }
</style>
