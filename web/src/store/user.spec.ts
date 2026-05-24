import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

const loginMock = vi.fn();
const getProfileMock = vi.fn();
const getStorageStatsMock = vi.fn();
const refreshTokenMock = vi.fn();
const logoutMock = vi.fn();
const updatePreferenceMock = vi.fn();
const setLocaleMock = vi.fn();

vi.mock('../api/user', () => ({
  login: (...args: unknown[]) => loginMock(...args),
  getProfile: (...args: unknown[]) => getProfileMock(...args),
  getStorageStats: (...args: unknown[]) => getStorageStatsMock(...args),
  refreshToken: (...args: unknown[]) => refreshTokenMock(...args),
  logout: (...args: unknown[]) => logoutMock(...args),
  updatePreference: (...args: unknown[]) => updatePreferenceMock(...args),
}));

vi.mock('./locale', () => ({
  useLocaleStore: () => ({
    setLocale: (...args: unknown[]) => setLocaleMock(...args),
  }),
}));

import { useUserStore } from './user';

describe('store/user', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.useRealTimers();
    loginMock.mockReset();
    getProfileMock.mockReset();
    getStorageStatsMock.mockReset();
    refreshTokenMock.mockReset();
    logoutMock.mockReset();
    updatePreferenceMock.mockReset();
    setLocaleMock.mockReset();
  });

  it('debounces storage stats refresh requests', async () => {
    vi.useFakeTimers();
    const store = useUserStore();
    store.setToken('token-1');
    store.setUser({
      userId: 'u-1',
      username: 'demo',
      email: 'demo@example.com',
      storageLimit: 1000,
      storageUsed: 0,
      emailVerified: true,
      createdAt: '2026-05-24T00:00:00Z',
    });
    getStorageStatsMock.mockResolvedValue({
      storageLimit: 1000,
      storageUsed: 10,
      storageAvailable: 990,
      storagePercentage: 1,
      fileCount: 1,
      folderCount: 1,
      breakdown: {},
    });

    store.scheduleStorageStatsRefresh(200);
    store.scheduleStorageStatsRefresh(200);
    store.scheduleStorageStatsRefresh(200);

    vi.advanceTimersByTime(199);
    await Promise.resolve();
    expect(getStorageStatsMock).toHaveBeenCalledTimes(0);

    vi.advanceTimersByTime(1);
    await Promise.resolve();
    await Promise.resolve();
    expect(getStorageStatsMock).toHaveBeenCalledTimes(1);
    expect(store.storageStats?.storageUsed).toBe(10);
  });
});
