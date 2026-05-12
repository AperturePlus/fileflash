<script setup lang="ts">
import { computed } from 'vue';
import { Icon } from '../../atoms';
import FileRow from './FileRow.vue';
import DropdownMenu from '../../common/DropdownMenu.vue';
import { getIconForFile } from '../../../utils/fileIcons';
import { useColumnResize } from '../../../composables/useColumnResize';
import type { ContentItem, FileItem, FolderItem } from '../../../types/file';
import { useLocaleStore } from '../../../store/locale';

type SortKey = 'name' | 'size' | 'updatedAt';

const props = defineProps<{
  mode: 'list' | 'grid' | 'tree';
  items: ContentItem[];
  selection: Set<string>;
  renamingId: string | null;
  renameValue: string;
  sortKey: SortKey;
  sortDirection: 'asc' | 'desc';
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const emit = defineEmits<{
  (e: 'update:renameValue', v: string): void;
  (e: 'toggleSelect', id: string): void;
  (e: 'select', payload: { item: ContentItem; modifiers: { shift: boolean } }): void;
  (e: 'activate', item: ContentItem): void;
  (e: 'clear-selection'): void;
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
  (e: 'sort', key: SortKey): void;
}>();

const isSelected = (id: string) => props.selection.has(id);

const sortIcon = computed(() => (props.sortDirection === 'asc' ? 'arrowUp' : 'arrowDown'));
const sortable = computed<Array<{ key: SortKey; label: string }>>(() => [
  { key: 'name', label: t('files.table.col.name') },
  { key: 'size', label: t('files.table.col.size') },
  { key: 'updatedAt', label: t('files.table.col.updated') },
]);

const { colWidths, onResizeStart } = useColumnResize();
const tableStyle = computed<Record<string, string>>(() => ({
  '--col-check': '44px',
  '--col-name': `${colWidths.name}px`,
  '--col-size': `${colWidths.size}px`,
  '--col-time': `${colWidths.time}px`,
  '--col-act': '56px',
}));
const colKeyFor = (key: SortKey): 'name' | 'size' | 'time' =>
  key === 'updatedAt' ? 'time' : key;

const isArchiveFile = (f: FileItem) => {
  const n = (f.name || '').toLowerCase();
  return n.endsWith('.zip') || n.endsWith('.7z') || n.endsWith('.tar')
      || n.endsWith('.tar.gz') || n.endsWith('.tgz') || n.endsWith('.gz');
};
</script>

<template>
  <div v-if="mode === 'list'" class="table" :style="tableStyle" @click.self="emit('clear-selection')">
    <div class="table__head">
      <div class="table__check" />
      <button
        v-for="col in sortable"
        :key="col.key"
        :data-sort-key="col.key"
        class="table__sort"
        :class="{ 'table__sort--active': sortKey === col.key }"
        @click="emit('sort', col.key)"
      >
        {{ col.label }}
        <Icon v-if="sortKey === col.key" :name="sortIcon" :size="12" />
        <span
          class="resize-handle"
          :data-resize-col="colKeyFor(col.key)"
          @pointerdown.stop.prevent="onResizeStart(colKeyFor(col.key), $event as PointerEvent)"
          @click.stop
        />
      </button>
      <div />
    </div>

    <FileRow
      v-for="item in items"
      :key="item.id"
      :item="item"
      :selected="isSelected(item.id)"
      :renaming="renamingId === item.id"
      :rename-value="renameValue"
      @update:rename-value="emit('update:renameValue', $event)"
      @toggle-select="emit('toggleSelect', $event)"
      @select="emit('select', $event)"
      @activate="emit('activate', $event)"
      @toggle-star="emit('toggleStar', $event)"
      @download="emit('download', $event)"
      @extract-archive="emit('extract-archive', $event)"
      @start-rename="emit('start-rename', $event)"
      @cancel-rename="emit('cancel-rename')"
      @finish-rename="emit('finish-rename')"
      @start-move="emit('start-move', $event)"
      @start-share="emit('start-share', $event)"
      @delete="emit('delete', $event)"
      @dragstart="emit('dragstart', $event)"
      @drop-on-folder="emit('drop-on-folder', $event)"
    />
  </div>

  <div v-else-if="mode === 'grid'" class="grid" @click.self="emit('clear-selection')">
    <div
      v-for="item in items"
      :key="item.id"
      class="card"
      :class="{ 'card--selected': isSelected(item.id) }"
      draggable="true"
      @click.stop="emit('select', { item, modifiers: { shift: $event.shiftKey } })"
      @dblclick="renamingId === item.id ? null : emit('activate', item)"
      @dragstart="emit('dragstart', { event: $event, item })"
      @dragover.prevent
      @drop.prevent="item.itemType === 'folder' && emit('drop-on-folder', { event: $event, folder: item as FolderItem })"
    >
      <div class="card__check" @click.stop>
        <input type="checkbox" :checked="isSelected(item.id)" @change.stop="emit('toggleSelect', item.id)" />
      </div>
      <button
        class="card__star"
        :class="{ 'card__star--on': item.isStarred }"
        @click.stop="emit('toggleStar', item)"
        :aria-label="item.isStarred ? t('files.table.aria.unstar') : t('files.table.aria.star')"
      >
        <Icon name="star" :size="14" />
      </button>
      <img
        v-if="item.itemType === 'folder'"
        src="../../../assets/generic/folder.svg"
        alt=""
        class="card__icon"
      />
      <img v-else :src="getIconForFile(item.name)" alt="" class="card__icon" />
      <div class="card__name">
        <input
          v-if="renamingId === item.id"
          :value="renameValue"
          class="card__rename"
          @input="emit('update:renameValue', ($event.target as HTMLInputElement).value)"
          @blur="emit('finish-rename')"
          @keydown.enter.prevent="emit('finish-rename')"
          @keydown.esc.prevent="emit('cancel-rename')"
        />
        <span v-else>{{ item.name }}</span>
      </div>
      <div class="card__actions" @click.stop>
        <DropdownMenu>
          <template #trigger>
            <button class="card__menu" :aria-label="t('files.table.aria.cardActions')">…</button>
          </template>
          <template #content>
            <div class="card__menu-list">
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
              <button class="card__menu-danger" @click="emit('delete', item)">{{ t('files.action.delete') }}</button>
            </div>
          </template>
        </DropdownMenu>
      </div>
    </div>
  </div>

  <div v-else class="tree">
    <slot name="tree" />
  </div>
</template>

<style scoped>
.table {
  display: flex; flex-direction: column;
  border: 1px solid var(--border-default);
  background: var(--surface-base);
}
.table__head {
  display: grid;
  grid-template-columns: var(--col-check) var(--col-name) var(--col-size) var(--col-time) var(--col-act);
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  height: 32px;
  background: var(--surface-inset);
  border-bottom: 1px solid var(--border-default);
  color: var(--text-dim);
  font-size: 11px;
  letter-spacing: 0.18em;
}
.table__sort {
  background: transparent;
  border: none;
  text-align: left;
  color: inherit;
  cursor: pointer;
  display: inline-flex; align-items: center; gap: 4px;
  font-family: inherit;
  font-size: inherit;
  letter-spacing: inherit;
  padding: 0;
  position: relative;
}
.table__sort--active { color: var(--text-primary); }
.resize-handle {
  position: absolute;
  top: 0;
  right: -8px;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
}
.resize-handle:hover {
  background: linear-gradient(to right, transparent, rgb(var(--ac-rgb) / 0.4), transparent);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 12px;
}
.card {
  position: relative;
  display: flex; flex-direction: column;
  align-items: center; gap: 8px;
  padding: 16px 12px;
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  cursor: default;
}
.card:hover { background: var(--surface-inset); }
.card--selected {
  background: rgb(var(--ac-rgb) / 0.12);
  border-color: var(--ac);
}
.card__check { position: absolute; top: 8px; left: 8px; }
.card__star {
  position: absolute; top: 8px; right: 36px;
  width: 22px; height: 22px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: none;
  color: var(--text-dim);
  cursor: pointer;
  padding: 0;
}
.card__star--on { color: var(--ac); }
.card__icon { width: 48px; height: 48px; }
.card__name {
  width: 100%;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-primary);
  word-break: break-all;
}
.card__rename {
  width: 100%;
  background: var(--surface-inset);
  border: 1px solid var(--ac);
  color: var(--text-primary);
  padding: 2px 4px;
  font: inherit;
}
.card__actions { position: absolute; top: 8px; right: 8px; }
.card__menu {
  width: 22px; height: 22px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
  padding: 0;
}
.card__menu-list {
  display: flex; flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  min-width: 160px;
}
.card__menu-list button {
  height: 32px;
  border: none;
  background: transparent;
  padding: 0 12px;
  text-align: left;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
}
.card__menu-list button:hover { background: var(--surface-inset); color: var(--text-primary); }
.card__menu-danger { color: var(--status-error) !important; }
</style>
