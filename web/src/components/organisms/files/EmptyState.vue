<script setup lang="ts">
import { Icon, Spinner, Text } from '../../atoms';

defineProps<{
  variant: 'loading' | 'empty' | 'no-results';
  query?: string;
}>();
</script>

<template>
  <div class="empty-state" :data-variant="variant">
    <template v-if="variant === 'loading'">
      <Spinner />
      <Text variant="label">LOADING</Text>
    </template>
    <template v-else-if="variant === 'empty'">
      <Icon name="folder" :size="32" />
      <Text variant="body">This folder is empty</Text>
      <Text variant="small">Upload files or create a folder.</Text>
    </template>
    <template v-else>
      <Icon name="search" :size="32" />
      <Text variant="body">No matches for "{{ query }}"</Text>
    </template>
  </div>
</template>

<style scoped>
.empty-state {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-dim);
}
</style>
