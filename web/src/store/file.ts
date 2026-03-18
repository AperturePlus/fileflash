import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getFolderContents, getFolderPath } from '../api/folder';
import type { ContentItem, PathItem } from '../types/file';

export const useFileStore = defineStore('file', () => {
  const items = ref<ContentItem[]>([]);
  const path = ref<PathItem[]>([]);
  const currentFolderId = ref<string | null>('root');
  const isLoading = ref(false);
  const selectedFile = ref<ContentItem | null>(null);

  async function fetchFolderContents(folderId: string) {
    isLoading.value = true;
    selectedFile.value = null; // Reset selection when navigating
    try {
      console.log(`正在获取文件夹内容: ${folderId}`);
      
      // Fetch folder contents and path concurrently
      const [contentsResponse, pathResponse] = await Promise.all([
        getFolderContents({ folderId }),
        getFolderPath(folderId),
      ]);
      
      console.log('Contents response:', contentsResponse);
      console.log('Path response:', pathResponse);
      
      // Validate responses - 更宽松的验证
      if (!contentsResponse) {
        throw new Error(`No contents response for folder ${folderId}`);
      }
      if (!pathResponse) {
        throw new Error(`No path response for folder ${folderId}`);
      }
      
      // 检查数据结构并适配 - 更灵活的数据提取
      let responseItems = [];
      let pathItems = [];
      
      // 尝试多种可能的数据结构
      if (contentsResponse.items) {
        responseItems = contentsResponse.items;
      } else if (contentsResponse.data) {
        responseItems = contentsResponse.data;
      } else if (Array.isArray(contentsResponse)) {
        responseItems = contentsResponse;
      }
      
      // 处理路径数据
      if (Array.isArray(pathResponse)) {
        pathItems = pathResponse;
      } else if (pathResponse.pathItems) {
        pathItems = pathResponse.pathItems;
      } else if (pathResponse.data) {
        pathItems = pathResponse.data;
      }
      
      console.log('Processed items:', responseItems);
      console.log('Processed path:', pathItems);
      
      // 如果是根文件夹，确保路径显示为 "My Files"
      if (folderId === 'root') {
        pathItems = [
          {
            folderId: 'root',
            name: 'My Files'
          }
        ];
      } else {
        // 处理其他路径，替换任何 root 为 "My Files"
        pathItems = pathItems.map((pathItem: any) => ({
          ...pathItem,
          name: pathItem.name === 'root' ? 'My Files' : pathItem.name
        }));
      }

      // Set store state
      items.value = responseItems;
      path.value = pathItems;
      currentFolderId.value = folderId;

    } catch (error) {
      console.error(`Failed to fetch contents for folder ${folderId}:`, error);
      // Handle error, maybe show a notification to the user
    } finally {
      isLoading.value = false;
    }
  }

  function navigateToFolder(folderId: string) {
    fetchFolderContents(folderId);
  }

  async function searchInFolder(folderId: string, query: string): Promise<ContentItem[]> {
    try {
      const response = await getFolderContents({ 
        folderId, 
        search: query 
      });
      
      let actualItems = response.items;

      // 特殊处理 root 文件夹的情况 - 与其他地方保持一致
      if (folderId === 'root' && actualItems.length === 1 && actualItems[0].name === 'root' && actualItems[0].itemType === 'folder') {
        const rootFolderId = actualItems[0].id.toString();
        const rootSearchResponse = await getFolderContents({ 
          folderId: rootFolderId, 
          search: query 
        });
        actualItems = rootSearchResponse.items;
      }

      return actualItems;
    } catch (error) {
      console.error(`Failed to search in folder ${folderId} with query "${query}":`, error);
      throw error;
    }
  }

  function removeItems(itemIds: string[]) {
    console.log('removeItems called with:', itemIds);
    console.log('Current items before filter:', items.value.map(item => ({ id: item.id, name: item.name })));
    
    // 从当前文件夹中移除指定的项目
    const itemsBefore = items.value.length;
    items.value = items.value.filter(item => {
      const shouldKeep = !itemIds.includes(item.id);
      if (!shouldKeep) {
        console.log(`Removing item: ${item.id} (${item.name})`);
      }
      return shouldKeep;
    });
    
    const itemsAfter = items.value.length;
    console.log(`Items count: ${itemsBefore} -> ${itemsAfter} (removed ${itemsBefore - itemsAfter})`);
    console.log('Remaining items:', items.value.map(item => ({ id: item.id, name: item.name })));
  }

  return {
    items,
    path,
    currentFolderId,
    isLoading,
    selectedFile,
    fetchFolderContents,
    navigateToFolder,
    searchInFolder,
    removeItems, // 添加新的删除方法
  };
}); 