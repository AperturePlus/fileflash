<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  value: number;
  tone?: 'accent' | 'success' | 'warning' | 'error' | 'info';
}>(), { tone: 'accent' });

const widthPct = computed(() => {
  const clamped = Math.max(0, Math.min(1, props.value));
  return `${clamped * 100}%`;
});
</script>

<template>
  <div class="ff-bar" :class="`ff-bar--${tone}`" :style="{ width: widthPct }" />
</template>

<style scoped>
.ff-bar { height: 4px; background: var(--ac); }
.ff-bar--success { background: var(--status-success); }
.ff-bar--warning { background: var(--status-warning); }
.ff-bar--error   { background: var(--status-error); }
.ff-bar--info    { background: var(--status-info); }
</style>
