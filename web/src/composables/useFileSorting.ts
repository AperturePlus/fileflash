import { ref, computed } from 'vue';
import type { Ref } from 'vue';
import type { ContentItem } from '../types/file';

type SortKey = 'name' | 'size' | 'updatedAt';
type SortDirection = 'asc' | 'desc';

export function useFileSorting(items: Ref<ContentItem[]>) {
  const sortKey = ref<SortKey>('name');
  const sortDirection = ref<SortDirection>('asc');

  const sortedItems = computed(() => {
    const sorted = [...items.value].sort((a, b) => {
      // Keep folders on top
      if (a.itemType === 'folder' && b.itemType !== 'folder') return -1;
      if (a.itemType !== 'folder' && b.itemType === 'folder') return 1;

      let compare = 0;
      if (sortKey.value === 'name') {
        compare = a.name.localeCompare(b.name);
      } else if (sortKey.value === 'size') {
        compare = (a.size || 0) - (b.size || 0);
      } else if (sortKey.value === 'updatedAt') {
        compare = new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      }
      
      return sortDirection.value === 'asc' ? compare : -compare;
    });
    return sorted;
  });

  const setSort = (key: SortKey) => {
    if (sortKey.value === key) {
      sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
    } else {
      sortKey.value = key;
      sortDirection.value = 'asc';
    }
  };

  return {
    sortKey,
    sortDirection,
    sortedItems,
    setSort,
  };
} 