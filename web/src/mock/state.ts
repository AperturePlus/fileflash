import Mock from 'mockjs';
import type { PermissionItem } from '../types/permission';
import type { Share, SharedItem } from '../types/share';
import type { NotificationItem } from '../types/notification';
import type { LogItem } from '../types/log';
import type { User, UserPreference } from '../types/user';

export type MockUserRecord = User & {
  status: 'active' | 'suspended';
  role: 'user' | 'admin';
  password: string;
  preference: UserPreference;
};

const now = () => new Date().toISOString();

const randomRecentTime = (maxHours = 72) => {
  const offset = Math.floor(Math.random() * maxHours * 60 * 60 * 1000);
  return new Date(Date.now() - offset).toISOString();
};

let notificationId = 200;
let logId = 1000;

export const mockUsers: MockUserRecord[] = [
  {
    userId: 'user1',
    username: 'admin',
    email: 'admin@fileflash.mock',
    storageLimit: 107374182400,
    storageUsed: 21474836480,
    createdAt: '2025-01-10T09:30:00.000Z',
    status: 'active',
    role: 'admin',
    password: 'admin123',
    preference: {
      language: 'zh-CN',
    },
  },
  {
    userId: 'user2',
    username: 'demo',
    email: 'demo@example.com',
    storageLimit: 53687091200,
    storageUsed: 10737418240,
    createdAt: '2025-02-18T10:10:00.000Z',
    status: 'active',
    role: 'user',
    password: 'demo123',
    preference: {
      language: 'en-US',
    },
  },
  {
    userId: 'user3',
    username: 'Alice Chen',
    email: 'alice@example.com',
    storageLimit: 53687091200,
    storageUsed: 10737418240,
    createdAt: '2025-03-12T11:20:00.000Z',
    status: 'active',
    role: 'user',
    password: 'alice123',
    preference: {
      language: 'zh-CN',
    },
  },
  {
    userId: 'user4',
    username: 'Bob Wang',
    email: 'bob@example.com',
    storageLimit: 53687091200,
    storageUsed: 3435973836,
    createdAt: '2025-06-02T08:15:00.000Z',
    status: 'active',
    role: 'user',
    password: 'bob123',
    preference: {
      language: 'en-US',
    },
  },
  {
    userId: 'user5',
    username: 'Charlie Li',
    email: 'charlie@example.com',
    storageLimit: 53687091200,
    storageUsed: 17448304640,
    createdAt: '2025-08-01T06:05:00.000Z',
    status: 'suspended',
    role: 'user',
    password: 'charlie123',
    preference: {
      language: 'zh-CN',
    },
  },
];

export const mockShares: Array<Share & { ownerUserId: string }> = [
  {
    shareId: 'share_1001',
    shareLink: 'S8M3J5',
    ownerUserId: 'user1',
    itemType: 'file',
    itemInfo: {
      id: 'file2',
      name: 'project-plan.pdf',
      size: 256000,
      mimeType: 'application/pdf',
      folderPath: '/My Files',
    },
    settings: {
      passwordProtected: false,
      expireAt: null,
      allowDownload: true,
      allowPreview: true,
    },
    createdAt: randomRecentTime(),
    visitCount: 18,
    downloadCount: 7,
  },
  {
    shareId: 'share_1002',
    shareLink: 'X4D9Q2',
    ownerUserId: 'user1',
    itemType: 'folder',
    itemInfo: {
      id: 'folder1',
      name: 'Work Documents',
      size: 48370,
      mimeType: 'inode/directory',
      folderPath: '/My Files',
    },
    settings: {
      passwordProtected: true,
      expireAt: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000).toISOString(),
      allowDownload: true,
      allowPreview: false,
    },
    createdAt: randomRecentTime(),
    visitCount: 6,
    downloadCount: 2,
  },
];

export const mockSharedItems: SharedItem[] = [
  {
    itemType: 'file',
    id: 'shared_file_1',
    name: 'Q3 Financial Report.xlsx',
    size: 1572864,
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    sharedBy: 'Alice Chen',
    permission: 'write',
    sharedAt: randomRecentTime(),
  },
  {
    itemType: 'folder',
    id: 'shared_folder_1',
    name: 'Project Phoenix Assets',
    size: 268435456,
    sharedBy: 'Bob Wang',
    permission: 'read',
    sharedAt: randomRecentTime(),
  },
  {
    itemType: 'file',
    id: 'shared_file_2',
    name: 'Design Mockups.fig',
    size: 25165824,
    mimeType: 'application/figma',
    sharedBy: 'Charlie Li',
    permission: 'read',
    sharedAt: randomRecentTime(),
  },
];

export const mockPermissions: PermissionItem[] = [
  {
    permissionId: 'perm_1',
    itemType: 'file',
    itemId: 'file2',
    grantedTo: {
      type: 'user',
      id: 'user2',
      name: 'Alice Chen',
    },
    permission: 'write',
    createdAt: randomRecentTime(),
  },
  {
    permissionId: 'perm_2',
    itemType: 'folder',
    itemId: 'folder1',
    grantedTo: {
      type: 'group',
      id: 'group1',
      name: 'Developers',
    },
    permission: 'read',
    createdAt: randomRecentTime(),
  },
];

export const mockNotifications: NotificationItem[] = [
  {
    id: 1,
    message: 'Welcome to FileFlash. Your account is ready.',
    isRead: false,
    createdAt: randomRecentTime(),
  },
  {
    id: 2,
    message: 'Storage usage reached 80%. Consider cleanup.',
    isRead: false,
    createdAt: randomRecentTime(),
  },
  {
    id: 3,
    message: 'Security scan completed for uploaded files.',
    isRead: true,
    createdAt: randomRecentTime(),
  },
];

export const mockLogs: LogItem[] = Array.from({ length: 40 }).map((_, index) => {
  const operation = Mock.Random.pick([
    'file_upload',
    'file_download',
    'file_delete',
    'file_share',
    'folder_create',
    'user_login',
    'virus_scan',
    'rate_limit_trigger',
  ]);

  return {
    id: `log_${900 + index}`,
    operation,
    operationName: operation.split('_').join(' '),
    details: {
      message: `Mock event for ${operation}`,
      resource: Mock.Random.pick(['file2', 'file6', 'folder1', 'file8']),
      status: Mock.Random.pick(['ok', 'ok', 'ok', 'warning']),
    },
    ipAddress: Mock.Random.ip(),
    performedAt: randomRecentTime(240),
  };
});

export function createMockId(prefix: string) {
  return `${prefix}_${Mock.Random.string('number', 6)}`;
}

export function addNotification(message: string, isRead = false) {
  notificationId += 1;
  const item: NotificationItem = {
    id: notificationId,
    message,
    isRead,
    createdAt: now(),
  };
  mockNotifications.unshift(item);
  return item;
}

export function addLog(operation: string, details: Record<string, string | number>) {
  logId += 1;
  const item: LogItem = {
    id: `log_${logId}`,
    operation,
    operationName: operation.split('_').join(' '),
    details,
    ipAddress: Mock.Random.ip(),
    performedAt: now(),
  };
  mockLogs.unshift(item);
  return item;
}

export function paginate<T>(items: T[], page = 1, perPage = 20) {
  const normalizedPage = Number.isFinite(page) && page > 0 ? page : 1;
  const normalizedPerPage = Number.isFinite(perPage) && perPage > 0 ? perPage : 20;
  const start = (normalizedPage - 1) * normalizedPerPage;
  const sliced = items.slice(start, start + normalizedPerPage);
  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / normalizedPerPage));

  return {
    items: sliced,
    pagination: {
      totalItems,
      totalPages,
      perPage: normalizedPerPage,
      currentPage: normalizedPage,
      hasPrev: normalizedPage > 1,
      hasNext: normalizedPage < totalPages,
    },
  };
}

let currentUserId = mockUsers[0].userId;

export function setCurrentUser(userId: string) {
  const target = mockUsers.find((user) => user.userId === userId);
  if (target) {
    currentUserId = target.userId;
  }
}

export function getCurrentUser() {
  const target = mockUsers.find((user) => user.userId === currentUserId);
  return target || mockUsers[0];
}
