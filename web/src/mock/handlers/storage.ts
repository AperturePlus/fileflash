import Mock from 'mockjs';
import { addLog, getCurrentUser, mockUsers } from '../state';
import { vfsApi } from '../vfs';

function computeStorageStats() {
  const nodes = Object.values(vfsApi.getAll()).filter((node) => !node.isTrashed);
  const files = nodes.filter((node) => node.type === 'file');
  const folders = nodes.filter((node) => node.type === 'folder' && node.id !== 'root');

  const storageUsed = files.reduce((sum, node) => sum + (node.size || 0), 0);
  const currentUser = getCurrentUser();
  const storageLimit = currentUser.storageLimit || 100 * 1024 * 1024 * 1024;

  const bucket = {
    documents: { size: 0, count: 0 },
    images: { size: 0, count: 0 },
    videos: { size: 0, count: 0 },
    audio: { size: 0, count: 0 },
    archives: { size: 0, count: 0 },
    others: { size: 0, count: 0 },
  };

  files.forEach((file) => {
    const size = file.size || 0;
    const mime = file.mimeType || '';

    if (mime.startsWith('image/')) {
      bucket.images.size += size;
      bucket.images.count += 1;
    } else if (mime.startsWith('video/')) {
      bucket.videos.size += size;
      bucket.videos.count += 1;
    } else if (mime.startsWith('audio/')) {
      bucket.audio.size += size;
      bucket.audio.count += 1;
    } else if (mime.includes('zip') || mime.includes('compressed')) {
      bucket.archives.size += size;
      bucket.archives.count += 1;
    } else if (mime.includes('pdf') || mime.includes('sheet') || mime.includes('word') || mime.startsWith('text/')) {
      bucket.documents.size += size;
      bucket.documents.count += 1;
    } else {
      bucket.others.size += size;
      bucket.others.count += 1;
    }
  });

  return {
    storage_limit: storageLimit,
    storage_used: storageUsed,
    storage_available: Math.max(storageLimit - storageUsed, 0),
    storage_percentage: Number(((storageUsed / storageLimit) * 100).toFixed(2)),
    file_count: files.length,
    folder_count: folders.length,
    breakdown: bucket,
  };
}

export const setupStorageMocks = () => {
  Mock.mock(/\/api\/v1\/storage\/statistics$/, 'get', () => {
    return {
      success: true,
      code: 200,
      data: computeStorageStats(),
    };
  });

  Mock.mock(/\/api\/v1\/storage\/summary$/, 'get', () => {
    return {
      success: true,
      code: 200,
      data: computeStorageStats(),
    };
  });

  Mock.mock(/\/api\/v1\/storage\/usage-trend(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const days = Math.min(Number(url.searchParams.get('days') || 7), 30);
    const currentUsed = computeStorageStats().storage_used;

    const trends = Array.from({ length: days }).map((_, index) => {
      const dayIndex = days - index - 1;
      const date = new Date(Date.now() - dayIndex * 24 * 60 * 60 * 1000);
      const dailyUsed = Math.max(currentUsed - dayIndex * 12000000 + Mock.Random.integer(-4000000, 4000000), 0);

      return {
        date: date.toISOString().split('T')[0],
        used: dailyUsed,
      };
    });

    return {
      success: true,
      code: 200,
      data: {
        trends,
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/storage\/users$/, 'get', () => {
    const items = mockUsers.map((user) => ({
      userId: user.userId,
      username: user.username,
      email: user.email,
      storageUsed: user.storageUsed,
      storageLimit: user.storageLimit,
      usagePercentage: Number(((user.storageUsed / user.storageLimit) * 100).toFixed(2)),
      status: user.status,
    }));

    return {
      success: true,
      code: 200,
      data: {
        items,
        pagination: {
          totalItems: items.length,
          totalPages: 1,
          perPage: items.length,
          currentPage: 1,
          hasPrev: false,
          hasNext: false,
        },
      },
    };
  });

  Mock.mock(/\/api\/v1\/admin\/storage\/users\/([^/]+)\/quota$/, 'patch', (options) => {
    const userId = (options.url.match(/\/api\/v1\/admin\/storage\/users\/([^/]+)\/quota/) || [])[1];
    const { storageLimit } = JSON.parse(options.body || '{}');

    if (!Number.isFinite(storageLimit) || Number(storageLimit) <= 0) {
      return {
        success: false,
        code: 400,
        message: 'storageLimit must be a positive number',
        data: null,
      };
    }

    const target = mockUsers.find((user) => user.userId === userId);
    if (!target) {
      return {
        success: false,
        code: 404,
        message: 'User not found',
        data: null,
      };
    }

    target.storageLimit = Number(storageLimit);
    addLog('admin_storage_quota_update', { userId: target.userId, storageLimit: target.storageLimit });

    return {
      success: true,
      code: 200,
      data: {
        userId: target.userId,
        storageLimit: target.storageLimit,
        storageUsed: target.storageUsed,
        usagePercentage: Number(((target.storageUsed / target.storageLimit) * 100).toFixed(2)),
        updatedAt: new Date().toISOString(),
      },
    };
  });
};
