import type { Ref } from 'vue';
import { batchDownloadFiles, batchFiles } from '../api/file';
import { useFileStore } from '../store/file';
import { ui } from '../utils/ui';

export function useBatchActions(
  selectedItems: Ref<Set<string>>,
  clearSelection: () => void,
) {
  const fileStore = useFileStore();

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
      ui.toast({ type: 'success', message: `Downloaded ${selected.length} item(s).` });
    } catch (error) {
      console.error('Batch download failed:', error);
      ui.toast({
        type: 'error',
        message: 'Failed to download selected files.',
        duration: 4200,
      });
    }
  };

  const handleBatchDelete = async () => {
    if (selectedItems.value.size === 0) return;

    const confirmed = await ui.confirm({
      title: 'Move To Trash',
      message: `Move ${selectedItems.value.size} selected item(s) to trash?`,
      confirmText: 'Move',
      danger: true,
    });
    if (!confirmed) return;

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
      await fileStore.fetchFolderContents(fileStore.currentFolderId || 'root');
      ui.toast({ type: 'success', message: `Moved ${idsToDelete.length} item(s) to trash.` });
    } catch (error) {
      console.error('Batch delete failed:', error);
      ui.toast({
        type: 'error',
        message: 'Failed to move selected items to trash.',
        duration: 4200,
      });
    }
  };

  return {
    handleBatchDownload,
    handleBatchDelete,
  };
}
