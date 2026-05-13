import Mock from 'mockjs';
import { addLog, createMockId, mockSharedItems, mockShares, paginate } from '../state';
import { vfsApi } from '../vfs';

function sanitizeShare<T extends { settings?: any }>(share: T) {
  if (!share.settings) return share;
  return {
    ...share,
    settings: {
      ...share.settings,
      password: undefined,
    },
  };
}

function buildMockFileBlob(file: { name: string; mimeType?: string; content?: string }) {
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

  if (file.mimeType === 'application/pdf') {
    const text = `%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF`;
    return new Blob([text], { type: 'application/pdf' });
  }

  return new Blob([`Binary file: ${file.name}`], { type: file.mimeType || 'application/octet-stream' });
}

function resolveSharedPreviewNode(node: any) {
  if (!node?.mediaOptimization) {
    return node;
  }
  if (node.mediaOptimization.status === 'ready') {
    return {
      ...node,
      mimeType: node.mediaOptimization.optimizedMimeType || node.mimeType,
    };
  }
  return node;
}

function generatePassword() {
  return Mock.Random.string('number', 6);
}

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
    const paged = paginate(mockShares, page, perPage);

    return {
      success: true,
      code: 200,
      data: {
        ...paged,
        items: paged.items.map((item) => sanitizeShare(item)),
      },
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
      data: sanitizeShare(share),
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

    if (share.settings.passwordProtected && password !== share.settings.password) {
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
          download: share.settings.allowDownload ? `/api/v1/shares/${share.shareLink}/download` : '',
          preview: share.settings.allowPreview ? `/api/v1/shares/${share.shareLink}/preview` : '',
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)\/settings$/, 'patch', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/]+)\/settings/) || [])[1];
    const payload = JSON.parse(options.body || '{}') as Partial<{
      passwordProtected: boolean;
      password: string;
      regeneratePassword: boolean;
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

    const nextPasswordProtected = payload.passwordProtected ?? share.settings.passwordProtected;
    share.settings.passwordProtected = nextPasswordProtected;
    share.settings.expireAt = payload.expireAt === undefined ? share.settings.expireAt : payload.expireAt;
    share.settings.allowDownload = payload.allowDownload ?? share.settings.allowDownload;
    share.settings.allowPreview = payload.allowPreview ?? share.settings.allowPreview;

    let issuedPassword: string | undefined;
    if (!nextPasswordProtected) {
      share.settings.password = undefined;
    } else {
      const wantsRegenerate = Boolean(payload.regeneratePassword);
      const customPassword = payload.password?.trim();
      const needsAutoGenerate = !share.settings.password;

      if (wantsRegenerate || customPassword || needsAutoGenerate) {
        issuedPassword = customPassword || generatePassword();
        share.settings.password = issuedPassword;
      }
    }

    addLog('share_settings_update', {
      shareId: share.shareId,
      allowDownload: share.settings.allowDownload ? 1 : 0,
      allowPreview: share.settings.allowPreview ? 1 : 0,
    });

    return {
      success: true,
      code: 200,
      data: {
        ...sanitizeShare(share),
        settings: {
          ...sanitizeShare(share).settings,
          ...(issuedPassword ? { password: issuedPassword } : {}),
        },
      },
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

  Mock.mock(/\/api\/v1\/shares\/([^/]+)\/save$/, 'post', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/]+)\/save/) || [])[1];
    const { targetFolderId } = JSON.parse(options.body || '{}');
    const share = mockShares.find((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (!share) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    try {
      const copied = vfsApi.copy(share.itemInfo.id, targetFolderId || 'root');
      addLog('shared_item_accept', { shareId: share.shareId, targetFolderId, savedId: copied.id });
      return {
        success: true,
        code: 201,
        data: {
          savedAt: new Date().toISOString(),
          itemType: share.itemType,
          itemId: copied.id,
          targetFolderId: targetFolderId || 'root',
        },
      };
    } catch (error) {
      return {
        success: false,
        code: 400,
        message: (error as Error).message || 'Failed to save share',
        data: null,
      };
    }
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)\/download$/, 'get', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/]+)\/download/) || [])[1];
    const share = mockShares.find((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (!share) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    if (share.itemType !== 'file') {
      return {
        success: false,
        code: 400,
        message: 'Only file shares support download',
        data: null,
      };
    }

    if (!share.settings.allowDownload) {
      return {
        success: false,
        code: 403,
        message: 'Download not allowed',
        data: null,
      };
    }

    const node = vfsApi.get(share.itemInfo.id);
    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    addLog('file_download', { shareId: share.shareId, fileId: node.id, fileName: node.name });
    return buildMockFileBlob(node);
  });

  Mock.mock(/\/api\/v1\/shares\/([^/]+)\/preview$/, 'get', (options) => {
    const shareLink = (options.url.match(/\/api\/v1\/shares\/([^/]+)\/preview/) || [])[1];
    const share = mockShares.find((item) => item.shareLink === shareLink || item.shareId === shareLink);

    if (!share) {
      return {
        success: false,
        code: 404,
        message: 'Share not found',
        data: null,
      };
    }

    if (share.itemType !== 'file') {
      return {
        success: false,
        code: 400,
        message: 'Only file shares support preview',
        data: null,
      };
    }

    if (!share.settings.allowPreview) {
      return {
        success: false,
        code: 403,
        message: 'Preview not allowed',
        data: null,
      };
    }

    const node = vfsApi.get(share.itemInfo.id);
    if (!node || node.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
        data: null,
      };
    }

    return buildMockFileBlob(resolveSharedPreviewNode(node));
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
