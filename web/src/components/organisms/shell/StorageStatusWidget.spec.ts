import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { mount } from '../../../test/mount';
import { eventBus } from '../../../utils/eventBus';
import type { StorageStats } from '../../../types/user';

const fetchStorageStatsMock = vi.fn(async () => undefined);
const scheduleStorageStatsRefreshMock = vi.fn();
const storageStatsRef = ref<StorageStats | null>(null);

vi.mock('../../../store/user', () => ({
  useUserStore: () => ({
    storageStats: storageStatsRef,
    fetchStorageStats: () => fetchStorageStatsMock(),
    scheduleStorageStatsRefresh: () => scheduleStorageStatsRefreshMock(),
  }),
}));

import StorageStatusWidget from './StorageStatusWidget.vue';

describe('organisms/shell/StorageStatusWidget', () => {
  beforeEach(() => {
    fetchStorageStatsMock.mockClear();
    scheduleStorageStatsRefreshMock.mockClear();
    storageStatsRef.value = {
      storageLimit: 1000,
      storageUsed: 10,
      storageAvailable: 990,
      storagePercentage: 1,
      fileCount: 1,
      folderCount: 1,
      breakdown: {},
    };
  });

  it('fetches storage stats on mount', () => {
    const wrapper = mount(StorageStatusWidget, { props: { collapsed: false } });
    expect(fetchStorageStatsMock).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('refreshes storage stats when file tree refresh event is emitted', async () => {
    const wrapper = mount(StorageStatusWidget, { props: { collapsed: false } });
    eventBus.emit('refresh-file-tree');
    expect(scheduleStorageStatsRefreshMock).toHaveBeenCalledTimes(1);

    wrapper.unmount();
    eventBus.emit('refresh-file-tree');
    expect(scheduleStorageStatsRefreshMock).toHaveBeenCalledTimes(1);
  });
});
