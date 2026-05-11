<script setup lang="ts">
defineProps<{ active: boolean }>();
defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="ff-tab"
    :class="{ 'ff-tab--active': active }"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.ff-tab {
  display: inline-flex; align-items: center;
  padding: 8px 14px;
  background: transparent; border: 0;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-family: var(--font-sans); font-size: var(--text-body); font-weight: var(--weight-medium);
  cursor: pointer;
  transition: color var(--mo-duration-fast) var(--mo-easing), border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-tab:hover { color: var(--text-primary); }
.ff-tab--active { color: var(--ac); border-bottom-color: var(--ac); }
</style>
