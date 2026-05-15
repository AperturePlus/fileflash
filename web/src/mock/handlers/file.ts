import JSZip from 'jszip';
import Mock from 'mockjs';
import { addLog, addNotification, createMockId, mockJobs, mockShares } from '../state';
import { STARRED_ITEMS_LIMIT, vfsApi, type VfsNode } from '../vfs';

const MINIMAL_VALID_PDF_BASE64 = 'JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCA2MTIgNzkyXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCA0NCA+PgpzdHJlYW0KQlQKL0YxIDI0IFRmCjEwMCA3MDAgVGQKKEhlbGxvLCBQREYhKSBUagpFVAplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKPDwgL1R5cGUgL0ZvbnQgL1N1YnR5cGUgL1R5cGUxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1OCAwMDAwMCBuIAowMDAwMDAwMTE1IDAwMDAwIG4gCjAwMDAwMDAyNzAgMDAwMDAgbiAKMDAwMDAwMDM2MyAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDYgL1Jvb3QgMSAwIFIgPj4Kc3RhcnR4cmVmCjQ0MwolJUVPRgo=';

function parseUrl(url: string) {
  return new URL(url, 'http://localhost');
}

function decodeBase64ToBytes(content: string) {
  const byteCharacters = atob(content);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i += 1) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  return new Uint8Array(byteNumbers);
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
    mediaOptimization: node.mediaOptimization,
  };
}

function buildMockFileBlob(file: VfsNode) {
  if (file.content) {
    const byteArray = decodeBase64ToBytes(file.content);
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
    return new Blob([decodeBase64ToBytes(MINIMAL_VALID_PDF_BASE64)], { type: 'application/pdf' });
  }

  return new Blob([`Binary file: ${file.name}`], { type: file.mimeType || 'application/octet-stream' });
}

function nowIso() {
  return new Date().toISOString();
}

function mockError(code: number, message: string) {
  return {
    success: false,
    code,
    message,
    data: null,
    timestamp: nowIso(),
  };
}

function resolvePreviewNode(file: VfsNode) {
  const optimization = file.mediaOptimization;
  if (!optimization) {
    return file;
  }
  if (optimization.status === 'ready') {
    return {
      ...file,
      mimeType: optimization.optimizedMimeType || file.mimeType,
    };
  }
  return file;
}

function splitFileName(name: string) {
  const dotIndex = name.lastIndexOf('.');
  if (dotIndex > 0) {
    return {
      stem: name.slice(0, dotIndex),
      ext: name.slice(dotIndex),
    };
  }
  return { stem: name, ext: '' };
}

function hasNameConflict({
  parentId,
  itemType,
  name,
  excludeId,
}: {
  parentId: string;
  itemType: 'file' | 'folder';
  name: string;
  excludeId?: string;
}) {
  return vfsApi
    .getChildren(parentId)
    .some((node) => !node.isTrashed && node.type === itemType && node.id !== excludeId && node.name === name);
}

function nextAvailableName({
  parentId,
  itemType,
  originalName,
  excludeId,
}: {
  parentId: string;
  itemType: 'file' | 'folder';
  originalName: string;
  excludeId?: string;
}) {
  if (!hasNameConflict({ parentId, itemType, name: originalName, excludeId })) {
    return originalName;
  }

  if (itemType === 'file') {
    const { stem, ext } = splitFileName(originalName);
    let index = 1;
    while (true) {
      const candidate = `${stem || 'file'} (${index})${ext}`;
      if (!hasNameConflict({ parentId, itemType, name: candidate, excludeId })) {
        return candidate;
      }
      index += 1;
    }
  }

  const base = originalName.trim() || 'Folder';
  let index = 1;
  while (true) {
    const candidate = `${base} (${index})`;
    if (!hasNameConflict({ parentId, itemType, name: candidate, excludeId })) {
      return candidate;
    }
    index += 1;
  }
}

function collectFolderSubtreeIds(rootFolderId: string): { folderIds: string[]; fileIds: string[] } {
  const folderIds: string[] = [];
  const fileIds: string[] = [];

  const walk = (folderId: string) => {
    folderIds.push(folderId);
    const children = vfsApi.getChildren(folderId);
    children.forEach((node) => {
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

function buildFolderRelativeZipPath(rootFolderId: string, fileId: string, fallbackName: string): string {
  const path = vfsApi.getPath(fileId);
  const rootIndex = path.findIndex((item) => item.id === rootFolderId);
  if (rootIndex < 0) {
    return fallbackName;
  }
  const folderSegments = path.slice(rootIndex, -1).map((item) => item.name);
  return [...folderSegments, fallbackName].join('/');
}

function revokeActiveShares(fileIds: string[], folderIds: string[]): number {
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

function moveNodeWithPolicy(
  itemId: string,
  targetFolderId: string,
  shareHandling: 'keep' | 'revoke',
  expectedType?: 'file' | 'folder',
) {
  const node = vfsApi.get(itemId);
  if (!node || node.isTrashed) {
    return { success: false as const, code: 404, message: 'Item not found' };
  }
  if (expectedType && node.type !== expectedType) {
    return { success: false as const, code: 404, message: `${expectedType === 'file' ? 'File' : 'Folder'} not found` };
  }

  const targetFolder = vfsApi.get(targetFolderId);
  if (!targetFolder || targetFolder.type !== 'folder' || targetFolder.isTrashed) {
    return { success: false as const, code: 404, message: 'Target folder not found' };
  }

  if (node.type === 'folder' && node.id === 'root') {
    return { success: false as const, code: 400, message: 'Root folder cannot be moved' };
  }

  const finalName = nextAvailableName({
    parentId: targetFolderId,
    itemType: node.type,
    originalName: node.name,
    excludeId: node.id,
  });

  try {
    vfsApi.move(itemId, targetFolderId);
    if (finalName !== node.name) {
      vfsApi.rename(itemId, finalName);
    }
  } catch (error) {
    return {
      success: false as const,
      code: 409,
      message: (error as Error)?.message || 'Move failed',
    };
  }

  let revokedShareCount = 0;
  if (shareHandling === 'revoke') {
    if (node.type === 'file') {
      revokedShareCount = revokeActiveShares([node.id], []);
    } else {
      const { folderIds, fileIds } = collectFolderSubtreeIds(node.id);
      revokedShareCount = revokeActiveShares(fileIds, folderIds);
    }
  }

  const movedNode = vfsApi.get(itemId)!;
  return {
    success: true as const,
    code: 200,
    itemType: movedNode.type,
    itemId: movedNode.id,
    targetFolderId,
    finalName: movedNode.name,
    movedAt: movedNode.updatedAt,
    shareHandling,
    revokedShareCount,
  };
}

function detectArchiveFormat(name: string) {
  const lower = (name || '').toLowerCase();
  if (lower.endsWith('.7z')) return '7z';
  if (lower.endsWith('.zip')) return 'zip';
  if (lower.endsWith('.tar.gz') || lower.endsWith('.tgz') || lower.endsWith('.gz')) return 'tar.gz';
  if (lower.endsWith('.tar')) return 'tar';
  return 'unknown';
}

function defaultSubfolderName(fileName: string) {
  const lower = (fileName || '').toLowerCase();
  if (lower.endsWith('.tar.gz')) return fileName.slice(0, -'.tar.gz'.length);
  if (lower.endsWith('.tgz')) return fileName.slice(0, -'.tgz'.length);
  const lastDot = fileName.lastIndexOf('.');
  return lastDot > 0 ? fileName.slice(0, lastDot) : fileName;
}

function ensureFolderPath(parentId: string, relPath: string) {
  const parts = relPath.split('/').filter(Boolean);
  let current = parentId;

  for (const part of parts) {
    const existing = vfsApi.getChildren(current).find((node) => node.type === 'folder' && node.name === part);
    if (existing && existing.type === 'folder') {
      current = existing.id;
      continue;
    }
    const created = vfsApi.createFolder(current, part);
    current = created.id;
  }

  return current;
}

function createMockJob<T>(taskType: string, payload: Record<string, any>, result: T) {
  const timestamp = nowIso();
  const jobId = createMockId('job');

  const job = {
    jobId,
    taskType,
    status: 'succeeded',
    priority: 100,
    payload,
    result,
    errorMessage: null,
    attempt: 0,
    maxAttempts: 5,
    scheduledAt: timestamp,
    startedAt: timestamp,
    finishedAt: timestamp,
    traceId: `mock-${jobId}`,
    idempotencyKey: null,
    requestedBy: null,
    createdAt: timestamp,
    updatedAt: timestamp,
  };

  mockJobs[jobId] = job as any;
  return job;
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

function paginateItems<T>(items: T[], page = 1, perPage = 20) {
  const normalizedPage = Math.max(1, Number(page) || 1);
  const normalizedPerPage = Math.max(1, Number(perPage) || 20);
  const start = (normalizedPage - 1) * normalizedPerPage;
  const sliced = items.slice(start, start + normalizedPerPage);
  const totalPages = Math.max(1, Math.ceil(items.length / normalizedPerPage));

  return {
    items: sliced,
    pagination: {
      totalItems: items.length,
      totalPages,
      perPage: normalizedPerPage,
      currentPage: normalizedPage,
      hasPrev: normalizedPage > 1,
      hasNext: normalizedPage < totalPages,
    },
  };
}

function toAdminFileAuditItem(node: VfsNode) {
  return {
    id: node.id,
    name: node.name,
    size: node.size || 0,
    mimeType: node.mimeType || 'application/octet-stream',
    hash: node.hash || `mock-hash-${node.id}`,
    virusStatus: node.virusStatus || 'pending',
    isShared: mockShares.some((share) => share.itemType === 'file' && share.itemInfo.id === node.id),
    ownerName: 'You',
    updatedAt: node.updatedAt,
    createdAt: node.createdAt,
  };
}

export const setupFileMocks = () => {
  Mock.mock(/\/api\/v1\/admin\/files(?:\?.*)?$/, 'get', (options) => {
    const url = parseUrl(options.url);
    const search = (url.searchParams.get('search') || '').trim().toLowerCase();
    const virusStatus = url.searchParams.get('virusStatus');
    const sort = url.searchParams.get('sort');
    const order = url.searchParams.get('order');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);

    const files = Object.values(vfsApi.getAll()).filter((node) => node.type === 'file' && !node.isTrashed);
    const sortedNodes = getSortedItems(files, sort, order);
    const filtered = sortedNodes.filter((node) => {
      if (search && !node.name.toLowerCase().includes(search)) {
        return false;
      }
      if (virusStatus && (node.virusStatus || 'pending') !== virusStatus) {
        return false;
      }
      return true;
    });

    return {
      success: true,
      code: 200,
      data: paginateItems(filtered.map(toAdminFileAuditItem), page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/admin\/files\/([^/]+)$/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/admin\/files\/([^/?]+)/) || [])[1];
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
      data: toAdminFileAuditItem(node),
    };
  });

  Mock.mock(/\/api\/v1\/admin\/files\/([^/]+)\/rescan$/, 'post', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/admin\/files\/([^/]+)\/rescan/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file' || node.isTrashed) {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    const normalizedName = node.name.toLowerCase();
    let nextStatus: 'clean' | 'pending' | 'flagged' = 'clean';
    if (normalizedName.includes('virus') || normalizedName.includes('suspicious')) {
      nextStatus = 'flagged';
    } else if (Math.random() < 0.15) {
      nextStatus = 'pending';
    }

    node.virusStatus = nextStatus;
    node.updatedAt = new Date().toISOString();
    addLog('virus_scan', { fileId: node.id, fileName: node.name, status: node.virusStatus });

    return {
      success: true,
      code: 200,
      data: {
        fileId: node.id,
        virusStatus: node.virusStatus,
        scannedAt: node.updatedAt,
      },
    };
  });

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

    return buildMockFileBlob(resolvePreviewNode(node));
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/archive\/preview$/, 'post', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/archive\/preview/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    const format = detectArchiveFormat(node.name);
    const entries = [
      { path: 'docs', isDir: true, size: 0 },
      { path: 'docs/README.txt', isDir: false, size: 1024 },
      { path: 'images', isDir: true, size: 0 },
      { path: 'images/logo.png', isDir: false, size: 2048 },
    ];
    const result = {
      archive: { format, fileName: node.name },
      entries,
      summary: {
        totalEntries: entries.length,
        fileCount: entries.filter((e) => !e.isDir).length,
        dirCount: entries.filter((e) => e.isDir).length,
        totalUncompressedBytes: entries.filter((e) => !e.isDir).reduce((sum, e) => sum + (e.size || 0), 0),
        truncated: false,
      },
      previewedAt: nowIso(),
    };

    const job = createMockJob('task.archive_preview', { fileId, fileName: node.name }, result);
    addLog('archive_preview', { fileId, fileName: node.name });

    return {
      success: true,
      code: 201,
      data: job,
    };
  });

  Mock.mock(/\/api\/v1\/files\/([^/]+)\/archive\/extract$/, 'post', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/([^/]+)\/archive\/extract/) || [])[1];
    const node = vfsApi.get(fileId);

    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    const body = JSON.parse(options.body || '{}');
    const targetFolderId = body.targetFolderId || 'root';
    const createSubfolder = Boolean(body.createSubfolder);
    const subfolderName = (body.subfolderName || '').trim() || defaultSubfolderName(node.name) || 'Extracted';

    let extractRootId = targetFolderId;
    if (createSubfolder) {
      extractRootId = vfsApi.createFolder(targetFolderId, subfolderName).id;
    }

    const previewEntries = [
      { path: 'docs', isDir: true, size: 0 },
      { path: 'docs/README.txt', isDir: false, size: 1024 },
      { path: 'images', isDir: true, size: 0 },
      { path: 'images/logo.png', isDir: false, size: 2048 },
    ];

    const createdDirs = new Set<string>();
    for (const entry of previewEntries) {
      if (entry.isDir) {
        ensureFolderPath(extractRootId, entry.path);
        createdDirs.add(entry.path);
        continue;
      }

      const parts = entry.path.split('/').filter(Boolean);
      const fileName = parts.pop() || 'file.bin';
      const parentPath = parts.join('/');
      const parentId = parentPath ? ensureFolderPath(extractRootId, parentPath) : extractRootId;
      const mimeType = fileName.toLowerCase().endsWith('.png') ? 'image/png' : 'text/plain';
      vfsApi.createFile(parentId, fileName, entry.size || 0, mimeType);
    }

    const totalBytes = previewEntries.filter((e) => !e.isDir).reduce((sum, e) => sum + (e.size || 0), 0);
    const result = {
      archive: { format: detectArchiveFormat(node.name), fileName: node.name },
      summary: {
        extractedFiles: previewEntries.filter((e) => !e.isDir).length,
        extractedDirs: createdDirs.size,
        skippedEntries: 0,
        totalBytes,
      },
      extractedFolderId: createSubfolder ? extractRootId : undefined,
      extractedAt: nowIso(),
    };

    const job = createMockJob('task.archive_extract', { fileId, fileName: node.name }, result);
    addLog('archive_extract', { fileId, fileName: node.name, targetFolderId });
    addNotification(`Extracted ${node.name} successfully.`);

    return {
      success: true,
      code: 201,
      data: job,
    };
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
    const { targetFolderId, shareHandling = 'keep' } = JSON.parse(options.body || '{}');
    const moved = moveNodeWithPolicy(fileId, targetFolderId, shareHandling, 'file');
    if (!moved.success) {
      return {
        success: false,
        code: moved.code,
        message: moved.message,
        data: null,
      };
    }
    addLog('file_move', { fileId, targetFolderId, shareHandling });

    return {
      success: true,
      code: 200,
      data: {
        fileId: moved.itemId,
        targetFolderId: moved.targetFolderId,
        finalName: moved.finalName,
        shareHandling: moved.shareHandling,
        revokedShareCount: moved.revokedShareCount,
        movedAt: moved.movedAt,
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
    const node = vfsApi.get(fileId);
    if (!node || node.type !== 'file' || node.isTrashed) {
      return mockError(404, 'File not found');
    }

    const next = Boolean(isStarred);
    if (next && !node.isStarred && vfsApi.getStarred().length >= STARRED_ITEMS_LIMIT) {
      return mockError(400, `已达收藏上限 ${STARRED_ITEMS_LIMIT}`);
    }

    const updatedNode = vfsApi.setStarred(fileId, next);

    return {
      success: true,
      code: 200,
      data: nodeToItem(updatedNode),
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
    const { fileIds = [], folderIds = [] } = JSON.parse(options.body || '{}');
    const zip = new JSZip();
    const zipPaths = new Map<string, string>();

    fileIds.forEach((fileId: string) => {
      const node = vfsApi.get(fileId);
      if (!node || node.type !== 'file' || node.isTrashed) return;
      zipPaths.set(fileId, node.name);
    });
    folderIds.forEach((folderId: string) => {
      const folder = vfsApi.get(folderId);
      if (!folder || folder.type !== 'folder' || folder.isTrashed) return;
      const subtree = collectFolderSubtreeIds(folderId);
      subtree.fileIds.forEach((id) => {
        const node = vfsApi.get(id);
        if (!node || node.type !== 'file' || node.isTrashed) return;
        const relativePath = buildFolderRelativeZipPath(folderId, id, node.name);
        if (!zipPaths.has(id)) {
          zipPaths.set(id, relativePath);
        }
      });
    });

    Array.from(zipPaths.entries()).forEach(([fileId, zipPath]) => {
      const node = vfsApi.get(fileId);
      if (!node || node.type !== 'file' || node.isTrashed) return;
      zip.file(zipPath, `Mock content for ${node.name}`);
    });

    addLog('file_batch_download', { count: zipPaths.size });
    return zip.generateAsync({ type: 'blob' });
  });

  Mock.mock(/\/api\/v1\/files\/batch$/, 'post', (options) => {
    const {
      action,
      fileIds = [],
      folderIds = [],
      targetFolderId,
      shareHandling = 'keep',
    } = JSON.parse(options.body || '{}');

    if ((!Array.isArray(fileIds) || fileIds.length === 0) && (!Array.isArray(folderIds) || folderIds.length === 0)) {
      return {
        success: false,
        code: 400,
        message: 'At least one fileId or folderId is required',
        data: null,
      };
    }

    const uniqueFileIds = Array.from(new Set(fileIds as string[]));
    const uniqueFolderIds = Array.from(new Set(folderIds as string[]));
    const results: Array<{
      itemType: 'file' | 'folder';
      itemId: string;
      success: boolean;
      finalName: string | null;
      movedAt: string | null;
      message: string | null;
      shareHandling: 'keep' | 'revoke';
      revokedShareCount: number;
    }> = [];

    if (action === 'delete') {
      uniqueFileIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node && node.type === 'file' && !node.isTrashed) {
          vfsApi.delete(id);
          results.push({
            itemType: 'file',
            itemId: id,
            success: true,
            finalName: node.name,
            movedAt: node.updatedAt,
            message: null,
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        } else {
          results.push({
            itemType: 'file',
            itemId: id,
            success: false,
            finalName: null,
            movedAt: null,
            message: 'File not found',
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        }
      });
      uniqueFolderIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node && node.type === 'folder' && !node.isTrashed) {
          vfsApi.delete(id);
          results.push({
            itemType: 'folder',
            itemId: id,
            success: true,
            finalName: node.name,
            movedAt: node.updatedAt,
            message: null,
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        } else {
          results.push({
            itemType: 'folder',
            itemId: id,
            success: false,
            finalName: null,
            movedAt: null,
            message: 'Folder not found',
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        }
      });
      const succeeded = results.filter((item) => item.success).length;
      addLog('file_batch_delete', { count: succeeded });
      addNotification(`${succeeded} item(s) moved to recycle bin`, true);
    } else if (action === 'move') {
      if (!targetFolderId) {
        return {
          success: false,
          code: 400,
          message: 'targetFolderId is required for move action',
          data: null,
        };
      }

      uniqueFileIds.forEach((id: string) => {
        const moved = moveNodeWithPolicy(id, targetFolderId, shareHandling, 'file');
        if (moved.success) {
          results.push({
            itemType: 'file',
            itemId: moved.itemId,
            success: true,
            finalName: moved.finalName,
            movedAt: moved.movedAt,
            message: null,
            shareHandling: moved.shareHandling,
            revokedShareCount: moved.revokedShareCount,
          });
        } else {
          results.push({
            itemType: 'file',
            itemId: id,
            success: false,
            finalName: null,
            movedAt: null,
            message: moved.message,
            shareHandling,
            revokedShareCount: 0,
          });
        }
      });
      uniqueFolderIds.forEach((id: string) => {
        const moved = moveNodeWithPolicy(id, targetFolderId, shareHandling, 'folder');
        if (moved.success) {
          results.push({
            itemType: 'folder',
            itemId: moved.itemId,
            success: true,
            finalName: moved.finalName,
            movedAt: moved.movedAt,
            message: null,
            shareHandling: moved.shareHandling,
            revokedShareCount: moved.revokedShareCount,
          });
        } else {
          results.push({
            itemType: 'folder',
            itemId: id,
            success: false,
            finalName: null,
            movedAt: null,
            message: moved.message,
            shareHandling,
            revokedShareCount: 0,
          });
        }
      });
      const succeeded = results.filter((item) => item.success).length;
      addLog('file_batch_move', { count: succeeded, targetFolderId: targetFolderId || '' });
    } else if (action === 'copy') {
      if (!targetFolderId) {
        return {
          success: false,
          code: 400,
          message: 'targetFolderId is required for copy action',
          data: null,
        };
      }

      uniqueFileIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node && node.type === 'file' && !node.isTrashed) {
          const copied = vfsApi.copy(id, targetFolderId);
          results.push({
            itemType: 'file',
            itemId: copied.id,
            success: true,
            finalName: copied.name,
            movedAt: copied.updatedAt,
            message: null,
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        } else {
          results.push({
            itemType: 'file',
            itemId: id,
            success: false,
            finalName: null,
            movedAt: null,
            message: 'File not found',
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        }
      });
      uniqueFolderIds.forEach((id: string) => {
        const node = vfsApi.get(id);
        if (node && node.type === 'folder' && !node.isTrashed) {
          const copied = vfsApi.copy(id, targetFolderId);
          results.push({
            itemType: 'folder',
            itemId: copied.id,
            success: true,
            finalName: copied.name,
            movedAt: copied.updatedAt,
            message: null,
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        } else {
          results.push({
            itemType: 'folder',
            itemId: id,
            success: false,
            finalName: null,
            movedAt: null,
            message: 'Folder not found',
            shareHandling: 'keep',
            revokedShareCount: 0,
          });
        }
      });
      const succeeded = results.filter((item) => item.success).length;
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
        processed: results.length,
        action,
        succeeded: results.filter((item) => item.success).length,
        failed: results.filter((item) => !item.success).length,
        results,
      },
    };
  });
};
