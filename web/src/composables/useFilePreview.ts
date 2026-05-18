import { nextTick, onUnmounted, ref } from 'vue';
import type { FileItem } from '../types/file';

export function useFilePreview() {
  const previewFile = ref<FileItem | null>(null);
  let lastTrigger: HTMLElement | null = null;

  const lockBodyScroll = () => {
    document.body.style.overflow = 'hidden';
  };
  const unlockBodyScroll = () => {
    document.body.style.overflow = '';
  };

  const openPreview = async (file: FileItem) => {
    const active = document.activeElement;
    lastTrigger = active instanceof HTMLElement ? active : null;
    previewFile.value = null;
    await nextTick();
    previewFile.value = file;
    lockBodyScroll();
  };

  const closePreview = () => {
    previewFile.value = null;
    unlockBodyScroll();
    const trigger = lastTrigger;
    lastTrigger = null;
    if (trigger && typeof trigger.focus === 'function') {
      trigger.focus();
    }
  };

  onUnmounted(() => {
    unlockBodyScroll();
    lastTrigger = null;
  });

  return { previewFile, openPreview, closePreview };
}
