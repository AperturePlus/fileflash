<script setup lang="ts">
import { computed } from 'vue';
import DropdownMenu from '../../../components/common/DropdownMenu.vue';
import { getIconForFile } from '../../../utils/fileIcons';
import type { ContentItem, FileItem, FolderItem } from '../../../types/file';

const props = defineProps<{
  viewMode: 'grid' | 'list';
  displayItems: ContentItem[];
  renamingItemId: string | null;
  renameInputValue: string;
  isSelected: (id: string) => boolean;
}>();

const emit = defineEmits<{
  (event: 'update:renameInputValue', value: string): void;
  (event: 'toggleSelection', itemId: string): void;
  (event: 'itemClick', item: ContentItem): void;
  (event: 'dragItemStart', payload: { event: DragEvent; item: ContentItem }): void;
  (event: 'folderDrop', payload: { event: DragEvent; folder: FolderItem }): void;
  (event: 'toggleStar', item: ContentItem): void;
  (event: 'finishRename'): void;
  (event: 'cancelRename'): void;
  (event: 'sort', key: 'name' | 'size' | 'updatedAt'): void;
  (event: 'download', item: FileItem): void;
  (event: 'extractArchive', item: FileItem): void;
  (event: 'startRename', item: ContentItem): void;
  (event: 'startMove', item: ContentItem): void;
  (event: 'startShare', item: ContentItem): void;
  (event: 'delete', item: ContentItem): void;
}>();

const renameValueProxy = computed({
  get: () => props.renameInputValue,
  set: (value: string) => emit('update:renameInputValue', value),
});

const onDragStart = (event: DragEvent, item: ContentItem) => {
  emit('dragItemStart', { event, item });
};

const onFolderDrop = (event: DragEvent, folder: FolderItem) => {
  event.stopPropagation();
  emit('folderDrop', { event, folder });
};

const isArchiveFile = (file: FileItem) => {
  const name = (file.name || '').toLowerCase();
  return name.endsWith('.zip')
    || name.endsWith('.7z')
    || name.endsWith('.tar')
    || name.endsWith('.tar.gz')
    || name.endsWith('.tgz')
    || name.endsWith('.gz');
};
</script>

<template>
  <div v-if="viewMode === 'list'" class="file-list">
    <div class="list-header">
      <div class="col checkbox" />
      <button class="col name" @click="emit('sort', 'name')">Name</button>
      <button class="col size" @click="emit('sort', 'size')">Size</button>
      <button class="col time" @click="emit('sort', 'updatedAt')">Updated</button>
      <div class="col actions" />
    </div>

    <div
      v-for="item in displayItems"
      :key="`list-${item.id}`"
      class="list-row"
      :class="{ selected: isSelected(item.id) }"
      draggable="true"
      @dragstart="onDragStart($event, item)"
      @click="emit('itemClick', item)"
      @drop.stop.prevent="item.itemType === 'folder' && onFolderDrop($event, item as FolderItem)"
      @dragover.prevent
    >
      <div class="col checkbox" @click.stop>
        <input type="checkbox" :checked="isSelected(item.id)" @change.stop="emit('toggleSelection', item.id)" />
      </div>

      <div class="col name name-cell">
        <img v-if="item.itemType === 'folder'" src="../../../assets/generic/folder.svg" alt="Folder" class="icon" />
        <img v-else :src="getIconForFile(item.name)" alt="File" class="icon" />

        <input
          v-if="renamingItemId === item.id"
          v-model="renameValueProxy"
          class="rename-input"
          @blur="emit('finishRename')"
          @keydown.enter.prevent="emit('finishRename')"
          @keydown.esc.prevent="emit('cancelRename')"
        />
        <span v-else>{{ item.name }}</span>

        <button
          class="star-btn"
          :class="{ active: item.isStarred }"
          :title="item.isStarred ? '取消星标' : '设为星标'"
          :aria-label="item.isStarred ? '取消星标' : '设为星标'"
          @click.stop="emit('toggleStar', item)"
        >
          <svg class="star-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2.8l2.92 5.91 6.52.95-4.72 4.6 1.11 6.49L12 17.66l-5.83 3.07 1.11-6.49-4.72-4.6 6.52-.95z" />
          </svg>
        </button>
      </div>

      <div class="col size">{{ item.itemType === 'file' ? `${(item.size / 1024).toFixed(1)} KB` : '--' }}</div>
      <div class="col time">{{ new Date(item.updatedAt).toLocaleString() }}</div>

      <div class="col actions" @click.stop>
        <DropdownMenu>
          <template #trigger>
            <button class="menu-btn">...</button>
          </template>
          <template #content>
            <div class="item-menu">
              <button v-if="item.itemType === 'file'" @click="emit('download', item as FileItem)">Download</button>
              <button v-if="item.itemType === 'file' && isArchiveFile(item as FileItem)" @click="emit('extractArchive', item as FileItem)">Extract...</button>
              <button @click="emit('startRename', item)">Rename</button>
              <button @click="emit('startMove', item)">Move</button>
              <button @click="emit('startShare', item)">Share</button>
              <button class="star-menu-btn" @click="emit('toggleStar', item)">
                <svg class="star-icon" :class="{ active: item.isStarred }" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2.8l2.92 5.91 6.52.95-4.72 4.6 1.11 6.49L12 17.66l-5.83 3.07 1.11-6.49-4.72-4.6 6.52-.95z" />
                </svg>
                <span>{{ item.isStarred ? '取消星标' : '设为星标' }}</span>
              </button>
              <button class="danger" @click="emit('delete', item)">Delete</button>
            </div>
          </template>
        </DropdownMenu>
      </div>
    </div>
  </div>

  <div v-else class="file-grid">
    <div
      v-for="item in displayItems"
      :key="`grid-${item.id}`"
      class="grid-card"
      :class="{ selected: isSelected(item.id) }"
      draggable="true"
      @dragstart="onDragStart($event, item)"
      @click="emit('itemClick', item)"
      @drop.stop.prevent="item.itemType === 'folder' && onFolderDrop($event, item as FolderItem)"
      @dragover.prevent
    >
      <div class="grid-check" @click.stop>
        <input type="checkbox" :checked="isSelected(item.id)" @change.stop="emit('toggleSelection', item.id)" />
      </div>

      <button
        class="star-btn floating"
        :class="{ active: item.isStarred }"
        :title="item.isStarred ? '取消星标' : '设为星标'"
        :aria-label="item.isStarred ? '取消星标' : '设为星标'"
        @click.stop="emit('toggleStar', item)"
      >
        <svg class="star-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2.8l2.92 5.91 6.52.95-4.72 4.6 1.11 6.49L12 17.66l-5.83 3.07 1.11-6.49-4.72-4.6 6.52-.95z" />
        </svg>
      </button>

      <img v-if="item.itemType === 'folder'" src="../../../assets/generic/folder.svg" alt="Folder" class="grid-icon" />
      <img v-else :src="getIconForFile(item.name)" alt="File" class="grid-icon" />

      <div class="grid-name">
        <input
          v-if="renamingItemId === item.id"
          v-model="renameValueProxy"
          class="rename-input"
          @blur="emit('finishRename')"
          @keydown.enter.prevent="emit('finishRename')"
          @keydown.esc.prevent="emit('cancelRename')"
        />
        <span v-else>{{ item.name }}</span>
      </div>

      <div class="grid-actions" @click.stop>
        <DropdownMenu>
          <template #trigger>
            <button class="menu-btn">...</button>
          </template>
          <template #content>
            <div class="item-menu">
              <button v-if="item.itemType === 'file'" @click="emit('download', item as FileItem)">Download</button>
              <button v-if="item.itemType === 'file' && isArchiveFile(item as FileItem)" @click="emit('extractArchive', item as FileItem)">Extract...</button>
              <button @click="emit('startRename', item)">Rename</button>
              <button @click="emit('startMove', item)">Move</button>
              <button @click="emit('startShare', item)">Share</button>
              <button class="star-menu-btn" @click="emit('toggleStar', item)">
                <svg class="star-icon" :class="{ active: item.isStarred }" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2.8l2.92 5.91 6.52.95-4.72 4.6 1.11 6.49L12 17.66l-5.83 3.07 1.11-6.49-4.72-4.6 6.52-.95z" />
                </svg>
                <span>{{ item.isStarred ? '取消星标' : '设为星标' }}</span>
              </button>
              <button class="danger" @click="emit('delete', item)">Delete</button>
            </div>
          </template>
        </DropdownMenu>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-header,
.list-row {
  display: grid;
  grid-template-columns: 44px 1.6fr 0.8fr 1.1fr 56px;
  align-items: center;
  gap: var(--spacing-sm);
}

.list-header {
  padding: 0 8px;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.list-header button {
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  color: inherit;
}

.list-row {
  min-height: 46px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 4px 8px;
}

.list-row:hover {
  background-color: var(--color-bg-tertiary);
}

.list-row.selected {
  background-color: var(--color-primary-light);
  border-color: rgba(var(--color-primary-rgb), 0.3);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.name-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.star-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-text-quaternary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.star-icon {
  width: 16px;
  height: 16px;
}

.star-icon path {
  fill: transparent;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linejoin: round;
  transition: fill 0.2s ease, stroke 0.2s ease;
}

.star-btn.active {
  color: #f59e0b;
}

.star-btn.active .star-icon path {
  fill: #f59e0b;
  stroke: #f59e0b;
}

.star-btn:hover {
  border-color: var(--color-border);
  transform: translateY(-1px);
}

.menu-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  cursor: pointer;
}

.item-menu {
  min-width: 140px;
  display: flex;
  flex-direction: column;
  padding: 6px;
}

.item-menu button {
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  padding: 0 8px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.item-menu button:hover {
  background-color: var(--color-bg-tertiary);
}

.star-menu-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.star-menu-btn .star-icon {
  width: 14px;
  height: 14px;
}

.star-menu-btn .star-icon.active path {
  fill: #f59e0b;
  stroke: #f59e0b;
}

.item-menu button.danger {
  color: var(--color-danger);
}

.rename-input {
  width: 100%;
  border: 1px solid var(--color-primary);
  border-radius: 6px;
  padding: 2px 6px;
  background-color: var(--color-bg-primary);
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: var(--spacing-md);
}

.grid-card {
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background-color: var(--color-bg-primary);
  padding: 12px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.grid-card:hover {
  box-shadow: var(--shadow-sm);
}

.grid-card.selected {
  border-color: rgba(var(--color-primary-rgb), 0.6);
  background-color: var(--color-primary-light);
}

.grid-check {
  position: absolute;
  top: 8px;
  left: 8px;
}

.grid-icon {
  width: 62px;
  height: 62px;
  object-fit: contain;
  margin-top: 8px;
}

.grid-name {
  width: 100%;
  text-align: center;
  word-break: break-word;
  min-height: 40px;
}

.grid-actions {
  align-self: flex-end;
}

.star-btn.floating {
  position: absolute;
  top: 8px;
  right: 8px;
}

@media (max-width: 900px) {
  .list-header,
  .list-row {
    grid-template-columns: 40px 1fr 90px 0;
  }

  .col.time,
  .col.actions {
    display: none;
  }
}
</style>
