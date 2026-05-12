<script setup lang="ts">
import { Text } from '../../atoms';
import type { Share } from '../../../types/share';

defineProps<{ share: Share }>();

const formatSize = (bytes: number) => {
  if (!bytes) return '--';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};
</script>

<template>
  <div class="share-info">
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">Type</Text>
      <Text variant="body" as="div">{{ share.itemType }}</Text>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">Name</Text>
      <Text variant="body" as="div" class="share-info__name">{{ share.itemInfo.name }}</Text>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">Size</Text>
      <div class="share-info__mono">{{ formatSize(share.itemInfo.size) }}</div>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">Expires</Text>
      <div class="share-info__mono">{{ share.settings.expireAt || 'Never' }}</div>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">Password</Text>
      <Text variant="body" as="div">{{ share.settings.passwordProtected ? 'Required' : 'Not required' }}</Text>
    </div>
  </div>
</template>

<style scoped>
.share-info {
  display: flex;
  flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.share-info__row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  padding: 10px 16px;
  align-items: center;
}
.share-info__row + .share-info__row {
  border-top: 1px solid var(--border-subtle);
}
.share-info__label {
  color: var(--text-dim);
}
.share-info__name {
  word-break: break-all;
}
.share-info__mono {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: var(--text-data);
  color: var(--text-secondary);
}
</style>
