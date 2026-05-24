import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import type { Share } from '../types/share';

const {
  getSharedItemsMock,
  getSharesMock,
  updateShareSettingsMock,
  deleteShareMock,
  acceptSharedItemMock,
  confirmMock,
  copyTextMock,
  toastMock,
} = vi.hoisted(() => ({
  getSharedItemsMock: vi.fn(async () => ({
    items: [],
    pagination: { totalItems: 0, totalPages: 1, perPage: 50, currentPage: 1, hasPrev: false, hasNext: false },
  })),
  getSharesMock: vi.fn(async () => ({
    items: [],
    pagination: { totalItems: 0, totalPages: 1, perPage: 50, currentPage: 1, hasPrev: false, hasNext: false },
  })),
  updateShareSettingsMock: vi.fn(async (_shareLink?: string, _payload?: Record<string, unknown>): Promise<Share> => ({
    shareId: 's1',
    shareLink: 'abc123',
    itemType: 'file',
    itemInfo: { id: 'f1', name: 'report.pdf', size: 1024, mimeType: 'application/pdf', folderPath: '/My Files' },
    settings: { passwordProtected: true, password: 'NEW-PASS', expireAt: null, allowDownload: true, allowPreview: true },
    createdAt: '2026-05-24T00:00:00.000Z',
  })),
  deleteShareMock: vi.fn(async () => ({})),
  acceptSharedItemMock: vi.fn(async () => ({})),
  confirmMock: vi.fn(async () => true),
  copyTextMock: vi.fn(async () => undefined),
  toastMock: vi.fn(),
}));

vi.mock('../store/locale', () => ({
  useLocaleStore: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('./useFileSelection', () => ({
  useFileSelection: () => ({
    selectedItems: ref(new Set<string>()),
    selectedCount: computed(() => 0),
    clear: vi.fn(),
    clearSelection: vi.fn(),
    toggleSelection: vi.fn(),
    toggleAdd: vi.fn(),
    selectRange: vi.fn(),
    lastSelectedId: ref<string | null>(null),
    isSelected: vi.fn(() => false),
  }),
}));

vi.mock('../api/share', () => ({
  getSharedItems: getSharedItemsMock,
  getShares: getSharesMock,
  updateShareSettings: updateShareSettingsMock,
  deleteShare: deleteShareMock,
  acceptSharedItem: acceptSharedItemMock,
}));

vi.mock('../utils/ui', () => ({
  ui: {
    confirm: confirmMock,
    copyText: copyTextMock,
    toast: toastMock,
  },
}));

import { useSharingCenter } from './useSharingCenter';

const makeShare = (overrides: Partial<Share> = {}): Share => {
  const base: Share = {
    shareId: 's1',
    shareLink: 'abc123',
    itemType: 'file',
    itemInfo: { id: 'f1', name: 'report.pdf', size: 1024, mimeType: 'application/pdf' },
    settings: { passwordProtected: true, expireAt: null, allowDownload: true, allowPreview: true },
    createdAt: '2026-05-24T00:00:00.000Z',
  };
  return {
    ...base,
    ...overrides,
    itemInfo: { ...base.itemInfo, ...(overrides.itemInfo || {}) },
    settings: { ...base.settings, ...(overrides.settings || {}) },
  };
};

describe('useSharingCenter regenerate password', () => {
  beforeEach(() => {
    getSharedItemsMock.mockClear();
    getSharesMock.mockClear();
    updateShareSettingsMock.mockClear();
    deleteShareMock.mockClear();
    acceptSharedItemMock.mockClear();
    confirmMock.mockClear();
    copyTextMock.mockClear();
    toastMock.mockClear();
  });

  it('confirms, regenerates password, and shows it to the sharer', async () => {
    confirmMock.mockResolvedValueOnce(true);
    updateShareSettingsMock.mockResolvedValueOnce(makeShare({
      settings: { passwordProtected: true, password: 'NEW-PASS-001', expireAt: null, allowDownload: true, allowPreview: true },
    }));

    const sharing = useSharingCenter();
    const share = makeShare();
    sharing.myShares.value = [share];

    await sharing.regenerateAndShowPassword(share);

    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(updateShareSettingsMock).toHaveBeenCalledWith('abc123', {
      passwordProtected: true,
      regeneratePassword: true,
    });
    expect(copyTextMock).toHaveBeenCalledWith(expect.objectContaining({ text: 'NEW-PASS-001' }));
    expect(toastMock).toHaveBeenCalledWith({
      type: 'success',
      message: 'sharing.toast.passwordRegenerated',
    });
  });

  it('does not regenerate when user cancels confirmation', async () => {
    confirmMock.mockResolvedValueOnce(false);

    const sharing = useSharingCenter();
    const share = makeShare();
    await sharing.regenerateAndShowPassword(share);

    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(updateShareSettingsMock).not.toHaveBeenCalled();
    expect(copyTextMock).not.toHaveBeenCalled();
  });

  it('shows error when api returns without new password', async () => {
    confirmMock.mockResolvedValueOnce(true);
    updateShareSettingsMock.mockResolvedValueOnce(makeShare({
      settings: { passwordProtected: true, password: null, expireAt: null, allowDownload: true, allowPreview: true },
    }));

    const sharing = useSharingCenter();
    const share = makeShare();
    await sharing.regenerateAndShowPassword(share);

    expect(copyTextMock).not.toHaveBeenCalled();
    expect(toastMock).toHaveBeenCalledWith({
      type: 'error',
      message: 'sharing.toast.passwordRegenerateFailed',
    });
    expect(getSharesMock).toHaveBeenCalledTimes(1);
  });

  it('shows error and refreshes links when regenerate api fails', async () => {
    confirmMock.mockResolvedValueOnce(true);
    updateShareSettingsMock.mockRejectedValueOnce(new Error('boom'));

    const sharing = useSharingCenter();
    const share = makeShare();
    await sharing.regenerateAndShowPassword(share);

    expect(copyTextMock).not.toHaveBeenCalled();
    expect(toastMock).toHaveBeenCalledWith({
      type: 'error',
      message: 'sharing.toast.passwordRegenerateFailed',
    });
    expect(getSharesMock).toHaveBeenCalledTimes(1);
  });
});
