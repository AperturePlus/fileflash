<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  name: string;
  src?: string;
  size?: 'sm' | 'md';
}>(), { size: 'md' });

const initials = computed(() => {
  const parts = props.name.trim().split(/\s+/);
  if (!parts[0]) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
});
</script>

<template>
  <span class="ff-avatar" :class="`ff-avatar--${size}`">
    <img v-if="src" :src="src" :alt="name" />
    <span v-else class="ff-avatar-initials">{{ initials }}</span>
  </span>
</template>

<style scoped>
.ff-avatar {
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  border: 1px solid var(--border-subtle);
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}
.ff-avatar--md { width: 28px; height: 28px; font-size: 11px; }
.ff-avatar--sm { width: 20px; height: 20px; font-size: 9px; }
.ff-avatar img { width: 100%; height: 100%; object-fit: cover; }
</style>
