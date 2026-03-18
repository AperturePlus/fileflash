import Mock from 'mockjs';

const sharedItems = [
  {
    itemType: 'file',
    id: 'shared_file_1',
    name: 'Q3 Financial Report.xlsx',
    size: 1572864,
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    sharedBy: 'Alice',
    permission: 'write',
    sharedAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
  },
  {
    itemType: 'folder',
    id: 'shared_folder_1',
    name: 'Project Phoenix Assets',
    size: 268435456,
    sharedBy: 'Bob',
    permission: 'read',
    sharedAt: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
  },
  {
    itemType: 'file',
    id: 'shared_file_2',
    name: 'Design Mockups.fig',
    size: 25165824,
    mimeType: 'application/figma',
    sharedBy: 'Charlie',
    permission: 'read',
    sharedAt: new Date(Date.now() - 259200000).toISOString(), // 3 days ago
  },
];

export const setupShareMocks = () => {
  // Get Shared Items
  Mock.mock(/\/api\/v1\/shared-items/, 'get', (options) => {
    // Basic mock, no sorting/paging for now
    return {
      success: true,
      code: 200,
      data: {
        items: sharedItems,
        pagination: { totalItems: sharedItems.length, totalPages: 1, perPage: sharedItems.length, currentPage: 1 },
      },
    };
  });
}; 