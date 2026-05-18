import { ref, computed } from 'vue';

export function useFileSelection() {
  const selectedItems = ref<Set<string>>(new Set());
  const lastSelectedId = ref<string | null>(null);

  const selectedCount = computed(() => selectedItems.value.size);

  const isSelected = (itemId: string | number) =>
    selectedItems.value.has(String(itemId));

  const toggleSelection = (itemId: string | number) => {
    if (!itemId && itemId !== 0) return;
    const id = String(itemId);
    const next = new Set(selectedItems.value);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedItems.value = next;
  };

  const toggleAdd = (itemId: string | number) => {
    const id = String(itemId);
    const next = new Set(selectedItems.value);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedItems.value = next;
    lastSelectedId.value = id;
  };

  const selectRange = (toId: string, items: ReadonlyArray<{ id: string }>) => {
    if (!lastSelectedId.value) {
      toggleAdd(toId);
      return;
    }
    const fromIdx = items.findIndex((it) => it.id === lastSelectedId.value);
    const toIdx = items.findIndex((it) => it.id === toId);
    if (fromIdx === -1 || toIdx === -1) {
      toggleAdd(toId);
      return;
    }
    const [lo, hi] = fromIdx < toIdx ? [fromIdx, toIdx] : [toIdx, fromIdx];
    const next = new Set(selectedItems.value);
    for (let i = lo; i <= hi; i += 1) next.add(items[i].id);
    selectedItems.value = next;
    lastSelectedId.value = toId;
  };

  const clear = () => {
    selectedItems.value = new Set();
    lastSelectedId.value = null;
  };

  const clearSelection = clear;

  return {
    selectedItems,
    lastSelectedId,
    isSelected,
    toggleSelection,
    toggleAdd,
    selectRange,
    selectedCount,
    clear,
    clearSelection,
  };
}
