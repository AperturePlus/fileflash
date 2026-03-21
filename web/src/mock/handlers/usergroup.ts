import Mock from 'mockjs';
import { createMockId, mockUsers, paginate } from '../state';

const groups: Array<{
  groupId: string;
  name: string;
  description?: string;
  memberCount: number;
  createdAt: string;
  members: Array<{ userId: string; role: 'member' | 'admin' }>;
}> = [
  {
    groupId: 'group1',
    name: 'Developers',
    description: 'All software developers',
    memberCount: 2,
    createdAt: new Date(Date.now() - 120 * 24 * 3600000).toISOString(),
    members: [
      { userId: 'user1', role: 'admin' },
      { userId: 'user2', role: 'member' },
    ],
  },
  {
    groupId: 'group2',
    name: 'Designers',
    description: 'UI and visual designers',
    memberCount: 1,
    createdAt: new Date(Date.now() - 80 * 24 * 3600000).toISOString(),
    members: [{ userId: 'user3', role: 'member' }],
  },
  {
    groupId: 'group3',
    name: 'Marketing',
    description: 'Marketing and growth team',
    memberCount: 1,
    createdAt: new Date(Date.now() - 40 * 24 * 3600000).toISOString(),
    members: [{ userId: 'user4', role: 'member' }],
  },
];

export const setupUserGroupMocks = () => {
  Mock.mock(/\/api\/v1\/user-groups(?:\?.*)?$/, 'get', (options) => {
    const url = new URL(options.url, 'http://localhost');
    const search = (url.searchParams.get('search') || '').toLowerCase();
    const page = Number(url.searchParams.get('page') || 1);
    const perPage = Number(url.searchParams.get('perPage') || 20);

    const filtered = groups.filter((group) => {
      if (!search) return true;
      return group.name.toLowerCase().includes(search) || (group.description || '').toLowerCase().includes(search);
    });

    const mapped = filtered.map(({ members, ...group }) => group);

    return {
      success: true,
      code: 200,
      data: paginate(mapped, page, perPage),
    };
  });

  Mock.mock(/\/api\/v1\/user-groups$/, 'post', (options) => {
    const { name, description } = JSON.parse(options.body || '{}');

    if (!name) {
      return {
        success: false,
        code: 400,
        message: 'name is required',
        data: null,
      };
    }

    const created = {
      groupId: createMockId('group'),
      name,
      description,
      memberCount: 0,
      createdAt: new Date().toISOString(),
      members: [] as Array<{ userId: string; role: 'member' | 'admin' }>,
    };

    groups.unshift(created);

    return {
      success: true,
      code: 201,
      data: {
        groupId: created.groupId,
        name: created.name,
        description: created.description,
        memberCount: created.memberCount,
        createdAt: created.createdAt,
      },
    };
  });

  Mock.mock(/\/api\/v1\/user-groups\/([^/]+)\/members$/, 'post', (options) => {
    const groupId = (options.url.match(/\/api\/v1\/user-groups\/([^/]+)\/members/) || [])[1];
    const { userId, role } = JSON.parse(options.body || '{}');

    const group = groups.find((entry) => entry.groupId === groupId);
    if (!group) {
      return {
        success: false,
        code: 404,
        message: 'Group not found',
        data: null,
      };
    }

    const user = mockUsers.find((entry) => entry.userId === userId);
    if (!user) {
      return {
        success: false,
        code: 404,
        message: 'User not found',
        data: null,
      };
    }

    const existing = group.members.find((member) => member.userId === userId);
    if (existing) {
      existing.role = role;
    } else {
      group.members.push({ userId, role });
      group.memberCount += 1;
    }

    return {
      success: true,
      code: 200,
      data: {
        groupId: group.groupId,
        groupName: group.name,
        addedUser: {
          userId: user.userId,
          username: user.username,
          role,
        },
        totalMembers: group.memberCount,
      },
    };
  });

  Mock.mock(/\/api\/v1\/user-groups\/([^/]+)\/members\/([^/]+)$/, 'delete', (options) => {
    const groupMatch = options.url.match(/\/api\/v1\/user-groups\/([^/]+)\/members\/([^/?]+)/);
    const groupId = groupMatch ? groupMatch[1] : '';
    const userId = groupMatch ? groupMatch[2] : '';

    const group = groups.find((entry) => entry.groupId === groupId);
    if (!group) {
      return {
        success: false,
        code: 404,
        message: 'Group not found',
        data: null,
      };
    }

    const memberIndex = group.members.findIndex((member) => member.userId === userId);
    if (memberIndex === -1) {
      return {
        success: false,
        code: 404,
        message: 'Group member not found',
        data: null,
      };
    }

    const [removedMember] = group.members.splice(memberIndex, 1);
    group.memberCount = Math.max(0, group.memberCount - 1);

    const user = mockUsers.find((entry) => entry.userId === userId);

    return {
      success: true,
      code: 200,
      data: {
        groupId: group.groupId,
        groupName: group.name,
        removedUser: {
          userId,
          username: user?.username || userId,
          role: removedMember.role,
        },
        remainingMembers: group.memberCount,
      },
    };
  });
};
