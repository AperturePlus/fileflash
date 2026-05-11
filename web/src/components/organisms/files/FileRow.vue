<script setup lang="ts">
import { computed } from 'vue';
import { Icon } from '../../atoms';
import DropdownMenu from '../../common/DropdownMenu.vue';
import { getIconForFile } from '../../../utils/fileIcons';
import type { ContentItem, FileItem, FolderItem } from '../../../types/file';
import { useLocaleStore } from '../../../store/locale';

const props = defineProps<{
  item: ContentItem;
  selected: boolean;
  renaming: boolean;
  renameValue: string;
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const emit = defineEmits<{
  (e: 'update:renameValue', v: string): void;
  (e: 'toggleSelect', id: string): void;
  (e: 'click', item: ContentItem): void;
  (e: 'toggleStar', item: ContentItem): void;
  (e: 'download', item: FileItem): void;
  (e: 'extract-archive', item: FileItem): void;
  (e: 'start-rename', item: ContentItem): void;
  (e: 'cancel-rename'): void;
  (e: 'finish-rename'): void;
  (e: 'start-move', item: ContentItem): void;
  (e: 'start-share', item: ContentItem): void;
  (e: 'delete', item: ContentItem): void;
  (e: 'dragstart', payload: { event: DragEvent; item: ContentItem }): void;
  (e: 'drop-on-folder', payload: { event: DragEvent; folder: FolderItem }): void;
}>();

const renameProxy = computed({
  get: () => props.renameValue,
  set: (v: string) => emit('update:renameValue', v),
});

const isArchiveFile = (f: FileItem) => {
  const n = (f.name || '').toLowerCase();
  return n.endsWith('.zip') || n.endsWith('.7z') || n.endsWith('.tar')
      || n.endsWith('.tar.gz') || n.endsWith('.tgz') || n.endsWith('.gz');
};

const formatTime = (s: string) => new Date(s).toLocaleString();
const formatSize = (b: number) => `${(b / 1024).toFixed(1)} KB`;
</script>

<template>
  <div
    class="row"
    :class="{ 'row--selected': selected }"
    draggable="true"
    @click="emit('click', item)"
    @dragstart="emit('dragstart', { event: $event, item })"
    @dragover.prevent
    @drop.prevent="item.itemType === 'folder' && emit('drop-on-folder', { event: $event, folder: item as FolderItem })"
  >
    <div class="row__check" @click.stop>
      <input
        type="checkbox"
        :checked="selected"
        @change.stop="emit('toggleSelect', item.id)"
      />
    </div>

    <div class="row__name">
      <img
        v-if="item.itemType === 'folder'"
        src="../../../assets/generic/folder.svg"
        alt=""
        class="row__icon"
      />
      <img v-else :src="getIconForFile(item.name)" alt="" class="row__icon" />

      <input
        v-if="renaming"
        v-model="renameProxy"
        class="row__rename"
        @blur="emit('finish-rename')"
        @keydown.enter.prevent="emit('finish-rename')"
        @keydown.esc.prevent="emit('cancel-rename')"
      />
      <span v-else class="row__label">{{ item.name }}</span>

      <button
        class="row__star"
        :class="{ 'row__star--on': item.isStarred }"
        :aria-label="item.isStarred ? t('files.table.aria.unstar') : t('files.table.aria.star')"
        @click.stop="emit('toggleStar', item)"
      >
        <Icon name="star" :size="14" />
      </button>
    </div>

    <div class="row__size">
      <span v-if="item.itemType === 'file'">{{ formatSize((item as FileItem).size) }}</span>
      <span v-else>--</span>
    </div>

    <div class="row__time">{{ formatTime(item.updatedAt) }}</div>

    <div class="row__actions" @click.stop>
      <DropdownMenu>
        <template #trigger>
          <button class="row__menu" :aria-label="t('files.table.aria.rowActions')">…</button>
        </template>
        <template #content>
          <div class="row__menu-list">
            <button v-if="item.itemType === 'file'" @click="emit('download', item as FileItem)">{{ t('files.action.download') }}</button>
            <button
              v-if="item.itemType === 'file' && isArchiveFile(item as FileItem)"
              @click="emit('extract-archive', item as FileItem)"
            >{{ t('files.action.extract') }}…</button>
            <button @click="emit('start-rename', item)">{{ t('files.action.rename') }}</button>
            <button @click="emit('start-move', item)">{{ t('files.action.move') }}</button>
            <button @click="emit('start-share', item)">{{ t('files.action.share') }}</button>
            <button @click="emit('toggleStar', item)">
              {{ item.isStarred ? t('files.action.unstar') : t('files.action.star') }}
            </button>
            <button class="row__menu-danger" @click="emit('delete', item)">{{ t('files.action.delete') }}</button>
          </div>
        </template>
      </DropdownMenu>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 44px 1.6fr 0.8fr 1.1fr 56px;
  align-items: center;
  gap: 12px;
  min-height: 40px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-base);
  font-size: 13.5px;
  cursor: default;
}
.row:hover { background: var(--surface-inset); }
.row--selected {
  background: rgb(var(--ac-rgb) / 0.12);
  box-shadow: inset 2px 0 0 var(--ac);
}
.row__name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.row__icon { width: 18px; height: 18px; flex: none; }
.row__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
  flex: 1;
}
.row__rename {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--ac);
  color: var(--text-primary);
  padding: 2px 6px;
  font: inherit;
}
.row__star {
  width: 22px; height: 22px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  padding: 0;
}
.row__star--on { color: var(--ac); }
.row__star:hover { color: var(--ac); }
.row__size, .row__time {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  color: var(--text-secondary);
  font-size: 12.5px;
}
.row__menu {
  width: 26px; height: 26px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
}
.row__menu-list {
  display: flex; flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  min-width: 160px;
}
.row__menu-list button {
  height: 32px;
  border: none;
  background: transparent;
  padding: 0 12px;
  text-align: left;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
}
.row__menu-list button:hover { background: var(--surface-inset); color: var(--text-primary); }
.row__menu-danger { color: var(--status-error) !important; }
</style>
