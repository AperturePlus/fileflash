<script setup lang="ts">
import IconButton from './IconButton.vue';

defineProps<{ removable?: boolean }>();
defineEmits<{ remove: [] }>();
</script>

<template>
  <span class="ff-tag">
    <slot />
    <IconButton
      v-if="removable"
      icon="close"
      label="Remove"
      size="sm"
      class="ff-tag-remove"
      @click="$emit('remove')"
    />
  </span>
</template>

<style scoped>
.ff-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px;
  font-family: var(--font-sans);
  font-size: var(--text-small);
  color: var(--text-secondary);
  background: var(--surface-inset);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}
.ff-tag-remove { width: 16px; height: 16px; }
</style>
