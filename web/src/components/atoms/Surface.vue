<script setup lang="ts">
withDefaults(defineProps<{
  elevation?: 'base' | 'raised' | 'inset';
  bordered?: boolean;
}>(), { elevation: 'base', bordered: false });
</script>

<template>
  <div class="ff-surface" :class="[
    `ff-surface--${elevation}`,
    bordered && 'ff-surface--bordered',
  ]">
    <slot />
  </div>
</template>

<style scoped>
.ff-surface--base   { background: var(--surface-base); }
.ff-surface--raised { background: var(--surface-raised); }
.ff-surface--inset  { background: var(--surface-inset); }
.ff-surface--bordered { border: 1px solid var(--border-default); }
</style>
