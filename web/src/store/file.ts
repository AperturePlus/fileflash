import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getFolderContents, getFolderPath } from '../api/folder';
import { useSettingsStore } from './settings';
import type { ContentItem, PathItem } from '../types/file';

export const useFileStore = defineStore('file', () => {
  const settingsStore = useSettingsStore();
  const items = ref<ContentItem[]>([]);
  const path = ref<PathItem[]>([]);
  const currentFolderId = ref<string | null>('root');
  const isLoading = ref(false);
  const selectedFile = ref<ContentItem | null>(null);

  async function fetchFolderContents(folderId: string) {
    isLoading.value = true;
    selectedFile.value = null;

    try {
      const contentsPromise = getFolderContents({
        folderId,
        perPage: settingsStore.settings.itemsPerPage,
      });
      const pathPromise = folderId === 'root' ? Promise.resolve(null) : getFolderPath(folderId);
      const [contentsResponse, pathResponse] = await Promise.all([contentsPromise, pathPromise]);

      items.value = contentsResponse.items;

      if (folderId === 'root') {
        path.value = [{ folderId: 'root', name: 'My Files' }];
      } else if (pathResponse) {
        path.value = pathResponse.pathItems.map((item) => ({
          ...item,
          name: item.folderId === 'root' ? 'My Files' : item.name,
        }));
      } else {
        path.value = [{ folderId: 'root', name: 'My Files' }];
      }

      currentFolderId.value = folderId;
    } catch (error) {
      console.error(`Failed to fetch contents for folder ${folderId}:`, error);
      items.value = [];
      path.value = [{ folderId: 'root', name: 'My Files' }];
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
        search: query,
        perPage: settingsStore.settings.itemsPerPage,
      });
      return response.items;
    } catch (error) {
      console.error(`Failed to search in folder ${folderId} with query \"${query}\":`, error);
      throw error;
    }
  }

  function removeItems(itemIds: string[]) {
    items.value = items.value.filter((item) => !itemIds.includes(item.id));
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
    removeItems,
  };
});
