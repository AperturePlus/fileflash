import Mock from 'mockjs';
import { createMockId, mockPermissions, mockUsers, paginate } from '../state';

const mockGroups = [
  { id: 'group1', name: 'Developers' },
  { id: 'group2', name: 'Designers' },
  { id: 'group3', name: 'Operations' },
];

export const setupPermissionMocks = () => {
  Mock.mock(/\/api\/v1\/permissions(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const fileId = url.searchParams.get('fileId');
    const folderId = url.searchParams.get('folderId');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);

    const filtered = mockPermissions.filter((permission) => {
      if (fileId) return permission.itemType === 'file' && permission.itemId === fileId;
      if (folderId) return permission.itemType === 'folder' && permission.itemId === folderId;
      return true;
    });

    return {
      success: true,
      code: 200,
      data: paginate(filtered, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/permissions$/, 'post', (options) => {
    const payload = JSON.parse(options.body || '{}');
    const { fileId, folderId, userId, groupId, permission } = payload;

    const itemType = fileId ? 'file' : folderId ? 'folder' : null;
    const itemId = fileId || folderId;

    if (!itemType || !itemId || !permission) {
      return {
        success: false,
        code: 400,
        message: 'Invalid permission payload',
        data: null,
      };
    }

    let grantedTo: { type: 'user' | 'group'; id: string; name: string } | null = null;

    if (userId) {
      const user = mockUsers.find((entry) => entry.userId === userId);
      grantedTo = {
        type: 'user',
        id: userId,
        name: user?.username || `User ${userId}`,
      };
    }

    if (groupId) {
      const group = mockGroups.find((entry) => entry.id === groupId);
      grantedTo = {
        type: 'group',
        id: groupId,
        name: group?.name || `Group ${groupId}`,
      };
    }

    if (!grantedTo) {
      return {
        success: false,
        code: 400,
        message: 'Either userId or groupId is required',
        data: null,
      };
    }

    const created = {
      permissionId: createMockId('perm'),
      itemType,
      itemId,
      grantedTo,
      permission,
      createdAt: new Date().toISOString(),
    };

    mockPermissions.unshift(created as any);

    return {
      success: true,
      code: 201,
      data: created,
    };
  });

  Mock.mock(/\/api\/v1\/permissions\/([^/]+)$/, 'put', (options) => {
    const permissionId = (options.url.match(/\/api\/v1\/permissions\/([^/?]+)/) || [])[1];
    const { permission } = JSON.parse(options.body || '{}');

    const target = mockPermissions.find((item) => item.permissionId === permissionId);
    if (!target) {
      return {
        success: false,
        code: 404,
        message: 'Permission not found',
        data: null,
      };
    }

    target.permission = permission;

    return {
      success: true,
      code: 200,
      data: target,
    };
  });

  Mock.mock(/\/api\/v1\/permissions\/([^/]+)$/, 'delete', (options) => {
    const permissionId = (options.url.match(/\/api\/v1\/permissions\/([^/?]+)/) || [])[1];
    const index = mockPermissions.findIndex((item) => item.permissionId === permissionId);

    if (index === -1) {
      return {
        success: false,
        code: 404,
        message: 'Permission not found',
        data: null,
      };
    }

    const removed = mockPermissions.splice(index, 1)[0];

    return {
      success: true,
      code: 200,
      data: {
        permissionId: removed.permissionId,
        revokedPermission: removed.permission,
        deletedAt: new Date().toISOString(),
      },
    };
  });
};
