import { ref, computed } from 'vue';

/**
 * File selection for the file store
 * @returns The file selection
 */
export function useFileSelection() {
  const selectedItems = ref<Set<string>>(new Set());

  const isSelected = (itemId: string | number) => {
    const stringId = String(itemId);
    return selectedItems.value.has(stringId);
  };

  const toggleSelection = (itemId: string | number) => {
    // 将 itemId 转换为字符串以确保一致性
    const stringId = String(itemId);
    
    // 确保 itemId 是有效的
    if (!itemId && itemId !== 0) {
      console.error('Invalid itemId passed to toggleSelection:', itemId);
      return;
    }
    
    // 创建新的 Set 来确保响应式更新
    const newSelectedItems = new Set(selectedItems.value);
    
    if (newSelectedItems.has(stringId)) {
      newSelectedItems.delete(stringId);
    } else {
      newSelectedItems.add(stringId);
    }
    
    selectedItems.value = newSelectedItems;
  };

  const selectedCount = computed(() => selectedItems.value.size);

  const clearSelection = () => {
    console.log('Clearing selection, current size:', selectedItems.value.size);
    // 创建新的空 Set 确保响应式更新
    selectedItems.value = new Set();
    console.log('Selection cleared, new size:', selectedItems.value.size);
  };

  return {
    selectedItems,
    isSelected,
    toggleSelection,
    selectedCount,
    clearSelection,
  };
} 