import Mock from 'mockjs';
import { addLog, mockShares } from '../state';
import { vfsApi, type VfsNode } from '../vfs';

function parseUrl(url: string) {
  return new URL(url, 'http://localhost');
}

function nodeToItem(node: VfsNode) {
  if (node.type === 'folder') {
    return {
      itemType: 'folder' as const,
      id: node.id,
      name: node.name,
      size: vfsApi.getFolderStats(node.id).totalSize,
      ownerName: 'You',
      updatedAt: node.updatedAt,
      createdAt: node.createdAt,
      parentFolderId: node.parent,
      permission: node.permission || 'owner',
      isStarred: node.isStarred || false,
    };
  }

  return {
    itemType: 'file' as const,
    id: node.id,
    name: node.name,
    size: node.size || 0,
    mimeType: node.mimeType || 'application/octet-stream',
    ownerName: 'You',
    updatedAt: node.updatedAt,
    createdAt: node.createdAt,
    folderId: node.parent || 'root',
    permission: node.permission || 'owner',
    isStarred: node.isStarred || false,
  };
}

function sortItems(nodes: VfsNode[], sort: string | null, order: string | null) {
  const sortField = sort || 'name';
  const sortOrder = order === 'desc' ? -1 : 1;

  return [...nodes].sort((a, b) => {
    if (a.type === 'folder' && b.type === 'file') return -1;
    if (a.type === 'file' && b.type === 'folder') return 1;

    let value = 0;
    if (sortField === 'size') {
      value = (a.size || 0) - (b.size || 0);
    } else if (sortField === 'updatedAt') {
      value = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
    } else if (sortField === 'createdAt') {
      value = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
    } else {
      value = a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
    }

    return value * sortOrder;
  });
}

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

function nextAvailableFolderName(parentId: string, originalName: string, excludeId: string) {
  const hasConflict = (candidate: string) =>
    vfsApi
      .getChildren(parentId)
      .some((node) => !node.isTrashed && node.type === 'folder' && node.id !== excludeId && node.name === candidate);

  if (!hasConflict(originalName)) {
    return originalName;
  }

  const stem = originalName.trim() || 'Folder';
  let index = 1;
  while (true) {
    const candidate = `${stem} (${index})`;
    if (!hasConflict(candidate)) {
      return candidate;
    }
    index += 1;
  }
}

function collectSubtreeIds(rootFolderId: string): { folderIds: string[]; fileIds: string[] } {
  const folderIds: string[] = [];
  const fileIds: string[] = [];

  const walk = (folderId: string) => {
    folderIds.push(folderId);
    vfsApi.getChildren(folderId).forEach((node) => {
      if (node.isTrashed) return;
      if (node.type === 'folder') {
        walk(node.id);
      } else {
        fileIds.push(node.id);
      }
    });
  };

  walk(rootFolderId);
  return { folderIds, fileIds };
}

function revokeShares(fileIds: string[], folderIds: string[]) {
  const fileSet = new Set(fileIds);
  const folderSet = new Set(folderIds);
  let revoked = 0;

  for (let index = mockShares.length - 1; index >= 0; index -= 1) {
    const share = mockShares[index];
    const matchFile = share.itemType === 'file' && fileSet.has(share.itemInfo.id);
    const matchFolder = share.itemType === 'folder' && folderSet.has(share.itemInfo.id);
    if (!matchFile && !matchFolder) continue;
    mockShares.splice(index, 1);
    revoked += 1;
  }
  return revoked;
}

export const setupFolderMocks = () => {
  Mock.mock(/\/api\/v1\/folders$/, 'get', (options) => {
    const url = parseUrl(options.url);
    const parentId = url.searchParams.get('parentId') || 'root';

    const folders = vfsApi
      .getChildren(parentId)
      .filter((node) => node.type === 'folder')
      .map(nodeToItem);

    return {
      success: true,
      code: 200,
      data: {
        items: folders,
        pagination: buildPagination(folders.length),
      },
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)\/path$/, 'get', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/]+)\/path/) || [])[1] || 'root';
    const path = vfsApi.getPath(folderId);

    if (!path.length) {
      return {
        success: false,
        code: 404,
        message: 'Folder not found',
        data: null,
      };
    }

    const pathItems = path.map((node) => ({
      folderId: node.id,
      name: node.id === 'root' ? 'My Files' : node.name,
    }));

    return {
      success: true,
      code: 200,
      data: {
        fullPath: pathItems.map((item) => item.name).join('/'),
        pathItems,
      },
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)\/size$/, 'get', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/]+)\/size/) || [])[1];

    try {
      const stats = vfsApi.getFolderStats(folderId);
      return {
        success: true,
        code: 200,
        data: stats,
      };
    } catch {
      return {
        success: false,
        code: 404,
        message: 'Folder not found',
        data: null,
      };
    }
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)\/copy$/, 'post', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/]+)\/copy/) || [])[1];
    const { targetParentId, newName } = JSON.parse(options.body || '{}');

    const copied = vfsApi.copy(folderId, targetParentId, newName);
    addLog('folder_copy', { folderId, copiedFolderId: copied.id, targetParentId });

    return {
      success: true,
      code: 201,
      data: nodeToItem(copied),
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)\/star$/, 'patch', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/]+)\/star/) || [])[1];
    const { isStarred } = JSON.parse(options.body || '{}');
    const updated = vfsApi.setStarred(folderId, Boolean(isStarred));

    return {
      success: true,
      code: 200,
      data: nodeToItem(updated),
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)(?:\?.*)?$/, 'get', (options) => {
    const match = options.url.match(/\/api\/v1\/folders\/([^/?]+)/);
    const folderId = match ? match[1] : 'root';
    const url = parseUrl(options.url);

    const search = url.searchParams.get('search');
    const sort = url.searchParams.get('sort');
    const order = url.searchParams.get('order');

    const folder = vfsApi.get(folderId);
    if (!folder || folder.type !== 'folder') {
      return {
        success: false,
        code: 404,
        message: 'Folder not found',
        data: null,
      };
    }

    const sourceItems = search ? vfsApi.search(folderId, search) : vfsApi.getChildren(folderId);
    const sorted = sortItems(sourceItems, sort, order);
    const items = sorted.map(nodeToItem);

    return {
      success: true,
      code: 200,
      data: {
        items,
        pagination: buildPagination(items.length),
      },
    };
  });

  Mock.mock(/\/api\/v1\/folders$/, 'post', (options) => {
    const { folderName, parentFolderId } = JSON.parse(options.body || '{}');

    if (!folderName || !parentFolderId) {
      return {
        success: false,
        code: 400,
        message: 'folderName and parentFolderId are required',
        data: null,
      };
    }

    const newFolder = vfsApi.createFolder(parentFolderId, folderName);
    addLog('folder_create', { folderId: newFolder.id, folderName });

    return {
      success: true,
      code: 201,
      data: nodeToItem(newFolder),
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)\/move$/, 'patch', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/]+)\/move/) || [])[1];
    const { targetParentId, shareHandling = 'keep' } = JSON.parse(options.body || '{}');
    const folder = vfsApi.get(folderId);
    if (!folder || folder.type !== 'folder' || folder.isTrashed) {
      return {
        success: false,
        code: 404,
        message: 'Folder not found',
        data: null,
      };
    }
    if (folder.id === 'root') {
      return {
        success: false,
        code: 400,
        message: 'Root folder cannot be moved',
        data: null,
      };
    }

    const targetFolder = vfsApi.get(targetParentId);
    if (!targetFolder || targetFolder.type !== 'folder' || targetFolder.isTrashed) {
      return {
        success: false,
        code: 404,
        message: 'Target folder not found',
        data: null,
      };
    }

    const finalName = nextAvailableFolderName(targetParentId, folder.name, folder.id);
    try {
      vfsApi.move(folderId, targetParentId);
      if (finalName !== folder.name) {
        vfsApi.rename(folderId, finalName);
      }
    } catch (error) {
      return {
        success: false,
        code: 409,
        message: (error as Error)?.message || 'Move failed',
        data: null,
      };
    }

    let revokedShareCount = 0;
    if (shareHandling === 'revoke') {
      const ids = collectSubtreeIds(folderId);
      revokedShareCount = revokeShares(ids.fileIds, ids.folderIds);
    }
    const movedFolder = vfsApi.get(folderId)!;
    addLog('folder_move', { folderId, targetParentId, shareHandling });

    return {
      success: true,
      code: 200,
      data: {
        folderId: movedFolder.id,
        targetParentId: targetParentId,
        finalName: movedFolder.name,
        shareHandling,
        revokedShareCount,
        movedAt: movedFolder.updatedAt,
      },
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)$/, 'patch', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/?]+)/) || [])[1];
    const { folderName } = JSON.parse(options.body || '{}');

    const renamed = vfsApi.rename(folderId, folderName);

    return {
      success: true,
      code: 200,
      data: nodeToItem(renamed),
    };
  });

  Mock.mock(/\/api\/v1\/folders\/([^/]+)$/, 'delete', (options) => {
    const folderId = (options.url.match(/\/api\/v1\/folders\/([^/?]+)/) || [])[1];
    const folder = vfsApi.get(folderId);

    if (!folder || folder.type !== 'folder') {
      return {
        success: false,
        code: 404,
        message: 'Folder not found',
        data: null,
      };
    }

    vfsApi.delete(folderId);
    addLog('folder_delete', { folderId, folderName: folder.name });

    return {
      success: true,
      code: 200,
      data: {
        folderId,
        folderName: folder.name,
        deletedAt: new Date().toISOString(),
      },
    };
  });
};
