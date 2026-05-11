<script setup lang="ts">
import { Icon, Spinner, Text } from '../../atoms';
import { useLocaleStore } from '../../../store/locale';

defineProps<{
  variant: 'loading' | 'empty' | 'no-results';
  query?: string;
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;
</script>

<template>
  <div class="empty-state" :data-variant="variant">
    <template v-if="variant === 'loading'">
      <Spinner />
      <Text variant="label">{{ t('files.empty.loading') }}</Text>
    </template>
    <template v-else-if="variant === 'empty'">
      <Icon name="folder" :size="32" />
      <Text variant="body">{{ t('files.empty.folderEmpty') }}</Text>
      <Text variant="small">{{ t('files.empty.emptyHint') }}</Text>
    </template>
    <template v-else>
      <Icon name="search" :size="32" />
      <Text variant="body">{{ t('files.empty.noMatch') }} "{{ query }}"</Text>
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
