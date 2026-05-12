<script setup lang="ts">
import { Text } from '../../atoms';
import { Button } from '../../molecules';

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
</script>

<template>
  <div class="share-actions">
    <Text variant="h2" as="h3" class="share-actions__title">Actions</Text>
    <div class="share-actions__row">
      <Button
        v-if="isFile"
        variant="ghost"
        :disabled="!canPreview || isPreviewing"
        :loading="isPreviewing"
        @click="$emit('preview')"
      >
        {{ isPreviewing ? 'Loading...' : 'Preview' }}
      </Button>
      <Button
        v-if="isFile"
        variant="ghost"
        :disabled="!canDownload || isDownloading"
        :loading="isDownloading"
        @click="$emit('download')"
      >
        {{ isDownloading ? 'Downloading...' : 'Download' }}
      </Button>
      <Button variant="primary" :disabled="isSaving" :loading="isSaving" @click="$emit('save')">
        {{ isSaving ? 'Saving...' : isFolder ? 'Save Folder to My Space' : 'Save to My Space' }}
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
