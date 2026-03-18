import Mock from 'mockjs';

// --- Types ---
export interface VfsNode {
  id: string;
  name: string;
  type: 'folder' | 'file';
  parent: string | null;
  children?: string[];
  size?: number;
  mimeType?: string;
  content?: string; // Base64 encoded content for files
  createdAt: string;
  updatedAt: string;
  permission?: 'read' | 'write' | 'owner';
  isTrashed?: boolean;
  deletedAt?: string;
}

export interface Vfs {
  [key: string]: VfsNode;
}

// --- Constants ---
//load from .env file
const VFS_STORAGE_KEY = import.meta.env.VFS_STORAGE_KEY || 'fileflash-vfs';

// --- Initial Data ---
const initialVfs: Vfs = {
  'root': { id: 'root', name: 'My Files', type: 'folder', parent: null, children: ['folder1', 'file1', 'file3', 'file4', 'file5', 'file6'], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'folder1': { id: 'folder1', name: 'Work Documents', type: 'folder', parent: 'root', children: ['file2'], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'file1': { id: 'file1', name: 'notes.txt', type: 'file', parent: 'root', size: 1024, mimeType: 'text/plain', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'file2': { id: 'file2', name: 'project-brief.docx', type: 'file', parent: 'folder1', size: 20480, mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'file3': { id: 'file3', name: 'main.py', type: 'file', parent: 'root', size: 5120, mimeType: 'text/x-python', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'file4': { id: 'file4', name: 'archive.zip', type: 'file', parent: 'root', size: 102400, mimeType: 'application/zip', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'file5': { id: 'file5', name: 'logo.png', type: 'file', parent: 'root', size: 12288, mimeType: 'image/png', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
  'file6': { id: 'file6', name: 'installer.exe', type: 'file', parent: 'root', size: 512000, mimeType: 'application/x-msdownload', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), permission: 'owner' },
};

// --- VFS Singleton ---
let vfs: Vfs;

function saveVfs() {
  localStorage.setItem(VFS_STORAGE_KEY, JSON.stringify(vfs));
}

function loadVfs(): Vfs {
  const storedVfs = localStorage.getItem(VFS_STORAGE_KEY);
  if (storedVfs) {
    try {
      const parsed = JSON.parse(storedVfs);
      
      // 验证VFS数据完整性
      if (parsed.root && parsed.root.children) {
        const rootChildren = parsed.root.children;
        const childIds = new Set();
        let hasDuplicates = false;
        
        rootChildren.forEach((childId: string) => {
          if (childIds.has(childId)) {
            hasDuplicates = true;
            console.error('🚨 VFS: Duplicate child ID detected:', childId);
          }
          childIds.add(childId);
        });
        
        if (hasDuplicates) {
          console.log('🔧 VFS: Cleaning up duplicate children in root folder');
          parsed.root.children = [...childIds]; // Remove duplicates
        }
      }
      
      return parsed;
    } catch (e) {
      console.error("Failed to parse VFS from localStorage, resetting.", e);
    }
  }
  return initialVfs;
}

// Initialize VFS
vfs = loadVfs();
saveVfs(); // Ensure it's saved on first load if it didn't exist

// --- VFS API ---
export const vfsApi = {
  get: (id: string): VfsNode | undefined => vfs[id],
  getAll: (): Vfs => vfs,
  
  getChildren: (folderId: string): VfsNode[] => {
    const parent = vfs[folderId];
    if (parent && parent.type === 'folder' && parent.children) {
      return parent.children
        .map(id => vfs[id])
        .filter(Boolean)
        .filter(item => !item.isTrashed); // Filter out trashed items from normal view
    }
    return [];
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

  createFile: (parentId: string, fileName: string, size: number, mimeType: string, content?: string): VfsNode => {
    const newId = Mock.Random.guid();
    const now = new Date().toISOString();
    const newFile: VfsNode = {
      id: newId,
      name: fileName,
      type: 'file',
      parent: parentId,
      size,
      mimeType,
      content,
      createdAt: now,
      updatedAt: now,
      permission: 'owner', // New files created by the user are owned by them
    };
    vfs[newId] = newFile;
    // Ensure parent folder exists and has a children array
    if (vfs[parentId] && vfs[parentId].children) {
      vfs[parentId].children?.push(newId);
    }
    saveVfs();
    return newFile;
  },
  
  createFolder: (parentId: string, folderName: string): VfsNode => {
    const newId = Mock.Random.guid();
    const now = new Date().toISOString();
    const newFolder: VfsNode = {
      id: newId,
      name: folderName,
      type: 'folder',
      parent: parentId,
      children: [],
      createdAt: now,
      updatedAt: now,
      permission: 'owner',
    };
    vfs[newId] = newFolder;
    // Ensure parent folder exists and has a children array
    if (vfs[parentId] && vfs[parentId].children) {
      vfs[parentId].children?.push(newId);
    }
    saveVfs();
    return newFolder;
  },

  rename: (id: string, newName: string): VfsNode => {
    vfs[id].name = newName;
    vfs[id].updatedAt = new Date().toISOString();
    saveVfs();
    return vfs[id];
  },
  
  move: (id: string, targetParentId: string): VfsNode => {
    const node = vfs[id];
    if (!node) throw new Error("Node to move not found");

    const oldParentId = node.parent;
    if (oldParentId && vfs[oldParentId]?.children) {
      const children = vfs[oldParentId].children!;
      const index = children.indexOf(id);
      if (index > -1) {
        children.splice(index, 1);
      }
    }
    
    node.parent = targetParentId;
    vfs[targetParentId].children?.push(id);
    node.updatedAt = new Date().toISOString();
    
    saveVfs();
    return node;
  },

  delete: (id: string) => {
    const node = vfs[id];
    if (!node) return;

    // Remove from parent's children list
    if (node.parent && vfs[node.parent]?.children) {
      const children = vfs[node.parent].children!;
      const index = children.indexOf(id);
      if (index > -1) {
        children.splice(index, 1);
      }
    }

    // Mark as trashed
    node.isTrashed = true;
    node.deletedAt = new Date().toISOString();

    // No recursive action. If a folder is deleted, its children are still in the VFS
    // but are effectively inaccessible until the parent folder is restored.
    saveVfs();
  },

  restore: (id: string) => {
    const node = vfs[id];
    if (!node) return;

    // Un-mark as trashed
    node.isTrashed = false;
    delete node.deletedAt;

    // Add back to parent's children list
    if (node.parent && vfs[node.parent]?.children) {
      if (!vfs[node.parent].children!.includes(id)) {
        vfs[node.parent].children!.push(id);
      }
    }
    
    // If a folder is restored, we need to recursively restore its children
    if (node.type === 'folder' && node.children) {
        // This is tricky. The simplest way is to not recursively trash.
        // Let's assume for now children are not marked as trashed when parent is.
    }

    saveVfs();
  },
  
  permanentDelete: (id: string) => {
    const node = vfs[id];
    if (!node) return;
    
    // Recursively delete children if it's a folder
    if (node.type === 'folder' && node.children) {
      // Make a copy of children array before iterating
      [...node.children].forEach(childId => vfsApi.permanentDelete(childId));
    }
    
    // Parent's children list is already updated when item was trashed.
    
    delete vfs[id];
    saveVfs();
  },

  // --- Development helpers ---
  resetVfs: () => {
    console.log('🔄 Resetting VFS to initial state...');
    vfs = JSON.parse(JSON.stringify(initialVfs)); // Deep clone
    saveVfs();
    console.log('✅ VFS reset complete');
    return vfs;
  },
  
  debugVfs: () => {
    console.log('🔍 VFS Debug Info:');
    console.log('Root children:', vfs.root?.children);
    console.log('All nodes:', Object.keys(vfs));
    
    if (vfs.root?.children) {
      const duplicates = vfs.root.children.filter((id, index, arr) => arr.indexOf(id) !== index);
      if (duplicates.length > 0) {
        console.error('❌ Found duplicate children:', duplicates);
      } else {
        console.log('✅ No duplicate children found');
      }
    }
    
    return vfs;
  },
};

// 在开发环境中暴露调试功能到全局
if (import.meta.env.DEV) {
  (window as any).vfsDebug = {
    reset: vfsApi.resetVfs,
    debug: vfsApi.debugVfs,
    getVfs: vfsApi.getAll
  };
  console.log('🛠️ VFS Debug tools available: vfsDebug.reset(), vfsDebug.debug(), vfsDebug.getVfs()');
} 