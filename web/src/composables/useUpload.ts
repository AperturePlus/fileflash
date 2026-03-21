import { ref } from 'vue';
import type { Ref } from 'vue';
import { useFileStore } from '../store/file';
import { uploadFile, type UploadProgressData } from '../utils/uploader';
import { eventBus } from '../utils/eventBus';

interface UploadTask {
  id: number;
  name: string;
  progress: UploadProgressData;
}

export function useUpload(currentFolderId: Ref<string | null>) {
  const fileStore = useFileStore();
  const uploadTasks = ref<UploadTask[]>([]);
  const isDragging = ref(false);
  let dragCounter = 0;

  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault();
    dragCounter++;
    
    // Only show drag overlay for actual file drops from the OS
    if (e.dataTransfer?.types.includes('Files') && !e.dataTransfer.types.includes('application/fileflash-item-ids')) {
      isDragging.value = true;
    }
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter === 0) {
      isDragging.value = false;
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) {
      if (e.dataTransfer.types.includes('application/fileflash-item-ids')) {
        // This indicates a potential move operation, not an upload.
        e.dataTransfer.dropEffect = 'move';
      } else if (e.dataTransfer.types.includes('Files')) {
        e.dataTransfer.dropEffect = 'copy';
      } else {
        e.dataTransfer.dropEffect = 'none';
      }
    }
  };

  const doUpload = async (file: File) => {
    const taskId = Date.now() + Math.random();
    uploadTasks.value.push({
      id: taskId,
      name: file.name,
      progress: { percentage: 0, uploadedSize: 0, totalSize: file.size },
    });
    try {
      const newFile = await uploadFile({
        file,
        parentId: currentFolderId.value || 'root',
        onUploadProgress: (progressData) => {
          const task = uploadTasks.value.find(t => t.id === taskId);
          if (task) task.progress = progressData;
        },
      });

      if (newFile) {
        // Manually add the new file to the list for immediate UI update.
        // We need to map the response to the local FileItem type.
        const fileItem = {
          itemType: 'file' as const,
          id: newFile.fileId,
          name: newFile.fileName,
          size: newFile.fileSize,
          mimeType: newFile.mimeType,
          ownerName: 'You', // Placeholder
          updatedAt: newFile.createdAt,
          createdAt: newFile.createdAt,
          folderId: newFile.folderId,
          permission: 'owner' as const,
        };
        fileStore.items.unshift(fileItem);
        
        // 显示成功提示
        console.log(`文件 "${file.name}" 上传成功！`);
      } else {
        // If upload completes but no file data is returned (e.g. second upload),
        // refresh the folder to ensure consistency.
        await fileStore.fetchFolderContents(currentFolderId.value || 'root');
        console.log(`文件 "${file.name}" 上传完成！`);
      }

      eventBus.emit('refresh-file-tree');
    } catch (error) {
      console.error('Upload failed:', error);
      alert(`Upload of ${file.name} failed!`);
    } finally {
      setTimeout(() => {
        uploadTasks.value = uploadTasks.value.filter(t => t.id !== taskId);
      }, 5000);
    }
  };
  
  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    isDragging.value = false;
    dragCounter = 0;
    
    // Check for internal item drop (move)
    const sourceItemIdsJSON = e.dataTransfer?.getData('application/fileflash-item-ids');
    if (sourceItemIdsJSON) {
      const sourceItemIds = JSON.parse(sourceItemIdsJSON);
      const targetFolderId = currentFolderId.value || 'root';

      // Prevent dropping into the same folder
      const firstItem = fileStore.items.find(item => item.id === sourceItemIds[0]);
      let isDroppingInSameFolder = false;
      if (firstItem?.itemType === 'folder') {
        isDroppingInSameFolder = firstItem.parentFolderId === targetFolderId;
      } else if (firstItem?.itemType === 'file') {
        isDroppingInSameFolder = firstItem.folderId === targetFolderId;
      }
      
      if (sourceItemIds.includes(targetFolderId) || isDroppingInSameFolder) return;

      const targetFolderName = fileStore.path[fileStore.path.length - 1]?.name || 'My Files';
      
      eventBus.emit('move-items', {
        sourceItemIds,
        targetFolderId,
        targetFolderName
      });
      return;
    }
    
    // Only process actual file drops from the user's OS (upload)
    if (!e.dataTransfer?.types.includes('Files')) {
      return;
    }
    
    const files = e.dataTransfer?.files;
    if (!files || files.length === 0) return;
    
    for (const file of files) {
      doUpload(file);
    }
  };
  
  const handleFileSelect = async (event: Event) => {
    const target = event.target as HTMLInputElement;
    const files = target.files;
    if (!files || files.length === 0) return;
    for (const file of files) {
      doUpload(file);
    }
    if (target) target.value = '';
  };

  return {
    uploadTasks,
    isDragging,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleFileSelect,
  };
} 
