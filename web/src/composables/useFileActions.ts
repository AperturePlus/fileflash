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
const TEMP_NEW_FOLDER_PREFIX = 'temp-new-folder';

function formatLocalTimestamp(date: Date): string {
  const yyyy = String(date.getFullYear());
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const mi = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${yyyy}${mm}${dd}-${hh}${mi}${ss}`;
}

export function useFileActions(currentFolderId: Ref<string | null>) {
  const fileStore = useFileStore();
  const settingsStore = useSettingsStore();
  const localeStore = useLocaleStore();
  const t = localeStore.t;
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
      if (tempId && tempId.startsWith(TEMP_NEW_FOLDER_PREFIX)) {
        fileStore.items = fileStore.items.filter((i) => i.id !== tempId);
      }
      cancelRename();
      ui.toast({ type: 'info', message: localeStore.t('files.toast.newFolderCanceled') });
    },
  });

  const registerRenameInput = (itemId: string, el: HTMLInputElement | null) => {
    if (renamingItemId.value !== itemId) return;
    renameInput.value = el;
  };

  const startRename = async (item: ContentItem) => {
    renamingItemId.value = item.id;
    renameInputValue.value = item.name;
    renameInput.value = null;
    await nextTick();
    renameInput.value?.focus();
    renameInput.value?.select();
  };

  const cancelRename = () => {
    if (renamingItemId.value && renamingItemId.value.startsWith(TEMP_NEW_FOLDER_PREFIX)) {
      fileStore.items = fileStore.items.filter((i) => i.id !== renamingItemId.value);
    }
    newFolderCancel.uninstall();
    renameInput.value = null;
    renamingItemId.value = null;
    renameInputValue.value = '';
    isRenaming.value = false;
  };

  const finishRename = async () => {
    if (!renamingItemId.value || isRenaming.value) return;
    isRenaming.value = true;

    const item = fileStore.items.find((i) => i.id === renamingItemId.value);
    if (!item) {
      cancelRename();
      return;
    }
    const newName = renameInputValue.value.trim();
    if (newName === '') {
      cancelRename();
      return;
    }
    const isTempFolder = item.id.startsWith(TEMP_NEW_FOLDER_PREFIX);
    if (!isTempFolder && newName === item.name) {
      cancelRename();
      return;
    }

    if (isTempFolder) {
      try {
        await createFolder({ folderName: newName, parentFolderId: currentFolderId.value || 'root' });
        await fileStore.fetchFolderContents(currentFolderId.value || 'root', { silent: true });
        ui.toast({
          type: 'success',
          message: t('files.rename.toast.createdFolder').replace('{folderName}', newName),
        });
      } catch (error) {
        console.error(`Failed to create folder "${newName}":`, error);
        ui.toast({ type: 'error', message: t('files.rename.toast.createFailed') });
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
      ui.toast({ type: 'success', message: t('files.rename.toast.renamed').replace('{newName}', newName) });
    } catch (error) {
      console.error(`Failed to rename ${item.name}:`, error);
      ui.toast({ type: 'error', message: t('files.rename.toast.renameFailed') });
    } finally {
      cancelRename();
      eventBus.emit('refresh-file-tree');
    }
  };

  const handleDelete = async (item: ContentItem) => {
    if (settingsStore.settings.confirmDelete) {
      const confirmed = await ui.confirm({
        title: t('files.delete.confirm.title'),
        message: t('files.delete.confirm.message').replace('{itemName}', item.name),
        confirmText: t('files.delete.confirm.confirmText'),
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
      ui.toast({ type: 'success', message: t('files.delete.toast.success').replace('{itemName}', item.name) });
    } catch (error) {
      console.error(`Failed to delete ${item.name}:`, error);
      ui.toast({ type: 'error', message: t('files.delete.toast.failed') });
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
      ui.toast({ type: 'warning', message: t('files.move.toast.noMovable') });
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
        const reason = firstError || t('files.move.reason.noneMoved');
        ui.toast({
          type: 'error',
          message: t('files.move.toast.failedNoneMoved').replace('{reason}', reason),
          duration: 4200,
        });
        return;
      }

      if (result.failed > 0) {
        const reason = firstError || t('files.move.reason.someFailed');
        ui.toast({
          type: 'warning',
          message: t('files.move.toast.partial')
            .replace('{succeeded}', String(result.succeeded))
            .replace('{processed}', String(result.processed))
            .replace('{reason}', reason),
          duration: 4200,
        });
      } else {
        ui.toast({ type: 'success', message: t('files.move.toast.success').replace('{count}', String(result.succeeded)) });
      }
    } catch (error) {
      console.error('Batch move failed:', error);
      ui.toast({ type: 'error', message: t('files.move.toast.failed') });
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
      ui.toast({ type: 'warning', message: t('files.move.toast.selectAtLeastOne') });
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
    const now = new Date();
    const baseName = `${t('files.toolbar.newFolder')}-${formatLocalTimestamp(now)}`;
    const existingNames = new Set(fileStore.items.map((item) => item.name));
    let defaultFolderName = baseName;
    let index = 2;
    while (existingNames.has(defaultFolderName)) {
      defaultFolderName = `${baseName}-${index}`;
      index += 1;
    }

    const tempId = `${TEMP_NEW_FOLDER_PREFIX}-${Date.now()}`;
    const tempFolder: FolderItem = {
      itemType: 'folder',
      id: tempId,
      name: defaultFolderName,
      size: 0,
      ownerName: t('files.owner.you'),
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
      ui.toast({ type: 'error', message: t('files.download.toast.failed') });
    }
  };

  return {
    renamingItemId,
    renameInputValue,
    registerRenameInput,
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
