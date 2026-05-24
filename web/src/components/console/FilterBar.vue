<script setup lang="ts">
defineEmits<{ (e: 'change'): void }>();
</script>

<template>
  <div class="filter-bar">
    <slot />
    <button class="filter-bar__apply" @click="$emit('change')">Apply</button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: var(--sp-md);
  align-items: center;
  flex-wrap: wrap;
  padding: var(--sp-md) var(--sp-lg);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.filter-bar :deep(input),
.filter-bar :deep(select) {
  height: 32px;
  padding: 0 var(--sp-sm);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-body);
}
.filter-bar :deep(input:focus),
.filter-bar :deep(select:focus) {
  outline: none;
  border-color: var(--ac);
}
.filter-bar__apply {
  height: 32px;
  padding: 0 14px;
  background: var(--ac);
  border: none;
  color: var(--ac-fg);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
}
.filter-bar__apply:hover {
  filter: brightness(1.08);
}
</style>
