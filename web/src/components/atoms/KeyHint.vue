<script setup lang="ts">
defineProps<{ keys: string[] }>();
</script>

<template>
  <span class="ff-keyhint" aria-hidden="true">
    <template v-for="(k, i) in keys" :key="i">
      <kbd>{{ k }}</kbd>
      <span v-if="i < keys.length - 1" class="ff-keyhint-sep">+</span>
    </template>
  </span>
</template>

<style scoped>
.ff-keyhint { display: inline-flex; align-items: center; gap: 4px; }
.ff-keyhint kbd {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  color: var(--text-secondary);
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  line-height: 1.4;
}
.ff-keyhint-sep { color: var(--text-dim); font-size: var(--text-label); }
</style>
