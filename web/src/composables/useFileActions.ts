import { nextTick, ref } from 'vue';
import type { Ref } from 'vue';
import type { ContentItem, FileItem, FolderItem } from '../types/file';
import { useFileStore } from '../store/file';
import { useSettingsStore } from '../store/settings';
import { useLocaleStore } from '../store/locale';
import { createFolder, deleteFolder, renameFolder } from '../api/folder';
import { batchFiles, deleteFile, downloadFile, renameFile } from '../api/file';
import { getShares } from '../api/share';
import { eventBus } from '../utils/eventBus';
import { ui } from '../utils/ui';
import { useNewFolderCancel } from './useNewFolderCancel';

type ShareHandling = 'keep' | 'revoke';

export function useFileActions(currentFolderId: Ref<string | null>) {
  const fileStore = useFileStore();
  const settingsStore = useSettingsStore();
  const localeStore = useLocaleStore();
  const renamingItemId = ref<string | null>(null);
  const renameInputValue = ref('');
  const renameInput = ref<HTMLInputElement | null>(null);
  const isRenaming = ref(false);

  const itemToMove = ref<ContentItem | null>(null);
  const moveSourceItemIds = ref<string[]>([]);
  const moveItemCount = ref(0);
  const moveHasActiveShare = ref(false);
  const isMoveDialogVisible = ref(false);

  const itemToShare = ref<ContentItem | null>(null);
  const isShareDialogVisible = ref(false);

  const newFolderCancel = useNewFolderCancel({
    renameInputValue,
    onCancel: () => {
      const tempId = renamingItemId.value;
      if (tempId && tempId.startsWith('temp-new-folder')) {
        fileStore.items = fileStore.items.filter((i) => i.id !== tempId);
      }
      cancelRename();
      ui.toast({ type: 'info', message: localeStore.t('files.toast.newFolderCanceled') });
    },
  });

  const startRename = async (item: ContentItem) => {
    renamingItemId.value = item.id;
    renameInputValue.value = item.name;
    await nextTick();
    renameInput.value?.focus();
  };

  const cancelRename = () => {
    if (renamingItemId.value && renamingItemId.value.startsWith('temp-new-folder')) {
      fileStore.items = fileStore.items.filter((i) => i.id !== renamingItemId.value);
    }
    newFolderCancel.uninstall();
    renamingItemId.value = null;
    renameInputValue.value = '';
    isRenaming.value = false;
  };

  const finishRename = async () => {
    if (!renamingItemId.value || isRenaming.value) return;
    isRenaming.value = true;

    const item = fileStore.items.find((i) => i.id === renamingItemId.value);
    if (!item || renameInputValue.value === item.name || renameInputValue.value.trim() === '') {
      cancelRename();
      return;
    }
    const newName = renameInputValue.value.trim();

    if (item.id.startsWith('temp-new-folder')) {
      try {
        await createFolder({ folderName: newName, parentFolderId: currentFolderId.value || 'root' });
        await fileStore.fetchFolderContents(currentFolderId.value || 'root', { silent: true });
        ui.toast({ type: 'success', message: `Created folder "${newName}".` });
      } catch (error) {
        console.error(`Failed to create folder "${newName}":`, error);
        ui.toast({ type: 'error', message: 'Folder creation failed.' });
        fileStore.items = fileStore.items.filter((i) => i.id !== item.id);
      } finally {
        cancelRename();
        eventBus.emit('refresh-file-tree');
      }
      return;
    }

    try {
      const updatedItem =
        item.itemType === 'folder'
          ? await renameFolder(item.id, { folderName: newName })
          : await renameFile(item.id, { fileName: newName });
      const index = fileStore.items.findIndex((i) => i.id === item.id);
      if (index !== -1) fileStore.items[index].name = updatedItem.name;
      ui.toast({ type: 'success', message: `Renamed to "${newName}".` });
    } catch (error) {
      console.error(`Failed to rename ${item.name}:`, error);
      ui.toast({ type: 'error', message: 'Rename failed.' });
    } finally {
      cancelRename();
      eventBus.emit('refresh-file-tree');
    }
  };

  const handleDelete = async (item: ContentItem) => {
    if (settingsStore.settings.confirmDelete) {
      const confirmed = await ui.confirm({
        title: 'Move To Trash',
        message: `Move "${item.name}" to trash?`,
        confirmText: 'Move',
        danger: true,
      });
      if (!confirmed) return;
    }

    try {
      if (item.itemType === 'folder') {
        await deleteFolder(item.id);
      } else {
        await deleteFile(item.id);
      }
      await fileStore.fetchFolderContents(fileStore.currentFolderId || 'root', { silent: true });
      eventBus.emit('refresh-file-tree');
      ui.toast({ type: 'success', message: `"${item.name}" moved to trash.` });
    } catch (error) {
      console.error(`Failed to delete ${item.name}:`, error);
      ui.toast({ type: 'error', message: 'Failed to move item to trash.' });
    }
  };

  const checkHasActiveShare = async (itemIds: string[]) => {
    if (!itemIds.length) return false;
    let page = 1;
    const perPage = 100;

    while (page <= 10) {
      const response = await getShares({ page, perPage });
      if (response.items.some((share) => itemIds.includes(share.itemInfo.id))) {
        return true;
      }
      if (!response.pagination?.hasNext) break;
      page += 1;
    }
    return false;
  };

  const executeBatchMove = async (
    sourceItemIds: string[],
    targetFolderId: string,
    shareHandling: ShareHandling = 'keep',
  ) => {
    const selected = sourceItemIds
      .map((id) => fileStore.items.find((item) => item.id === id))
      .filter((item): item is ContentItem => Boolean(item));

    const knownIds = new Set(selected.map((item) => item.id));
    const unknownIds = sourceItemIds.filter((id) => !knownIds.has(id));
    const fileIds = selected.filter((item) => item.itemType === 'file').map((item) => item.id);
    const folderIds = [
      ...selected.filter((item) => item.itemType === 'folder').map((item) => item.id),
      ...unknownIds,
    ];

    if (!fileIds.length && !folderIds.length) {
      ui.toast({ type: 'warning', message: 'No movable items found.' });
      return;
    }

    try {
      const result = await batchFiles({
        action: 'move',
        fileIds,
        folderIds,
        targetFolderId,
        shareHandling,
      });

      await fileStore.fetchFolderContents(currentFolderId.value || 'root', { silent: true });
      eventBus.emit('refresh-file-tree');

      const firstError = result.results.find((item) => !item.success)?.message;
      if (result.succeeded === 0) {
        ui.toast({
          type: 'error',
          message: `Move failed. ${firstError || 'No items were moved.'}`,
          duration: 4200,
        });
        return;
      }

      if (result.failed > 0) {
        ui.toast({
          type: 'warning',
          message: `Moved ${result.succeeded}/${result.processed}. ${firstError || 'Some items failed.'}`,
          duration: 4200,
        });
      } else {
        ui.toast({ type: 'success', message: `Moved ${result.succeeded} item(s).` });
      }
    } catch (error) {
      console.error('Batch move failed:', error);
      ui.toast({ type: 'error', message: 'Batch move failed.' });
    }
  };

  const handleBatchMove = async (
    sourceItemIds: string[],
    targetFolderId: string,
    shareHandling: ShareHandling = 'keep',
  ) => {
    await executeBatchMove(sourceItemIds, targetFolderId, shareHandling);
  };

  const openMoveDialog = async (sourceItems: ContentItem[]) => {
    moveSourceItemIds.value = sourceItems.map((item) => item.id);
    moveItemCount.value = sourceItems.length;
    itemToMove.value = sourceItems.length === 1 ? sourceItems[0] : null;
    moveHasActiveShare.value = await checkHasActiveShare(moveSourceItemIds.value);
    isMoveDialogVisible.value = true;
  };

  const startMove = async (item: ContentItem) => {
    await openMoveDialog([item]);
  };

  const startMoveForSelection = async (sourceItemIds: string[]) => {
    const sourceItems = fileStore.items.filter((item) => sourceItemIds.includes(item.id));
    if (!sourceItems.length) {
      ui.toast({ type: 'warning', message: 'Please select at least one item.' });
      return;
    }
    await openMoveDialog(sourceItems);
  };

  const closeMoveDialog = () => {
    isMoveDialogVisible.value = false;
    itemToMove.value = null;
    moveSourceItemIds.value = [];
    moveItemCount.value = 0;
    moveHasActiveShare.value = false;
  };

  const handleMoveConfirm = async (payload: { targetFolderId: string; shareHandling: ShareHandling }) => {
    if (!moveSourceItemIds.value.length) return;

    await executeBatchMove(moveSourceItemIds.value, payload.targetFolderId, payload.shareHandling || 'keep');
    closeMoveDialog();
  };

  const handleCreateFolder = () => {
    const tempId = `temp-new-folder-${Date.now()}`;
    const tempFolder: FolderItem = {
      itemType: 'folder',
      id: tempId,
      name: '',
      size: 0,
      ownerName: 'You',
      updatedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      parentFolderId: currentFolderId.value,
      permission: 'owner',
    };
    fileStore.items.unshift(tempFolder);
    startRename(tempFolder);
    newFolderCancel.install(tempId);
  };

  const startShare = (item: ContentItem) => {
    itemToShare.value = item;
    isShareDialogVisible.value = true;
  };

  const handleDownload = async (file: FileItem) => {
    try {
      const blob = await downloadFile(file.id);
      if (!(blob instanceof Blob)) {
        throw new TypeError('Downloaded data is not a valid file (blob).');
      }
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(`Failed to download file ${file.name}:`, error);
      ui.toast({ type: 'error', message: 'Download failed.' });
    }
  };

  return {
    renamingItemId,
    renameInputValue,
    renameInput,
    itemToMove,
    moveItemCount,
    moveHasActiveShare,
    isMoveDialogVisible,
    itemToShare,
    isShareDialogVisible,
    startRename,
    cancelRename,
    finishRename,
    handleDelete,
    handleCreateFolder,
    handleBatchMove,
    startMove,
    startMoveForSelection,
    closeMoveDialog,
    handleMoveConfirm,
    startShare,
    handleDownload,
  };
}
