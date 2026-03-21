import Mock from 'mockjs';
import { addLog, createMockId, mockSharedItems, mockShares, paginate } from '../state';
import { vfsApi } from '../vfs';

function sortSharedItems<T extends { [key: string]: any }>(items: T[], sort: string | null, order: string | null) {
  const sortField = sort || 'sharedAt';
  const direction = order === 'asc' ? 1 : -1;

  return [...items].sort((a, b) => {
    const av = a[sortField];
    const bv = b[sortField];

    if (typeof av === 'number' && typeof bv === 'number') {
      return (av - bv) * direction;
    }

    return String(av || '').localeCompare(String(bv || ''), undefined, { sensitivity: 'base' }) * direction;
  });
}

export const setupShareMocks = () => {
  Mock.mock(/\/api\/v1\/shares$/, 'post', (options) => {
    const { resourceType, resourceId } = JSON.parse(options.body || '{}');
    const resource = vfsApi.get(resourceId);

    if (!resource || resource.type !== resourceType) {
      return {
        success: false,
        code: 404,
        message: 'Resource not found',
        data: null,
      };
    }

    const shareLink = Mock.Random.string('upper', 6);
    const share = {
      shareId: createMockId('share'),
      shareLink,
      ownerUserId: 'user1',
      itemType: resourceType,
      itemInfo: {
        id: resource.id,
        name: resource.name,
        size: resource.type === 'folder' ? vfsApi.getFolderStats(resource.id).totalSize : resource.size || 0,
        mimeType: resource.mimeType || (resource.type === 'folder' ? 'inode/directory' : 'application/octet-stream'),
        folderPath: vfsApi
          .getPath(resource.id)
          .slice(0, -1)
          .map((node) => node.name)
          .join('/'),
      },
      settings: {
        passwordProtected: false,
        expireAt: null,
        allowDownload: true,
        allowPreview: true,
      },
      createdAt: new Date().toISOString(),
      visitCount: 0,
      downloadCount: 0,
    };

    mockShares.unshift(share);
    addLog('file_share', { resourceId, shareId: share.shareId, shareLink });

    return {
      success: true,
      code: 201,
      data: share,
    };
  });

  Mock.mock(/\/api\/v1\/shares(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);

    return {
      success: true,
      code: 200,
      data: paginate(mockShares, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)$/, 'get', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/?]+)/) || [])[1];
    const share = mockShares.find((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (!share) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    return {
      success: true,
      code: 200,
      data: share,
    };
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)\/access$/, 'post', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/]+)\/access/) || [])[1];
    const { password } = JSON.parse(options.body || '{}');
    const share = mockShares.find((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (!share) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    if (share.settings.passwordProtected && password !== '123456') {
      return {
        success: false,
        code: 403,
        message: 'Invalid share password',
        data: null,
      };
    }

    if (share.settings.expireAt && new Date(share.settings.expireAt).getTime() < Date.now()) {
      return {
        success: false,
        code: 410,
        message: 'Share link expired',
        data: null,
      };
    }

    share.visitCount = (share.visitCount || 0) + 1;

    return {
      success: true,
      code: 200,
      data: {
        accessToken: createMockId('access'),
        expiresIn: 1800,
        itemType: share.itemType,
        itemInfo: share.itemInfo,
        accessUrls: {
          download: share.settings.allowDownload ? `/api/v1/files/${share.itemInfo.id}/download` : '',
          preview: share.settings.allowPreview ? `/api/v1/files/${share.itemInfo.id}/preview` : '',
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)\/settings$/, 'patch', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/]+)\/settings/) || [])[1];
    const payload = JSON.parse(options.body || '{}') as Partial<{
      passwordProtected: boolean;
      expireAt: string | null;
      allowDownload: boolean;
      allowPreview: boolean;
    }>;
    const share = mockShares.find((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (!share) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    share.settings = {
      passwordProtected: payload.passwordProtected ?? share.settings.passwordProtected,
      expireAt: payload.expireAt === undefined ? share.settings.expireAt : payload.expireAt,
      allowDownload: payload.allowDownload ?? share.settings.allowDownload,
      allowPreview: payload.allowPreview ?? share.settings.allowPreview,
    };

    addLog('share_settings_update', {
      shareId: share.shareId,
      allowDownload: share.settings.allowDownload ? 1 : 0,
      allowPreview: share.settings.allowPreview ? 1 : 0,
    });

    return {
      success: true,
      code: 200,
      data: share,
    };
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)$/, 'delete', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/?]+)/) || [])[1];
    const index = mockShares.findIndex((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (index === -1) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    const removed = mockShares.splice(index, 1)[0];
    addLog('share_delete', { shareId: removed.shareId, shareLink: removed.shareLink });

    return {
      success: true,
      code: 200,
      data: {
        shareId: removed.shareId,
        shareLink: removed.shareLink,
        deletedAt: new Date().toISOString(),
      },
    };
  });

  Mock.mock(/\/api\/v1\/shared-items(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);
    const sort = url.searchParams.get('sort');
    const order = url.searchParams.get('order');

    const sorted = sortSharedItems(mockSharedItems, sort, order);

    return {
      success: true,
      code: 200,
      data: paginate(sorted, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/shared-items\/([^/]+)\/accept$/, 'post', (options) => {
    const itemId = (options.url.match(/\/api\/v1\/shared-items\/([^/]+)\/accept/) || [])[1];
    const item = mockSharedItems.find((entry) => entry.id === itemId);

    if (!item) {
      return {
        success: false,
        code: 404,
        message: 'Shared item not found',
        data: null,
      };
    }

    if (item.itemType === 'folder') {
      vfsApi.createFolder('root', `${item.name} (Shared)`);
    } else {
      vfsApi.createFile('root', `${item.name}`, item.size, item.mimeType || 'application/octet-stream');
    }

    addLog('shared_item_accept', { itemId, itemName: item.name });

    return {
      success: true,
      code: 200,
      data: {
        accepted: true,
        acceptedAt: new Date().toISOString(),
        itemId,
      },
    };
  });
};
