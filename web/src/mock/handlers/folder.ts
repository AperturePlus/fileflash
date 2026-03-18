import Mock from 'mockjs';
import { vfsApi } from '../vfs';

export const setupFolderMocks = () => {
  // Get Folder Contents
  Mock.mock(/\/api\/v1\/folders\/([^\/]+)(?:\?.*)?$/, 'get', (options) => {
    const match = options.url.match(/\/api\/v1\/folders\/([^\/]+)(?:\?.*)?$/);
    const folderId = match ? match[1] : 'root';
    console.log('🔍 Mock API: Getting contents for folder', folderId);
    
    const children = vfsApi.getChildren(folderId);
    console.log('📁 Mock API: Found', children.length, 'children for folder', folderId);

    // 检查VFS节点是否存在
    const folderNode = vfsApi.get(folderId);
    if (!folderNode) {
      console.error('🚨 Mock API: Folder not found in VFS:', folderId);
      return {
        success: false,
        code: 404,
        message: `Folder ${folderId} not found`,
        data: null,
      };
    }

    // 简化API调试输出
    const childIds = children.map(c => c.id);
    const uniqueChildIds = new Set(childIds);
    if (childIds.length !== uniqueChildIds.size) {
      console.error('🚨 Mock API: VFS has duplicate children for folder', folderId);
    }

    const response = {
      success: true,
      code: 200,
      data: {
        items: children.map(c => ({...c, itemType: c.type, permission: c.permission || 'owner' })), // Ensure permission is passed
        pagination: { totalItems: children.length, totalPages: 1, perPage: children.length, currentPage: 1 },
      },
    };
    
    console.log('📤 Mock API: Returning response:', {
      success: response.success,
      itemCount: response.data.items.length,
      firstItem: response.data.items[0]
    });

    return response;
  });

  // Get Folder Path
  Mock.mock(/\/api\/v1\/folders\/([^\/]+)\/path$/, 'get', (options) => {
    const match = options.url.match(/\/api\/v1\/folders\/([^\/]+)\/path$/);
    const folderId = match ? match[1] : 'root';
    console.log('🔍 Mock API: Getting path for folder', folderId);
    
    const folderNode = vfsApi.get(folderId);
    if (!folderNode) {
      console.error('🚨 Mock API: Folder not found in VFS for path:', folderId);
      return {
        success: false,
        code: 404,
        message: `Folder ${folderId} not found`,
        data: null,
      };
    }
    
    const path = vfsApi.getPath(folderId);
    console.log('📤 Mock API: Returning path response:', {
      success: true,
      pathCount: path.length,
      pathItems: path.map(p => ({ folderId: p.id, name: p.name }))
    });
    
    return {
      success: true,
      code: 200,
      data: {
        pathItems: path.map(p => ({ folderId: p.id, name: p.name })),
      },
    };
  });

  // Create Folder
  Mock.mock(/\/api\/v1\/folders/, 'post', (options) => {
    const { folderName, parentFolderId } = JSON.parse(options.body);
    const newFolder = vfsApi.createFolder(parentFolderId, folderName);
    
    return {
      success: true,
      code: 201,
      data: newFolder,
    };
  });

  // Delete Folder
  Mock.mock(/\/api\/v1\/folders\/([^\/]+)$/, 'delete', (options) => {
    const match = options.url.match(/\/api\/v1\/folders\/([^\/]+)$/);
    const folderId = match ? match[1] : '';
    vfsApi.delete(folderId);
    return { success: true, code: 200, data: { folderId, message: 'Folder moved to trash.' } };
  });

  // Move Folder
  Mock.mock(/\/api\/v1\/folders\/([^\/]+)\/move$/, 'patch', (options) => {
    const match = options.url.match(/\/api\/v1\/folders\/([^\/]+)\/move$/);
    const folderId = match ? match[1] : '';
    const { targetParentId } = JSON.parse(options.body);
    const movedFolder = vfsApi.move(folderId, targetParentId);
    return { success: true, code: 200, data: movedFolder };
  });
}; 