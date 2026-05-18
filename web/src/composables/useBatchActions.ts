import type { Ref } from 'vue';
import { batchDownloadFiles, batchFiles } from '../api/file';
import { useFileStore } from '../store/file';
import { useLocaleStore } from '../store/locale';
import { useSettingsStore } from '../store/settings';
import { ui } from '../utils/ui';

export function useBatchActions(
  selectedItems: Ref<Set<string>>,
  clearSelection: () => void,
) {
  const fileStore = useFileStore();
  const settingsStore = useSettingsStore();
  const localeStore = useLocaleStore();
  const t = localeStore.t;

  const handleBatchDownload = async () => {
    if (selectedItems.value.size === 0) return;
    const selected = Array.from(selectedItems.value)
      .map((id) => fileStore.items.find((item) => item.id === id))
      .filter((item): item is NonNullable<typeof item> => Boolean(item));
    const fileIds = selected.filter((item) => item.itemType === 'file').map((item) => item.id);
    const folderIds = selected.filter((item) => item.itemType === 'folder').map((item) => item.id);

    try {
      const blob = await batchDownloadFiles({ fileIds, folderIds });
      if (!(blob instanceof Blob)) {
        throw new Error('Response is not a valid Blob');
      }
      if (blob.size === 0) {
        throw new Error('Downloaded file is empty');
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fileflash-Download-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      clearSelection();
      ui.toast({
        type: 'success',
        message: t('files.batch.download.toast.success').replace('{count}', String(selected.length)),
      });
    } catch (error) {
      console.error('Batch download failed:', error);
      ui.toast({
        type: 'error',
        message: t('files.batch.download.toast.failed'),
        duration: 4200,
      });
    }
  };

  const handleBatchDelete = async () => {
    if (selectedItems.value.size === 0) return;

    if (settingsStore.settings.confirmDelete) {
      const confirmed = await ui.confirm({
        title: t('files.batch.delete.confirm.title'),
        message: t('files.batch.delete.confirm.message').replace('{count}', String(selectedItems.value.size)),
        confirmText: t('files.batch.delete.confirm.confirmText'),
        danger: true,
      });
      if (!confirmed) return;
    }

    const idsToDelete = Array.from(selectedItems.value);
    const selected = idsToDelete
      .map((id) => fileStore.items.find((item) => item.id === id))
      .filter((item): item is NonNullable<typeof item> => Boolean(item));
    const fileIds = selected.filter((item) => item.itemType === 'file').map((item) => item.id);
    const folderIds = selected.filter((item) => item.itemType === 'folder').map((item) => item.id);
    try {
      const result = await batchFiles({ action: 'delete', fileIds, folderIds });
      if (!result) throw new Error('Delete failed');
      clearSelection();
      await fileStore.fetchFolderContents(fileStore.currentFolderId || 'root', { silent: true });
      ui.toast({
        type: 'success',
        message: t('files.batch.delete.toast.success').replace('{count}', String(idsToDelete.length)),
      });
    } catch (error) {
      console.error('Batch delete failed:', error);
      ui.toast({
        type: 'error',
        message: t('files.batch.delete.toast.failed'),
        duration: 4200,
      });
    }
  };

  return {
    handleBatchDownload,
    handleBatchDelete,
  };
}
