<script setup lang="ts">
import { Text } from '../../atoms';
import type { Share } from '../../../types/share';
import { useLocaleStore } from '../../../store/locale';

defineProps<{ share: Share }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const formatSize = (bytes: number) => {
  if (!bytes) return '--';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};
const formatItemType = (itemType: Share['itemType']) =>
  t(itemType === 'folder' ? 'share.itemType.folder' : 'share.itemType.file');
</script>

<template>
  <div class="share-info">
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">{{ t('share.info.type') }}</Text>
      <Text variant="body" as="div">{{ formatItemType(share.itemType) }}</Text>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">{{ t('share.info.name') }}</Text>
      <Text variant="body" as="div" class="share-info__name">{{ share.itemInfo.name }}</Text>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">{{ t('share.info.size') }}</Text>
      <div class="share-info__mono">{{ formatSize(share.itemInfo.size) }}</div>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">{{ t('share.info.expires') }}</Text>
      <div class="share-info__mono">{{ share.settings.expireAt || t('share.info.never') }}</div>
    </div>
    <div class="share-info__row">
      <Text variant="label" as="div" class="share-info__label">{{ t('share.info.password') }}</Text>
      <Text variant="body" as="div">{{ share.settings.passwordProtected ? t('share.info.passwordRequired') : t('share.info.passwordNotRequired') }}</Text>
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
