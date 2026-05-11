<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue';
import FileDetailPanel from './FileDetailPanel.vue';
import { useLocaleStore } from '../../../store/locale';
import type { FileItem } from '../../../types/file';

const props = defineProps<{ file: FileItem | null }>();
const emit = defineEmits<{ (e: 'close'): void }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const isOpen = computed(() => props.file !== null);

const onKey = (ev: KeyboardEvent) => {
  if (ev.key === 'Escape' && isOpen.value) {
    ev.stopPropagation();
    emit('close');
  }
};

onMounted(() => {
  document.addEventListener('keydown', onKey);
});
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey);
});

const onOverlayClick = (ev: MouseEvent) => {
  if (ev.target === ev.currentTarget) emit('close');
};
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="file-preview-dialog__overlay"
      role="presentation"
      @click="onOverlayClick"
    >
      <div
        class="file-preview-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="t('files.preview.title')"
        tabindex="-1"
      >
        <button
          class="file-preview-dialog__close"
          :aria-label="t('files.preview.close')"
          @click="emit('close')"
        >
          &times;
        </button>
        <div class="file-preview-dialog__body">
          <FileDetailPanel :file="file" @close="emit('close')" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.file-preview-dialog__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.file-preview-dialog {
  position: relative;
  width: min(1200px, 92vw);
  height: min(800px, 90vh);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  outline: none;
}
.file-preview-dialog__close {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  z-index: 1;
}
.file-preview-dialog__close:hover {
  background: var(--surface-inset);
  color: var(--text-primary);
}
.file-preview-dialog__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}
.file-preview-dialog__body :deep(.detail) {
  flex: 1;
  min-height: 0;
}
</style>
