import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../api/user', () => ({
  getAdminUsers: vi.fn(),
  updateUserStatus: vi.fn(),
}));

vi.mock('../../../utils/ui', () => ({
  ui: {
    toast: vi.fn(),
  },
}));

import { getAdminUsers } from '../../../api/user';
import UsersPage from './UsersPage.vue';

const getAdminUsersMock = vi.mocked(getAdminUsers);

function pageData() {
  return {
    items: [
      {
        userId: '1',
        username: 'alice',
        email: 'alice@example.com',
        role: 'USER' as const,
        status: 'active' as const,
        emailVerified: true,
        emailVerifiedAt: null,
        storageLimit: 1024,
        storageUsed: 0,
        usagePercentage: 0,
        lastLoginAt: null,
        lastActiveAt: null,
        createdAt: '2026-05-01T00:00:00Z',
        usageStats: {
          trafficBytes: 1536,
          agentTokens: 12345,
        },
      },
    ],
    pagination: {
      totalItems: 1,
      totalPages: 1,
      perPage: 20,
      currentPage: 1,
      hasPrev: false,
      hasNext: false,
    },
  };
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-26T12:00:00.000Z'));
    getAdminUsersMock.mockResolvedValue(pageData());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('loads the default previous 7 day usage window', async () => {
    mount(UsersPage);
    await flushPromises();

    expect(getAdminUsersMock).toHaveBeenCalledWith(expect.objectContaining({
      page: 1,
      perPage: 20,
      usageFrom: '2026-05-19T00:00:00.000Z',
      usageTo: '2026-05-26T23:59:59.999Z',
    }));
  });

  it('reloads with the edited usage window after apply', async () => {
    const wrapper = mount(UsersPage);
    await flushPromises();

    const dateInputs = wrapper.findAll('input[type="date"]');
    await dateInputs[0].setValue('2026-05-01');
    await dateInputs[1].setValue('2026-05-10');
    await wrapper.find('.filter-bar__apply').trigger('click');
    await flushPromises();

    expect(getAdminUsersMock).toHaveBeenLastCalledWith(expect.objectContaining({
      usageFrom: '2026-05-01T00:00:00.000Z',
      usageTo: '2026-05-10T23:59:59.999Z',
    }));
  });

  it('renders upload traffic and agent tokens', async () => {
    const wrapper = mount(UsersPage);
    await flushPromises();

    expect(wrapper.text()).toContain('Uploaded 1.5 KB');
    expect(wrapper.text()).toContain('Agent 12,345 tokens');
  });
});
