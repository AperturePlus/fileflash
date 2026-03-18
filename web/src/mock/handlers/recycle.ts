import Mock from 'mockjs';
import { vfsApi } from '../vfs';
import type { RecycleBinItem } from '../../types/file';

export const setupRecycleMocks = () => {
  // Get Recycle Bin Contents
  Mock.mock(/\/api\/v1\/recycle-bin/, 'get', () => {
    const allItems = vfsApi.getAll();
    const trashedItems: RecycleBinItem[] = Object.values(allItems)
      .filter(item => item.isTrashed)
      .map(item => {
        const path = vfsApi.getPath(item.id);
        const originalPath = path.slice(0, -1).map(p => p.name).join('/');

        const daysUntilPermanentDelete = 30 - Math.floor((Date.now() - new Date(item.deletedAt!).getTime()) / (1000 * 60 * 60 * 24));

        return {
          itemType: item.type,
          id: item.id,
          name: item.name,
          originalPath: originalPath || 'My Files',
          size: item.size || 0,
          mimeType: item.mimeType,
          deletedAt: item.deletedAt!,
          autoDeleteAt: new Date(new Date(item.deletedAt!).getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          daysUntilPermanentDelete: daysUntilPermanentDelete > 0 ? daysUntilPermanentDelete : 0,
          canRestore: true, // Mock logic, always true for now
          restoreConflicts: false, // Mock logic, always false for now
        };
      });

    return {
      success: true,
      code: 200,
      data: {
        items: trashedItems.sort((a, b) => new Date(b.deletedAt).getTime() - new Date(a.deletedAt).getTime()),
        pagination: { totalItems: trashedItems.length, totalPages: 1, perPage: trashedItems.length, currentPage: 1 },
      },
    };
  });

  // Restore Item
  Mock.mock(/\/api\/v1\/recycle-bin\/(.+)\/restore/, 'post', (options) => {
    const itemId = (options.url.match(/\/api\/v1\/recycle-bin\/(.+)\/restore/) || [])[1];
    vfsApi.restore(itemId);
    const restoredItem = vfsApi.get(itemId);
    return {
      success: true,
      code: 200,
      message: 'Item restored successfully.',
      data: {
        itemType: restoredItem?.type,
        id: restoredItem?.id,
        name: restoredItem?.name,
        restoredTo: restoredItem?.parent,
        restoredAt: new Date().toISOString(),
      },
    };
  });

  // Permanent Delete
  Mock.mock(/\/api\/v1\/recycle-bin\/(.+)/, 'delete', (options) => {
    const itemId = (options.url.match(/\/api\/v1\/recycle-bin\/(.+)/) || [])[1];
    const item = vfsApi.get(itemId);
    if (!item) {
        return { success: false, code: 404, message: 'Item not found.' };
    }
    vfsApi.permanentDelete(itemId);
    return {
        success: true,
        code: 200,
        message: 'Item permanently deleted.',
        data: {
            itemType: item.type,
            id: item.id,
            name: item.name,
            permanentlyDeletedAt: new Date().toISOString(),
        },
    };
  });
}; 