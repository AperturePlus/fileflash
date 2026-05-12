<script setup lang="ts">
import { Text } from '../../atoms';
import { Button } from '../../molecules';
import { useLocaleStore } from '../../../store/locale';

defineProps<{
  isFile: boolean;
  isFolder: boolean;
  canPreview: boolean;
  canDownload: boolean;
  isPreviewing: boolean;
  isDownloading: boolean;
  isSaving: boolean;
}>();

defineEmits<{
  (e: 'preview'): void;
  (e: 'download'): void;
  (e: 'save'): void;
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;
</script>

<template>
  <div class="share-actions">
    <Text variant="h2" as="h3" class="share-actions__title">{{ t('share.actions.title') }}</Text>
    <div class="share-actions__row">
      <Button
        v-if="isFile"
        variant="ghost"
        :disabled="!canPreview || isPreviewing"
        :loading="isPreviewing"
        @click="$emit('preview')"
      >
        {{ isPreviewing ? t('share.actions.loading') : t('share.actions.preview') }}
      </Button>
      <Button
        v-if="isFile"
        variant="ghost"
        :disabled="!canDownload || isDownloading"
        :loading="isDownloading"
        @click="$emit('download')"
      >
        {{ isDownloading ? t('share.actions.downloading') : t('share.actions.download') }}
      </Button>
      <Button variant="primary" :disabled="isSaving" :loading="isSaving" @click="$emit('save')">
        {{ isSaving ? t('share.actions.saving') : isFolder ? t('share.actions.saveFolder') : t('share.actions.save') }}
      </Button>
    </div>
  </div>
</template>

<style scoped>
.share-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  padding: 16px;
}
.share-actions__title { margin: 0; }
.share-actions__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
