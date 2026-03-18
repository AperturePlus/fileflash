import Mock from 'mockjs';

const groups = [
  { groupId: 'group1', name: 'Developers', description: 'All software developers' },
  { groupId: 'group2', name: 'Designers', description: 'UI/UX design team' },
  { groupId: 'group3', name: 'Marketing', description: 'Marketing and sales' },
];

export const setupUserGroupMocks = () => {
  // Get User Groups (with search)
  Mock.mock(/\/api\/v1\/user-groups/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const search = url.searchParams.get('search') || '';

    const filteredGroups = groups.filter(group => 
      group.name.toLowerCase().includes(search.toLowerCase())
    );

    return {
      success: true,
      code: 200,
      data: {
        items: filteredGroups,
        pagination: { totalItems: filteredGroups.length, totalPages: 1, perPage: filteredGroups.length, currentPage: 1 },
      },
    };
  });
}; 