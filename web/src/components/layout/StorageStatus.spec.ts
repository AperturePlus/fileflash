import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { mount } from '../../test/mount';
import type { StorageStats } from '../../types/user';

const fetchStorageStatsMock = vi.fn(async () => undefined);
const scheduleStorageStatsRefreshMock = vi.fn();
const storageStatsRef = ref<StorageStats | null>(null);

vi.mock('../../store/user', () => ({
  useUserStore: () => ({
    storageStats: storageStatsRef,
    fetchStorageStats: () => fetchStorageStatsMock(),
    scheduleStorageStatsRefresh: () => scheduleStorageStatsRefreshMock(),
  }),
}));

import StorageStatus from './StorageStatus.vue';

function buildStats(overrides: Partial<StorageStats> = {}): StorageStats {
  return {
    storageLimit: 1000,
    storageUsed: 0,
    storageAvailable: 1000,
    storagePercentage: 0,
    fileCount: 0,
    folderCount: 0,
    breakdown: {},
    ...overrides,
  };
}

describe('layout/StorageStatus', () => {
  beforeEach(() => {
    fetchStorageStatsMock.mockClear();
    scheduleStorageStatsRefreshMock.mockClear();
    storageStatsRef.value = null;
  });

  it('uses a minimum visible width when storage is non-zero but percentage is tiny', () => {
    const wrapper = mount(StorageStatus, {
      props: {
        stats: buildStats({
          storageUsed: 1,
          storageLimit: 10_000,
          storageAvailable: 9_999,
          storagePercentage: 0.01,
        }),
      },
    });
    const style = wrapper.find('.progress-bar-fill').attributes('style');
    expect(style).toContain('width: 1%;');
  });

  it('clamps and uses actual percentage for normal values', () => {
    const wrapper = mount(StorageStatus, {
      props: {
        stats: buildStats({
          storageUsed: 500,
          storageLimit: 1000,
          storageAvailable: 500,
          storagePercentage: 145.3,
        }),
      },
    });
    const style = wrapper.find('.progress-bar-fill').attributes('style');
    expect(style).toContain('width: 100%;');
  });
});
