import Mock from 'mockjs';

export interface VfsNode {
  id: string;
  name: string;
  type: 'folder' | 'file';
  parent: string | null;
  children?: string[];
  size?: number;
  mimeType?: string;
  content?: string;
  createdAt: string;
  updatedAt: string;
  permission?: 'read' | 'write' | 'owner';
  isTrashed?: boolean;
  deletedAt?: string;
  isStarred?: boolean;
  starredAt?: string;
  hash?: string;
  virusStatus?: 'clean' | 'pending' | 'flagged';
  thumbnailUrl?: string;
  mediaOptimization?: {
    status: 'queued' | 'running' | 'ready' | 'failed';
    mediaType: 'audio' | 'video';
    optimizedMimeType?: string;
    updatedAt: string;
  };
}

export interface Vfs {
  [key: string]: VfsNode;
}

const VFS_STORAGE_KEY = import.meta.env.VFS_STORAGE_KEY || 'fileflash-vfs';
export const STARRED_ITEMS_LIMIT = 20;

function nowIso() {
  return new Date().toISOString();
}

function newId() {
  return Mock.Random.guid();
}

const initialVfs: Vfs = {
  root: {
    id: 'root',
    name: 'My Files',
    type: 'folder',
    parent: null,
    children: ['folder1', 'folder2', 'file1', 'file2', 'file3', 'file4', 'file5'],
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
  },
  folder1: {
    id: 'folder1',
    name: 'Work Documents',
    type: 'folder',
    parent: 'root',
    children: ['file6', 'file7'],
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
  },
  folder2: {
    id: 'folder2',
    name: 'Media',
    type: 'folder',
    parent: 'root',
    children: ['file8', 'file9'],
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
  },
  file1: {
    id: 'file1',
    name: 'notes.txt',
    type: 'file',
    parent: 'root',
    size: 1024,
    mimeType: 'text/plain',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    isStarred: true,
    starredAt: nowIso(),
    hash: 'mock-hash-file1',
    virusStatus: 'clean',
  },
  file2: {
    id: 'file2',
    name: 'project-plan.pdf',
    type: 'file',
    parent: 'root',
    size: 256000,
    mimeType: 'application/pdf',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    hash: 'mock-hash-file2',
    virusStatus: 'clean',
  },
  file3: {
    id: 'file3',
    name: 'cover.jpg',
    type: 'file',
    parent: 'root',
    size: 98000,
    mimeType: 'image/jpeg',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    thumbnailUrl: '/src/assets/image.svg',
    virusStatus: 'clean',
  },
  file4: {
    id: 'file4',
    name: 'archive.zip',
    type: 'file',
    parent: 'root',
    size: 102400,
    mimeType: 'application/zip',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    virusStatus: 'clean',
  },
  file5: {
    id: 'file5',
    name: 'README.md',
    type: 'file',
    parent: 'root',
    size: 2048,
    mimeType: 'text/markdown',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    virusStatus: 'clean',
  },
  file6: {
    id: 'file6',
    name: 'release-notes.docx',
    type: 'file',
    parent: 'folder1',
    size: 30480,
    mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    virusStatus: 'clean',
  },
  file7: {
    id: 'file7',
    name: 'budget.xlsx',
    type: 'file',
    parent: 'folder1',
    size: 17890,
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    virusStatus: 'clean',
  },
  file8: {
    id: 'file8',
    name: 'intro.mp3',
    type: 'file',
    parent: 'folder2',
    size: 4500030,
    mimeType: 'audio/mpeg',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    isStarred: true,
    starredAt: nowIso(),
    virusStatus: 'clean',
    mediaOptimization: {
      status: 'ready',
      mediaType: 'audio',
      optimizedMimeType: 'audio/mp4',
      updatedAt: nowIso(),
    },
  },
  file9: {
    id: 'file9',
    name: 'walkthrough.mp4',
    type: 'file',
    parent: 'folder2',
    size: 25000000,
    mimeType: 'video/mp4',
    createdAt: nowIso(),
    updatedAt: nowIso(),
    permission: 'owner',
    virusStatus: 'clean',
    mediaOptimization: {
      status: 'running',
      mediaType: 'video',
      updatedAt: nowIso(),
    },
  },
};

let vfs: Vfs;

function saveVfs() {
  localStorage.setItem(VFS_STORAGE_KEY, JSON.stringify(vfs));
}

function sanitizeVfs(input: Vfs): Vfs {
  const sanitized: Vfs = { ...input };

  Object.values(sanitized).forEach((node) => {
    if (node.type === 'folder') {
      const children = Array.isArray(node.children) ? node.children : [];
      const deduped = Array.from(new Set(children)).filter((childId) => Boolean(sanitized[childId]));
      node.children = deduped;
    }
  });

  return sanitized;
}

function loadVfs(): Vfs {
  const storedVfs = localStorage.getItem(VFS_STORAGE_KEY);
  if (!storedVfs) {
    return JSON.parse(JSON.stringify(initialVfs));
  }

  try {
    const parsed = JSON.parse(storedVfs) as Vfs;
    if (!parsed.root || parsed.root.type !== 'folder') {
      return JSON.parse(JSON.stringify(initialVfs));
    }
    return sanitizeVfs(parsed);
  } catch {
    return JSON.parse(JSON.stringify(initialVfs));
  }
}

function ensureFolder(nodeId: string) {
  const node = vfs[nodeId];
  if (!node || node.type !== 'folder') {
    throw new Error(`Folder ${nodeId} not found`);
  }
  if (!Array.isArray(node.children)) {
    node.children = [];
  }
  return node;
}

function removeChild(parentId: string | null, childId: string) {
  if (!parentId) return;
  const parent = vfs[parentId];
  if (!parent || parent.type !== 'folder' || !parent.children) return;
  parent.children = parent.children.filter((id) => id !== childId);
}

function appendChild(parentId: string, childId: string) {
  const parent = ensureFolder(parentId);
  if (!parent.children!.includes(childId)) {
    parent.children!.push(childId);
  }
}

function cloneNodeRecursively(sourceId: string, targetParentId: string, newName?: string): string {
  const source = vfs[sourceId];
  if (!source) throw new Error('Source node not found');

  const nodeId = newId();
  const timestamp = nowIso();
  const copy: VfsNode = {
    ...source,
    id: nodeId,
    parent: targetParentId,
    name: newName ?? source.name,
    createdAt: timestamp,
    updatedAt: timestamp,
    isTrashed: false,
    deletedAt: undefined,
    isStarred: false,
  };

  if (copy.type === 'folder') {
    copy.children = [];
  }

  vfs[nodeId] = copy;
  appendChild(targetParentId, nodeId);

  if (source.type === 'folder' && source.children) {
    source.children.forEach((childId) => {
      cloneNodeRecursively(childId, nodeId);
    });
  }

  return nodeId;
}

function markSubtree(nodeId: string, updater: (node: VfsNode) => void) {
  const node = vfs[nodeId];
  if (!node) return;

  updater(node);
  if (node.type === 'folder' && node.children) {
    node.children.forEach((childId) => markSubtree(childId, updater));
  }
}

function collectSubtreeStats(nodeId: string): { totalSize: number; fileCount: number; folderCount: number } {
  const node = vfs[nodeId];
  if (!node || node.isTrashed) {
    return { totalSize: 0, fileCount: 0, folderCount: 0 };
  }

  if (node.type === 'file') {
    return { totalSize: node.size || 0, fileCount: 1, folderCount: 0 };
  }

  let totalSize = 0;
  let fileCount = 0;
  let folderCount = 1;

  (node.children || []).forEach((childId) => {
    const childStats = collectSubtreeStats(childId);
    totalSize += childStats.totalSize;
    fileCount += childStats.fileCount;
    folderCount += childStats.folderCount;
  });

  return { totalSize, fileCount, folderCount };
}

vfs = loadVfs();
saveVfs();

export const vfsApi = {
  get: (id: string): VfsNode | undefined => vfs[id],

  getAll: (): Vfs => vfs,

  getChildren: (folderId: string): VfsNode[] => {
    const parent = vfs[folderId];
    if (!parent || parent.type !== 'folder' || !parent.children) {
      return [];
    }

    return parent.children
      .map((id) => vfs[id])
      .filter((node): node is VfsNode => Boolean(node))
      .filter((node) => !node.isTrashed);
  },

  getPath: (id: string): VfsNode[] => {
    const path: VfsNode[] = [];
    let current: VfsNode | undefined = vfs[id];

    while (current) {
      path.unshift(current);
      current = current.parent ? vfs[current.parent] : undefined;
    }

    return path;
  },

  search: (folderId: string, query: string): VfsNode[] => {
    const lowerQuery = query.trim().toLowerCase();
    if (!lowerQuery) return [];

    const results: VfsNode[] = [];

    const walk = (nodeId: string) => {
      const node = vfs[nodeId];
      if (!node || node.isTrashed) return;

      if (node.id !== folderId && node.name.toLowerCase().includes(lowerQuery)) {
        results.push(node);
      }

      if (node.type === 'folder' && node.children) {
        node.children.forEach((childId) => walk(childId));
      }
    };

    walk(folderId);
    return results;
  },

  createFile: (parentId: string, fileName: string, size: number, mimeType: string, content?: string): VfsNode => {
    ensureFolder(parentId);

    const timestamp = nowIso();
    const file: VfsNode = {
      id: newId(),
      name: fileName,
      type: 'file',
      parent: parentId,
      size,
      mimeType,
      content,
      createdAt: timestamp,
      updatedAt: timestamp,
      permission: 'owner',
      isStarred: false,
      hash: `mock-hash-${Mock.Random.string('lower', 12)}`,
      virusStatus: 'clean',
    };

    vfs[file.id] = file;
    appendChild(parentId, file.id);
    saveVfs();
    return file;
  },

  createFolder: (parentId: string, folderName: string): VfsNode => {
    ensureFolder(parentId);

    const timestamp = nowIso();
    const folder: VfsNode = {
      id: newId(),
      name: folderName,
      type: 'folder',
      parent: parentId,
      children: [],
      createdAt: timestamp,
      updatedAt: timestamp,
      permission: 'owner',
      isStarred: false,
    };

    vfs[folder.id] = folder;
    appendChild(parentId, folder.id);
    saveVfs();
    return folder;
  },

  rename: (id: string, newName: string): VfsNode => {
    const node = vfs[id];
    if (!node) {
      throw new Error('Node not found');
    }

    node.name = newName;
    node.updatedAt = nowIso();
    saveVfs();
    return node;
  },

  move: (id: string, targetParentId: string): VfsNode => {
    if (id === 'root') {
      throw new Error('Root folder cannot be moved');
    }

    const node = vfs[id];
    if (!node) {
      throw new Error('Node not found');
    }

    ensureFolder(targetParentId);

    if (node.parent === targetParentId) {
      return node;
    }

    if (node.type === 'folder') {
      let cursor = targetParentId;
      while (cursor) {
        if (cursor === id) {
          throw new Error('Cannot move a folder into itself');
        }
        const cursorNode = vfs[cursor];
        cursor = cursorNode?.parent || '';
      }
    }

    removeChild(node.parent, id);
    node.parent = targetParentId;
    node.updatedAt = nowIso();
    appendChild(targetParentId, id);
    saveVfs();
    return node;
  },

  copy: (id: string, targetParentId: string, newName?: string): VfsNode => {
    ensureFolder(targetParentId);
    const newIdValue = cloneNodeRecursively(id, targetParentId, newName);
    const copied = vfs[newIdValue];
    saveVfs();
    return copied;
  },

  setStarred: (id: string, isStarred: boolean): VfsNode => {
    const node = vfs[id];
    if (!node) {
      throw new Error('Node not found');
    }

    node.isStarred = isStarred;
    node.starredAt = isStarred ? nowIso() : undefined;
    node.updatedAt = nowIso();
    saveVfs();
    return node;
  },

  getStarred: (): VfsNode[] => {
    return Object.values(vfs)
      .filter((node) => !node.isTrashed && node.id !== 'root' && node.isStarred)
      .sort((left, right) => {
        const leftTs = new Date(left.starredAt || left.updatedAt || left.createdAt).getTime();
        const rightTs = new Date(right.starredAt || right.updatedAt || right.createdAt).getTime();
        if (rightTs !== leftTs) {
          return rightTs - leftTs;
        }
        return right.id.localeCompare(left.id);
      });
  },

  delete: (id: string) => {
    if (id === 'root') return;
    const node = vfs[id];
    if (!node) return;

    removeChild(node.parent, id);

    const deletedAt = nowIso();
    markSubtree(id, (entry) => {
      entry.isTrashed = true;
      entry.deletedAt = deletedAt;
      entry.updatedAt = deletedAt;
    });

    saveVfs();
  },

  restore: (id: string) => {
    const node = vfs[id];
    if (!node) return;

    const restoreAncestors = (nodeId: string) => {
      const current = vfs[nodeId];
      if (!current || !current.parent) return;
      const parent = vfs[current.parent];
      if (!parent) return;

      if (parent.isTrashed) {
        restoreAncestors(parent.id);
        parent.isTrashed = false;
        parent.deletedAt = undefined;
      }

      appendChild(parent.id, current.id);
    };

    restoreAncestors(id);

    markSubtree(id, (entry) => {
      entry.isTrashed = false;
      entry.deletedAt = undefined;
      entry.updatedAt = nowIso();
    });

    saveVfs();
  },

  permanentDelete: (id: string) => {
    if (id === 'root') return;
    const node = vfs[id];
    if (!node) return;

    removeChild(node.parent, id);

    const erase = (nodeId: string) => {
      const target = vfs[nodeId];
      if (!target) return;
      if (target.type === 'folder' && target.children) {
        [...target.children].forEach((childId) => erase(childId));
      }
      delete vfs[nodeId];
    };

    erase(id);
    saveVfs();
  },

  clearRecycleBin: () => {
    const trashedNodes = Object.values(vfs)
      .filter((node) => node.isTrashed)
      .sort((a, b) => (b.type === 'folder' ? 1 : 0) - (a.type === 'folder' ? 1 : 0));

    let fileCount = 0;
    let folderCount = 0;
    let totalSize = 0;

    trashedNodes.forEach((node) => {
      if (!vfs[node.id]) return;
      if (node.type === 'file') {
        fileCount += 1;
        totalSize += node.size || 0;
      } else {
        folderCount += 1;
      }
      vfsApi.permanentDelete(node.id);
    });

    saveVfs();
    return {
      filesDeleted: fileCount,
      foldersDeleted: folderCount,
      totalStorageFreed: totalSize,
    };
  },

  getFolderStats: (folderId: string) => {
    const node = vfs[folderId];
    if (!node || node.type !== 'folder') {
      throw new Error('Folder not found');
    }

    const stats = collectSubtreeStats(folderId);
    return {
      totalSize: stats.totalSize,
      fileCount: stats.fileCount,
      folderCount: Math.max(stats.folderCount - 1, 0),
    };
  },

  resetVfs: () => {
    vfs = JSON.parse(JSON.stringify(initialVfs));
    saveVfs();
    return vfs;
  },

  debugVfs: () => {
    return {
      nodes: Object.keys(vfs).length,
      rootChildren: vfs.root?.children || [],
      trashed: Object.values(vfs).filter((node) => node.isTrashed).map((node) => node.id),
    };
  },
};

if (import.meta.env.DEV) {
  (window as any).vfsDebug = {
    reset: vfsApi.resetVfs,
    debug: vfsApi.debugVfs,
    getVfs: vfsApi.getAll,
  };
}
