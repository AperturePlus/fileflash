import { ref, nextTick } from 'vue';
import type { Ref } from 'vue';
import type { ContentItem, FileItem, FolderItem } from '../types/file';
import { useFileStore } from '../store/file';
import { renameFolder, deleteFolder, moveFolder, createFolder } from '../api/folder';
import { renameFile, deleteFile, moveFile, downloadFile, batchFiles } from '../api/file';
import { eventBus } from '../utils/eventBus';

/**
 * File actions for the file store
 * @param currentFolderId - The current folder id
 * @returns The file actions
 */
export function useFileActions(currentFolderId: Ref<string | null>) {
  const fileStore = useFileStore();
  const renamingItemId = ref<string | null>(null);
  const renameInputValue = ref('');
  const renameInput = ref<HTMLInputElement | null>(null);
  const isRenaming = ref(false); // 添加标志防止重复调用

  const itemToMove = ref<ContentItem | null>(null);
  const isMoveDialogVisible = ref(false);
  const itemToShare = ref<ContentItem | null>(null);
  const isShareDialogVisible = ref(false);

  const startRename = async (item: ContentItem) => {
    renamingItemId.value = item.id;
    renameInputValue.value = item.name;
    await nextTick();
    renameInput.value?.focus();
  };

  const cancelRename = () => {
    if (renamingItemId.value && renamingItemId.value.startsWith('temp-new-folder')) {
      fileStore.items = fileStore.items.filter(i => i.id !== renamingItemId.value);
    }
    renamingItemId.value = null;
    renameInputValue.value = '';
    isRenaming.value = false; // 重置标志
  };

  const finishRename = async () => {
    // 防止重复调用
    if (!renamingItemId.value || isRenaming.value) return;
    isRenaming.value = true;
    
    const item = fileStore.items.find(i => i.id === renamingItemId.value);
    if (!item || renameInputValue.value === item.name || renameInputValue.value.trim() === '') {
      cancelRename();
      return;
    }
    const newName = renameInputValue.value.trim();

    // If this is a temporary new folder, create it on the backend
    if (item.id.startsWith('temp-new-folder')) {
      try {
        await createFolder({ folderName: newName, parentFolderId: currentFolderId.value || 'root' });
        // 创建成功后立即刷新文件夹内容以显示新创建的文件夹
        await fileStore.fetchFolderContents(currentFolderId.value || 'root');
      } catch (error) {
         console.error(`Failed to create folder "${newName}":`, error);
        alert('Folder creation failed!');
        // Remove the temporary item on failure
        fileStore.items = fileStore.items.filter(i => i.id !== item.id);
      } finally {
        cancelRename();
        eventBus.emit('refresh-file-tree');
      }
      return;
    }

    try {
      const updatedItem = item.itemType === 'folder'
        ? await renameFolder(item.id, { folderName: newName })
        : await renameFile(item.id, { fileName: newName });
      const index = fileStore.items.findIndex(i => i.id === item.id);
      if (index !== -1) fileStore.items[index].name = updatedItem.name;
    } catch (error) {
      console.error(`Failed to rename ${item.name}:`, error);
      alert('Rename failed!');
    } finally {
      cancelRename();
      eventBus.emit('refresh-file-tree');
    }
  };
  
  const handleDelete = async (item: ContentItem) => {
    if (!confirm(`Are you sure you want to move "${item.name}" to the trash?`)) return;
    try {
      if (item.itemType === 'folder') {
        await deleteFolder(item.id);
      } else {
        await deleteFile(item.id);
      }
      
      // 重新获取当前目录的内容以确保同步
      await fileStore.fetchFolderContents(fileStore.currentFolderId || 'root');
      eventBus.emit('refresh-file-tree');
      
      console.log(`✅ 成功删除 "${item.name}"，已刷新目录`);
    } catch (error) {
      console.error(`Failed to delete ${item.name}:`, error);
      alert('Failed to move to trash!');
    }
  };

  const handleBatchMove = async (sourceItemIds: string[], targetFolderId: string) => {
    const filesToMove = fileStore.items.filter(i => sourceItemIds.includes(i.id));
    const fileIds = filesToMove.filter(i => i.itemType === 'file').map(i => i.id);
    const folderIds = filesToMove.filter(i => i.itemType === 'folder').map(i => i.id);

    try {
      const movePromises = [];
      // Batch move files if any
      if (fileIds.length > 0) {
        movePromises.push(batchFiles({ action: 'move', fileIds, targetFolderId }));
      }
      // Move folders one by one
      for (const folderId of folderIds) {
        movePromises.push(moveFolder(folderId, { targetParentId: targetFolderId }));
      }

      await Promise.all(movePromises);
    } catch (error) {
      console.error('Batch move failed:', error);
      alert('Failed to move some items.');
    } finally {
      // Refresh the view after the move
      fileStore.fetchFolderContents(currentFolderId.value || 'root');
      eventBus.emit('refresh-file-tree');
    }
  };

  const handleCreateFolder = () => {
    // Create a temporary folder object
    const tempId = `temp-new-folder-${Date.now()}`;
    const tempFolder: FolderItem = {
      itemType: 'folder',
      id: tempId,
      name: '', // Initially empty
      size: 0,
      ownerName: 'You', // Or get from user store
      updatedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      parentFolderId: currentFolderId.value,
      permission: 'owner',
    };
    // Add it to the list and immediately start renaming
    fileStore.items.unshift(tempFolder);
    startRename(tempFolder);
  };

  const startMove = (item: ContentItem) => {
    itemToMove.value = item;
    isMoveDialogVisible.value = true;
  };

  const closeMoveDialog = () => {
    isMoveDialogVisible.value = false;
    itemToMove.value = null;
  };

  const handleMoveConfirm = async (targetFolderId: string) => {
    const itemToMoveVal = itemToMove.value;
    if (!itemToMoveVal) return;

    try {
      if (itemToMoveVal.itemType === 'folder') {
        await moveFolder(itemToMoveVal.id, { targetParentId: targetFolderId });
      } else {
        await moveFile(itemToMoveVal.id, { targetFolderId: targetFolderId });
      }
      fileStore.fetchFolderContents(currentFolderId.value || 'root');
      alert('Item moved successfully!');
    } catch (error) {
      console.error(`Failed to move ${itemToMoveVal.name}:`, error);
      alert('Move failed!');
    } finally {
      closeMoveDialog();
      eventBus.emit('refresh-file-tree');
    }
  };

  const startShare = (item: ContentItem) => {
    itemToShare.value = item;
    isShareDialogVisible.value = true;
  };
  
  const handleDownload = async (file: FileItem) => {
    try {
      const blob = await downloadFile(file.id);
      if (!(blob instanceof Blob)) {
        throw new TypeError("Downloaded data is not a valid file (blob).");
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
      alert('Download failed!');
    }
  };

  return {
    renamingItemId,
    renameInputValue,
    renameInput,
    itemToMove,
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
    closeMoveDialog,
    handleMoveConfirm,
    startShare,
    handleDownload,
  };
} 