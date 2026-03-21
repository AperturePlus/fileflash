import JSZip from 'jszip';
import Mock from 'mockjs';
import { addLog, addNotification } from '../state';
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

function buildMockFileBlob(file: VfsNode) {
  if (file.content) {
    const byteCharacters = atob(file.content);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i += 1) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: file.mimeType || 'application/octet-stream' });
  }

  if ((file.mimeType || '').startsWith('text/')) {
    return new Blob([`Mock content for ${file.name}`], { type: file.mimeType || 'text/plain' });
  }

  if ((file.mimeType || '').startsWith('image/')) {
    const svg = `<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"640\" height=\"360\"><rect width=\"100%\" height=\"100%\" fill=\"#1f2937\"/><text x=\"50%\" y=\"50%\" dominant-baseline=\"middle\" text-anchor=\"middle\" fill=\"#f9fafb\" font-size=\"24\">${file.name}</text></svg>`;
    return new Blob([svg], { type: 'image/svg+xml' });
  }

  if ((file.mimeType || '').startsWith('audio/')) {
    return new Blob([], { type: file.mimeType || 'audio/mpeg' });
  }

  if ((file.mimeType || '').startsWith('video/')) {
    return new Blob([], { type: file.mimeType || 'video/mp4' });
  }

  if (file.mimeType === 'application/pdf') {
    const text = `%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF`;
    return new Blob([text], { type: 'application/pdf' });
  }

  return new Blob([`Binary file: ${file.name}`], { type: file.mimeType || 'application/octet-stream' });
}

function getSortedItems(items: VfsNode[], sort: string | null, order: string | null) {
  const sortField = sort || 'name';
  const sortOrder = order === 'desc' ? -1 : 1;

  return [...items].sort((a, b) => {
    if (a.type === 'folder' && b.type === 'file') return -1;
    if (a.type === 'file' && b.type === 'folder') return 1;

    let compareValue = 0;
    if (sortField === 'size') {
      compareValue = (a.size || 0) - (b.size || 0);
    } else if (sortField === 'updatedAt') {
      compareValue = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
    } else if (sortField === 'createdAt') {
      compareValue = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
    } else {
      compareValue = a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
    }

    return compareValue * sortOrder;
  });
}

export const setupFileMocks = () => {
  Mock.mock(/\/api\/v1\/files\/?(\?.*)?$/, 'get', (options) => {
    const url = parseUrl(options.url);
    const folderId = url.searchParams.get('folderId') || 'root';
    const search = url.searchParams.get('search');
    const sort = url.searchParams.get('sort');
    const order = url.searchParams.get('order');

    const sourceItems = search
      ? vfsApi.search(folderId, search)
      : vfsApi.getChildren(folderId);

    const sorted = getSortedItems(sourceItems, sort, order);
    const mapped = sorted.map(nodeToItem);

    return {
      success: true,
      code: 200,
      data: {
        items: mapped,
        pagination: {
          totalItems: mapped.length,
          totalPages: 1,
          perPage: mapped.length,
          currentPage: 1,
          hasPrev: false,
          hasNext: false,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/starred$/, 'get', () => {
    const starred = vfsApi.getStarred().map(nodeToItem);

    return {
      success: true,
      code: 200,
      data: {
        items: starred,
        pagination: {
          totalItems: starred.length,
          totalPages: 1,
          perPage: starred.length,
          currentPage: 1,
          hasPrev: false,
          hasNext: false,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)$/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/?]+)/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file' || node.isTrashed) {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    return {
      success: true,
      code: 200,
      data: {
        ...nodeToItem(node),
        status: true,
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/download$/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/download/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    addLog('file_download', { fileId: node.id, fileName: node.name });
    return buildMockFileBlob(node);
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/preview$/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/preview/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    return buildMockFileBlob(node);
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/thumbnail$/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/thumbnail/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    const svg = `<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"200\" height=\"120\"><rect width=\"100%\" height=\"100%\" fill=\"#0f172a\"/><text x=\"50%\" y=\"50%\" dominant-baseline=\"middle\" text-anchor=\"middle\" fill=\"#e2e8f0\" font-size=\"12\">${node.name}</text></svg>`;
    return new Blob([svg], { type: 'image/svg+xml' });
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/move$/, 'patch', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/move/) || [])[1];
    const { targetFolderId } = JSON.parse(options.body || '{}');

    const moved = vfsApi.move(fileId, targetFolderId);
    addLog('file_move', { fileId, targetFolderId });

    return {
      success: true,
      code: 200,
      data: {
        fileId: moved.id,
        targetFolderId,
        movedAt: moved.updatedAt,
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/copy$/, 'post', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/copy/) || [])[1];
    const { targetFolderId, newName } = JSON.parse(options.body || '{}');

    const copied = vfsApi.copy(fileId, targetFolderId, newName);
    addLog('file_copy', { fileId, targetFolderId, copiedFileId: copied.id });

    return {
      success: true,
      code: 201,
      data: {
        fileId: copied.id,
        originalFileId: fileId,
        targetFolderId,
        newName: copied.name,
        copiedAt: copied.createdAt,
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/star$/, 'patch', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/star/) || [])[1];
    const { isStarred } = JSON.parse(options.body || '{}');
    const node = vfsApi.setStarred(fileId, Boolean(isStarred));

    return {
      success: true,
      code: 200,
      data: nodeToItem(node),
    };
  });

  Mock.mock(/\/api\/v1\/files\/(?![^/]+\/(?:move|copy|download|preview|thumbnail|star)$)([^/?]+)$/, 'patch', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/?]+)/) || [])[1];
    const { fileName } = JSON.parse(options.body || '{}');
    const updated = vfsApi.rename(fileId, fileName);

    return {
      success: true,
      code: 200,
      data: {
        ...nodeToItem(updated),
        status: true,
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)$/, 'delete', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/?]+)/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    vfsApi.delete(fileId);
    addLog('file_delete', { fileId, fileName: node.name });

    return {
      success: true,
      code: 200,
      data: {
        fileId,
        fileName: node.name,
        deletedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/files\/batch-download$/, 'post', async (options) => {
    const { fileIds = [] } = JSON.parse(options.body || '{}');
    const zip = new JSZip();

    fileIds.forEach((fileId: string) => {
      const node = vfsApi.get(fileId);
      if (!node || node.type !== 'file' || node.isTrashed) return;
      zip.file(node.name, `Mock content for ${node.name}`);
    });

    addLog('file_batch_download', { count: fileIds.length });
    return zip.generateAsync({ type: 'blob' });
  });

  Mock.mock(/\/api\/v1\/files\/batch$/, 'post', (options) => {
    const { action, fileIds = [], targetFolderId } = JSON.parse(options.body || '{}');

    if (!Array.isArray(fileIds) || fileIds.length === 0) {
      return {
        success: false,
        code: 400,
        message: 'fileIds is required',
        data: null,
      };
    }

    let succeeded = 0;

    if (action === 'delete') {
      fileIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node) {
          vfsApi.delete(id);
          succeeded += 1;
        }
      });
      addLog('file_batch_delete', { count: succeeded });
      addNotification(`${succeeded} files moved to recycle bin`, true);
    } else if (action === 'move') {
      fileIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node) {
          vfsApi.move(id, targetFolderId);
          succeeded += 1;
        }
      });
      addLog('file_batch_move', { count: succeeded, targetFolderId: targetFolderId || '' });
    } else if (action === 'copy') {
      fileIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node) {
          vfsApi.copy(id, targetFolderId);
          succeeded += 1;
        }
      });
      addLog('file_batch_copy', { count: succeeded, targetFolderId: targetFolderId || '' });
    } else {
      return {
        success: false,
        code: 400,
        message: 'Unsupported batch action',
        data: null,
      };
    }

    return {
      success: true,
      code: 200,
      data: {
        processed: fileIds.length,
        action,
        succeeded,
      },
    };
  });
};
