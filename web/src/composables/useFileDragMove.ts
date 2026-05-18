import type { Ref } from 'vue';
import type { ContentItem, FolderItem } from '../types/file';
import { ui } from '../utils/ui';

interface Options {
  isSelected: (id: string) => boolean;
  selectedItems: Ref<Set<string>>;
  handleBatchMove: (sourceIds: string[], targetFolderId: string, shareHandling: 'keep' | 'revoke') => void;
}

export function useFileDragMove({ isSelected, selectedItems, handleBatchMove }: Options) {
  const confirm = (sourceIds: string[], targetFolderId: string, message: string) =>
    ui.confirm({ title: 'Move Items', message, confirmText: 'Move' })
      .then((ok) => ok && handleBatchMove(sourceIds, targetFolderId, 'keep'));

  const onDragItemStart = ({ event, item }: { event: DragEvent; item: ContentItem }) => {
    if (!event.dataTransfer) return;
    const ids = isSelected(item.id) ? Array.from(selectedItems.value) : [item.id];
    event.dataTransfer.setData('application/fileflash-item-ids', JSON.stringify(ids));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onFolderDrop = ({ event, folder }: { event: DragEvent; folder: FolderItem }) => {
    event.preventDefault();
    const raw = event.dataTransfer?.getData('application/fileflash-item-ids');
    if (!raw) return;
    const sourceIds: string[] = JSON.parse(raw);
    if (sourceIds.includes(folder.id)) return;
    confirm(sourceIds, folder.id, `Move ${sourceIds.length} item(s) into "${folder.name}"?`);
  };

  const onBreadcrumbDrop = ({ sourceItemIds, targetFolderId }: { sourceItemIds: string[]; targetFolderId: string }) =>
    confirm(sourceItemIds, targetFolderId, `Move ${sourceItemIds.length} item(s) to this folder?`);

  const onSidebarMove = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[]; targetFolderId: string; targetFolderName: string }) =>
    confirm(sourceItemIds, targetFolderId, `Move ${sourceItemIds.length} item(s) to "${targetFolderName}"?`);

  return { onDragItemStart, onFolderDrop, onBreadcrumbDrop, onSidebarMove };
}
