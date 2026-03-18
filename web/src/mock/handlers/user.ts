import Mock from 'mockjs';
import { vfsApi } from '../vfs'; // We might not need vfs here, but good to have.

const users = [
  { userId: 'user1', username: 'Alice', email: 'alice@example.com' },
  { userId: 'user2', username: 'Bob', email: 'bob@example.com' },
  { userId: 'user3', username: 'Charlie', email: 'charlie@example.com' },
  { userId: 'user4', username: 'David', email: 'david@example.com' },
];

export const setupUserMocks = () => {
  // Get Users (with search)
  Mock.mock(/\/api\/v1\/users/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const search = url.searchParams.get('search') || '';
    
    const filteredUsers = users.filter(user => 
      user.username.toLowerCase().includes(search.toLowerCase()) ||
      user.email.toLowerCase().includes(search.toLowerCase())
    );

    return {
      success: true,
      code: 200,
      data: {
        items: filteredUsers,
        pagination: { totalItems: filteredUsers.length, totalPages: 1, perPage: filteredUsers.length, currentPage: 1 },
      },
    };
  });

  // Get User Profile
  Mock.mock(/\/api\/v1\/me\/profile/, 'get', {
    success: true,
    code: 200,
    data: {
      userId: 'user1', 
      username: 'Demo User', 
      email: 'demo@example.com',
      storageLimit: 107374182400, // 100GB
      storageUsed: 21474836480,   // 20GB
      createdAt: '@datetime("yyyy-MM-dd HH:mm:ss")',
      updatedAt: '@datetime("yyyy-MM-dd HH:mm:ss")',
      lastLogin: '@datetime("yyyy-MM-dd HH:mm:ss")',
      groups: [
        {
          groupId: 1,
          groupName: '开发团队',
          role: 'admin'
        },
        {
          groupId: 2,
          groupName: '项目管理',
          role: 'member'
        }
      ]
    }
  });

  // Get Storage Stats
  Mock.mock(/\/api\/v1\/me\/storage-stats/, 'get', {
    success: true,
    code: 200,
    data: {
      storageLimit: 107374182400, // 100GB
      storageUsed: 21474836480,   // 20GB
      storageAvailable: 85899345920, // 80GB
      storagePercentage: 20,
      fileCount: 1247,
      folderCount: 86,
      breakdown: {
        documents: {
          size: 5368709120, // 5GB
          count: 234
        },
        images: {
          size: 10737418240, // 10GB
          count: 567
        },
        videos: {
          size: 4294967296, // 4GB
          count: 12
        },
        audio: {
          size: 1073741824, // 1GB
          count: 89
        },
        archives: {
          size: 268435456, // 256MB
          count: 15
        },
        others: {
          size: 268435456, // 256MB
          count: 330
        }
      }
    },
  });

  // Get Activity Log
  Mock.mock(/\/api\/v1\/me\/activity-log/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const page = parseInt(url.searchParams.get('page') || '1');
    const perPage = parseInt(url.searchParams.get('perPage') || '20');
    
    const activities = Mock.mock({
      [`items|${perPage}`]: [{
        'id|+1': 1,
        'operation|1': ['file_upload', 'file_download', 'file_delete', 'folder_create', 'file_share', 'login'],
        details: {
          fileName: '@word.txt',
          fileSize: '@integer(1024, 10485760)',
          'action|1': ['创建', '上传', '下载', '删除', '分享']
        },
        ipAddress: '@ip',
        performedAt: '@datetime("yyyy-MM-dd HH:mm:ss")'
      }]
    });

    return {
      success: true,
      code: 200,
      data: {
        items: activities.items,
        pagination: {
          currentPage: page,
          perPage: perPage,
          totalItems: 156,
          totalPages: Math.ceil(156 / perPage)
        }
      }
    };
  });
}; 