import type { Ref } from 'vue';
import { batchFiles, batchDownloadFiles } from '../api/file';
import { useFileStore } from '../store/file';

/**
 * Batch actions for the file store
 * @param selectedItems - The selected items
 * @param clearSelection - The function to clear the selection
 * @returns The batch actions
 */
export function useBatchActions(
  selectedItems: Ref<Set<string>>,
  clearSelection: () => void
) {
  const fileStore = useFileStore();

  const handleBatchDownload = async () => {
    if (selectedItems.value.size === 0) return;
    const idsToDownload = Array.from(selectedItems.value);
    
    console.log('开始批量下载，文件IDs:', idsToDownload);
    
    try {
      const blob = await batchDownloadFiles(idsToDownload);
      
      // Debug: Check if we actually got a blob
      console.log('Download response type:', typeof blob);
      console.log('Is Blob?', blob instanceof Blob);
      console.log('Blob size:', blob?.size);
      
      if (!(blob instanceof Blob)) {
        throw new Error('Response is not a valid Blob');
      }
      
      if (blob.size === 0) {
        throw new Error('Downloaded file is empty');
      }
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fileflash-Download-${new Date().toISOString().slice(0,10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      clearSelection();
      
      console.log(`✅ 成功下载 ${idsToDownload.length} 个文件`);
    } catch (error) {
      console.error('Batch download failed:', error);
      
      // 根据错误类型给出更具体的提示
      let errorMessage = 'Failed to download selected files.';
      if (error instanceof Error) {
        if (error.message.includes('500')) {
          errorMessage = '服务器内部错误，批量下载功能暂时不可用。请尝试单独下载文件。';
        } else if (error.message.includes('404')) {
          errorMessage = '部分文件不存在，无法完成批量下载。';
        } else if (error.message.includes('Network Error')) {
          errorMessage = '网络连接错误，请检查网络后重试。';
        }
      }
      
      alert(errorMessage);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedItems.value.size === 0) {
      console.warn('No items selected for deletion');
      return;
    }
    
    if (!confirm(`Are you sure you want to move ${selectedItems.value.size} items to the trash?`)) {
      return;
    }
    
    const idsToDelete = Array.from(selectedItems.value);
    console.log('开始批量删除，文件IDs:', idsToDelete);
    console.log('Current fileStore items before delete:', fileStore.items.map(item => ({ id: item.id, name: item.name })));
    
    try {
      // 发送删除请求
      const result = await batchFiles({ action: 'delete', fileIds: idsToDelete });
      console.log('批量删除API响应:', result);
      
      // 验证API响应是否表示成功
      if (result) {
        console.log(`API返回成功删除了项目`);

        // 清除选择状态
        clearSelection();
        
        // 重新获取当前目录的内容以确保同步
        console.log('重新获取当前目录内容...');
        await fileStore.fetchFolderContents(fileStore.currentFolderId || 'root');
        
        console.log(`✅ 成功删除 ${idsToDelete.length} 个项目，已刷新目录`);
        // 可选：显示成功提示
        // alert(`Successfully moved ${idsToDelete.length} item(s) to trash.`);
      } else {
        console.error('API返回的结果表明删除失败:', result);
        throw new Error('Delete operation failed on server');
      }
      
    } catch (error) {
      console.error('Batch delete failed:', error);
      console.error('Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
        response: (error as any)?.response?.data
      });
      
      // 根据错误类型给出更具体的提示
      let errorMessage = 'Failed to move selected items to trash.';
      if (error instanceof Error) {
        if (error.message.includes('500')) {
          errorMessage = '服务器内部错误，删除失败。请稍后重试。';
        } else if (error.message.includes('404')) {
          errorMessage = '部分文件不存在，无法完成删除操作。';
        } else if (error.message.includes('403')) {
          errorMessage = '没有权限删除部分文件。';
        }
      }
      
      alert(errorMessage);
    }
  };

  return {
    handleBatchDownload,
    handleBatchDelete,
  };
} 