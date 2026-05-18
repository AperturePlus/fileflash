<script setup lang="ts">
withDefaults(defineProps<{
  tone?: 'accent' | 'success' | 'warning' | 'error' | 'info';
}>(), { tone: 'accent' });
</script>

<template>
  <span class="ff-dot" :class="`ff-dot--${tone}`" aria-hidden="true" />
</template>

<style scoped>
.ff-dot { display: inline-block; width: 8px; height: 8px; background: var(--ac); }
.ff-dot--success { background: var(--status-success); }
.ff-dot--warning { background: var(--status-warning); }
.ff-dot--error   { background: var(--status-error); }
.ff-dot--info    { background: var(--status-info); }
</style>
