import Mock from 'mockjs';
import type { RecycleBinItem } from '../../types/file';
import { addLog } from '../state';
import { vfsApi } from '../vfs';

function buildPagination(count: number) {
  return {
    totalItems: count,
    totalPages: 1,
    perPage: count,
    currentPage: 1,
    hasPrev: false,
    hasNext: false,
  };
}

export const setupRecycleMocks = () => {
  Mock.mock(/\/api\/v1\/recycle-bin$/, 'get', () => {
    const all = Object.values(vfsApi.getAll());

    const trashedItems: RecycleBinItem[] = all
      .filter((node) => node.isTrashed)
      .map((node) => {
        const path = vfsApi.getPath(node.id);
        const originalPath = path.slice(0, -1).map((item) => item.name).join('/') || 'My Files';
        const deletedAt = node.deletedAt || new Date().toISOString();
        const expireAt = new Date(new Date(deletedAt).getTime() + 30 * 24 * 60 * 60 * 1000);
        const daysUntilPermanentDelete = Math.max(
          0,
          Math.ceil((expireAt.getTime() - Date.now()) / (24 * 60 * 60 * 1000)),
        );

        return {
          itemType: node.type,
          id: node.id,
          name: node.name,
          originalPath,
          size: node.size || 0,
          mimeType: node.mimeType,
          deletedAt,
          autoDeleteAt: expireAt.toISOString(),
          daysUntilPermanentDelete,
          canRestore: true,
          restoreConflicts: false,
        };
      })
      .sort((a, b) => new Date(b.deletedAt).getTime() - new Date(a.deletedAt).getTime());

    return {
      success: true,
      code: 200,
      data: {
        items: trashedItems,
        pagination: buildPagination(trashedItems.length),
      },
    };
  });

  Mock.mock(/\/api\/v1\/recycle-bin\/([^/]+)\/restore$/, 'post', (options) => {
    const itemId = (options.url.match(/\/api\/v1\/recycle-bin\/([^/]+)\/restore/) || [])[1];
    const node = vfsApi.get(itemId);

    if (!node) {
      return {
        success: false,
        code: 404,
        message: 'Item not found',
        data: null,
      };
    }

    vfsApi.restore(itemId);
    addLog('recycle_restore', { itemId, itemName: node.name });

    return {
      success: true,
      code: 200,
      message: 'Item restored successfully',
      data: {
        itemType: node.type,
        id: node.id,
        name: node.name,
        restoredTo: node.parent,
        restoredAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/recycle-bin\/([^/]+)$/, 'delete', (options) => {
    const itemId = (options.url.match(/\/api\/v1\/recycle-bin\/([^/?]+)/) || [])[1];
    const url = new URL(options.url, 'http://localhost');
    const itemType = url.searchParams.get('itemType');
    const node = vfsApi.get(itemId);

    if (!node) {
      return {
        success: false,
        code: 404,
        message: 'Item not found',
        data: null,
      };
    }
    if (itemType && itemType !== node.type) {
      return {
        success: false,
        code: 400,
        message: 'itemType does not match target item',
        data: null,
      };
    }

    vfsApi.permanentDelete(itemId);
    addLog('recycle_permanent_delete', { itemId, itemName: node.name });

    return {
      success: true,
      code: 200,
      message: 'Item permanently deleted',
      data: {
        itemType: node.type,
        id: node.id,
        name: node.name,
        permanentlyDeletedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/recycle-bin$/, 'delete', () => {
    const result = vfsApi.clearRecycleBin();
    addLog('recycle_clear', { filesDeleted: result.filesDeleted, foldersDeleted: result.foldersDeleted });

    return {
      success: true,
      code: 200,
      data: {
        filesDeleted: result.filesDeleted,
        foldersDeleted: result.foldersDeleted,
        totalStorageFreed: result.totalStorageFreed,
        cleanupCompletedAt: new Date().toISOString(),
      },
    };
  });
};
