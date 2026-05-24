import { ref } from 'vue';
import type { Ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useFileStore } from '../store/file';
import { useLocaleStore } from '../store/locale';
import { useUploadStore } from '../store/upload';
import { eventBus } from '../utils/eventBus';

export function useUpload(currentFolderId: Ref<string | null>) {
  const fileStore = useFileStore();
  const uploadStore = useUploadStore();
  const localeStore = useLocaleStore();
  const t = localeStore.t;
  const { tasks: uploadTasks } = storeToRefs(uploadStore);

  const isDragging = ref(false);
  let dragCounter = 0;

  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault();
    dragCounter += 1;
    if (e.dataTransfer?.types.includes('Files') && !e.dataTransfer.types.includes('application/fileflash-item-ids')) {
      isDragging.value = true;
    }
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    dragCounter -= 1;
    if (dragCounter <= 0) {
      dragCounter = 0;
      isDragging.value = false;
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (!e.dataTransfer) return;
    if (e.dataTransfer.types.includes('application/fileflash-item-ids')) {
      e.dataTransfer.dropEffect = 'move';
      return;
    }
    if (e.dataTransfer.types.includes('Files')) {
      e.dataTransfer.dropEffect = 'copy';
      return;
    }
    e.dataTransfer.dropEffect = 'none';
  };

  const enqueueUpload = async (file: File) => {
    await uploadStore.startUpload(file, currentFolderId.value || 'root');
  };

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    isDragging.value = false;
    dragCounter = 0;

    const sourceItemIdsJSON = e.dataTransfer?.getData('application/fileflash-item-ids');
    if (sourceItemIdsJSON) {
      if (e.target !== e.currentTarget) return;

      let sourceItemIds: string[] = [];
      try {
        const parsed = JSON.parse(sourceItemIdsJSON);
        sourceItemIds = Array.isArray(parsed) ? parsed.map((id) => String(id)) : [];
      } catch (error) {
        console.warn('Invalid internal drag payload:', error);
        return;
      }
      if (!sourceItemIds.length) return;

      const targetFolderId = currentFolderId.value || 'root';
      const firstItem = fileStore.items.find((item) => item.id === sourceItemIds[0]);
      let isDroppingInSameFolder = false;
      if (firstItem?.itemType === 'folder') {
        isDroppingInSameFolder = firstItem.parentFolderId === targetFolderId;
      } else if (firstItem?.itemType === 'file') {
        isDroppingInSameFolder = firstItem.folderId === targetFolderId;
      }
      if (sourceItemIds.includes(targetFolderId) || isDroppingInSameFolder) return;

      const targetFolderName = fileStore.path[fileStore.path.length - 1]?.name || t('files.root.myFiles');
      eventBus.emit('move-items', { sourceItemIds, targetFolderId, targetFolderName });
      return;
    }

    if (!e.dataTransfer?.types.includes('Files')) return;
    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;
    for (const file of files) {
      await enqueueUpload(file);
    }
  };

  const handleFileSelect = async (event: Event) => {
    const target = event.target as HTMLInputElement;
    const files = target.files;
    if (!files || files.length === 0) return;
    for (const file of files) {
      await enqueueUpload(file);
    }
    target.value = '';
  };

  const cancelUpload = async (taskId: string | number) => {
    await uploadStore.cancelTask(String(taskId));
  };

  return {
    uploadTasks,
    isDragging,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleFileSelect,
    cancelUpload,
  };
}
