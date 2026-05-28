import { describe, expect, it, beforeEach, vi } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../test/mount';
import ShareDialog from './ShareDialog.vue';
import type { Share } from '../../types/share';

type MockPagination = {
  totalItems: number;
  totalPages: number;
  perPage: number;
  currentPage: number;
  hasPrev: boolean;
  hasNext: boolean;
};

type MockShareList = {
  items: Share[];
  pagination: MockPagination;
};

const {
  getSharesMock,
  createShareMock,
  updateShareSettingsMock,
  deleteShareMock,
  getPermissionsMock,
  createPermissionMock,
  updatePermissionMock,
  deletePermissionMock,
  getUsersMock,
  getUserGroupsMock,
  confirmMock,
  copyTextMock,
} = vi.hoisted(() => ({
  getSharesMock: vi.fn(async (): Promise<MockShareList> => ({
    items: [],
    pagination: { totalItems: 0, totalPages: 1, perPage: 100, currentPage: 1, hasPrev: false, hasNext: false },
  })),
  createShareMock: vi.fn(async (_payload?: Record<string, unknown>): Promise<Share> => ({
    shareId: 's-new',
    shareLink: 'NEW123',
    itemType: 'file',
    itemInfo: { id: 'f-1', name: 'draft.txt', size: 12, mimeType: 'text/plain', folderPath: '/My Files' },
    settings: { passwordProtected: false, expireAt: null, allowDownload: true, allowPreview: true },
    createdAt: '2026-05-24T00:00:00.000Z',
  })),
  updateShareSettingsMock: vi.fn(async (_shareLink?: string, _payload?: Record<string, unknown>): Promise<Share> => ({
    shareId: 's-new',
    shareLink: 'NEW123',
    itemType: 'file',
    itemInfo: { id: 'f-1', name: 'draft.txt', size: 12, mimeType: 'text/plain', folderPath: '/My Files' },
    settings: { passwordProtected: false, expireAt: null, allowDownload: true, allowPreview: false },
    createdAt: '2026-05-24T00:00:00.000Z',
  })),
  deleteShareMock: vi.fn(async () => ({
    shareId: 's-old',
    shareLink: 'OLD999',
    deletedAt: '2026-05-24T00:00:00.000Z',
  })),
  getPermissionsMock: vi.fn(async () => ({ items: [], pagination: { totalItems: 0, totalPages: 1, perPage: 50, currentPage: 1, hasPrev: false, hasNext: false } })),
  createPermissionMock: vi.fn(async () => ({
    permissionId: 'perm-new',
    itemType: 'file',
    itemId: 'f-1',
    grantedTo: { type: 'user', id: 'u-2', name: 'alice' },
    permission: 'read',
    createdAt: '2026-05-24T00:00:00.000Z',
  })),
  updatePermissionMock: vi.fn(async () => ({})),
  deletePermissionMock: vi.fn(async () => ({})),
  getUsersMock: vi.fn(async () => ({ items: [{ userId: 'u-2', username: 'alice', email: 'alice@example.com' }] })),
  getUserGroupsMock: vi.fn(async () => ({ items: [] })),
  confirmMock: vi.fn(async () => true),
  copyTextMock: vi.fn(async () => undefined),
}));

vi.mock('@vueuse/core', () => ({
  useDebounceFn: (fn: (...args: unknown[]) => unknown) => fn,
}));

vi.mock('../../api/share', () => ({
  getShares: getSharesMock,
  createShare: createShareMock,
  updateShareSettings: updateShareSettingsMock,
  deleteShare: deleteShareMock,
}));

vi.mock('../../api/permission', () => ({
  getPermissions: getPermissionsMock,
  createPermission: createPermissionMock,
  updatePermission: updatePermissionMock,
  deletePermission: deletePermissionMock,
}));

vi.mock('../../api/user', () => ({
  getUsers: getUsersMock,
}));

vi.mock('../../api/usergroup', () => ({
  getUserGroups: getUserGroupsMock,
}));

vi.mock('../../utils/ui', () => ({
  ui: {
    confirm: confirmMock,
    copyText: copyTextMock,
    toast: vi.fn(),
    promptText: vi.fn(),
    resolveConfirm: vi.fn(),
    resolvePrompt: vi.fn(),
    dismissToast: vi.fn(),
  },
  uiState: {
    confirm: null,
    prompt: null,
    toasts: [],
  },
}));

const baseItem = {
  itemType: 'file' as const,
  id: 'f-1',
  name: 'draft.txt',
  size: 12,
  mimeType: 'text/plain',
  ownerName: 'owner',
  createdAt: '2026-05-24T00:00:00.000Z',
  updatedAt: '2026-05-24T00:00:00.000Z',
  folderId: 'root',
};

const makeShare = (overrides: Partial<Share> = {}): Share => {
  const base: Share = {
    shareId: 's-new',
    shareLink: 'NEW123',
    itemType: 'file',
    itemInfo: { id: 'f-1', name: 'draft.txt', size: 12, mimeType: 'text/plain', folderPath: '/My Files' },
    settings: { passwordProtected: false, expireAt: null, allowDownload: true, allowPreview: true },
    createdAt: '2026-05-24T00:00:00.000Z',
  };
  return {
    ...base,
    ...overrides,
    itemInfo: { ...base.itemInfo, ...(overrides.itemInfo || {}) },
    settings: { ...base.settings, ...(overrides.settings || {}) },
  };
};

const flush = async () => {
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
};

const openDialog = async () => {
  const wrapper = mount(ShareDialog, {
    props: {
      isVisible: false,
      itemToShare: baseItem,
    },
  });
  await wrapper.setProps({ isVisible: true });
  await flush();
  return wrapper;
};

const addDraftCollaborator = async (wrapper: ReturnType<typeof mount>) => {
  const input = wrapper.find('.search-box input');
  await input.setValue('ali');
  await input.trigger('input');
  await flush();
  const result = wrapper.find('.search-item');
  await result.trigger('click');
  await flush();
};

describe('ShareDialog draft submit flow', () => {
  beforeEach(() => {
    getSharesMock.mockClear();
    createShareMock.mockClear();
    updateShareSettingsMock.mockClear();
    deleteShareMock.mockClear();
    getPermissionsMock.mockClear();
    createPermissionMock.mockClear();
    updatePermissionMock.mockClear();
    deletePermissionMock.mockClear();
    getUsersMock.mockClear();
    getUserGroupsMock.mockClear();
    confirmMock.mockClear();
    copyTextMock.mockClear();
  });

  it('does not submit anything when closed without done', async () => {
    const wrapper = await openDialog();
    await wrapper.find('.modal-close').trigger('click');

    expect(wrapper.emitted('close')).toBeTruthy();
    expect(createShareMock).not.toHaveBeenCalled();
    expect(updateShareSettingsMock).not.toHaveBeenCalled();
    expect(createPermissionMock).not.toHaveBeenCalled();
    expect(updatePermissionMock).not.toHaveBeenCalled();
    expect(deletePermissionMock).not.toHaveBeenCalled();
    expect(deleteShareMock).not.toHaveBeenCalled();
  });

  it('submits collaborator and share settings only when done is clicked', async () => {
    const wrapper = await openDialog();

    const switchInput = wrapper.find('.switch input[type="checkbox"]');
    await switchInput.setValue(true);
    await addDraftCollaborator(wrapper);

    const settingChecks = wrapper.findAll('.settings-grid .setting-check input[type="checkbox"]');
    await settingChecks[2].setValue(false);
    await wrapper.find('.done-btn').trigger('click');
    await flush();

    expect(createPermissionMock).toHaveBeenCalledTimes(1);
    expect(createPermissionMock).toHaveBeenCalledWith({
      fileId: 'f-1',
      userId: 'u-2',
      groupId: undefined,
      permission: 'read',
    });
    expect(createShareMock).toHaveBeenCalledTimes(1);
    expect(updateShareSettingsMock).toHaveBeenCalledTimes(1);
    expect(updateShareSettingsMock).toHaveBeenCalledWith('NEW123', expect.objectContaining({ allowPreview: false }));
    expect(wrapper.emitted('close')).toBeTruthy();
  });

  it('requires confirmation before revoking an existing public link', async () => {
    getSharesMock.mockImplementationOnce(async (): Promise<MockShareList> => ({
      items: [makeShare({ shareId: 's-old', shareLink: 'OLD999' })],
      pagination: { totalItems: 1, totalPages: 1, perPage: 100, currentPage: 1, hasPrev: false, hasNext: false },
    }));

    const wrapper = await openDialog();
    const switchInput = wrapper.find('.switch input[type="checkbox"]');
    await switchInput.setValue(false);

    confirmMock.mockResolvedValueOnce(false);
    await wrapper.find('.done-btn').trigger('click');
    await flush();

    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(deleteShareMock).not.toHaveBeenCalled();
    expect(wrapper.emitted('close')).toBeFalsy();

    confirmMock.mockResolvedValueOnce(true);
    await wrapper.find('.done-btn').trigger('click');
    await flush();

    expect(deleteShareMock).toHaveBeenCalledTimes(1);
    expect(deleteShareMock).toHaveBeenCalledWith('OLD999');
    expect(wrapper.emitted('close')).toBeTruthy();
  });

  it('shows auto-generated password after done when password was left blank', async () => {
    updateShareSettingsMock.mockImplementationOnce(async () => makeShare({
      settings: {
        passwordProtected: true,
        password: 'AUTO-987654',
        expireAt: null,
        allowDownload: true,
        allowPreview: true,
      },
    }));

    const wrapper = await openDialog();
    await wrapper.find('.switch input[type="checkbox"]').setValue(true);

    const settingChecks = wrapper.findAll('.settings-grid .setting-check input[type="checkbox"]');
    await settingChecks[0].setValue(true);
    await wrapper.find('.done-btn').trigger('click');
    await flush();

    expect(updateShareSettingsMock).toHaveBeenCalledTimes(1);
    const payload = updateShareSettingsMock.mock.calls[0]?.[1] as Record<string, unknown> | undefined;
    expect(payload?.passwordProtected).toBe(true);
    expect(payload?.password).toBeUndefined();
    expect(copyTextMock).toHaveBeenCalledTimes(1);
    expect(copyTextMock).toHaveBeenCalledWith(expect.objectContaining({ text: 'AUTO-987654' }));
    expect(wrapper.emitted('close')).toBeTruthy();
  });

  it('does not force password dialog after done when user provided password manually', async () => {
    updateShareSettingsMock.mockImplementationOnce(async () => makeShare({
      settings: {
        passwordProtected: true,
        password: 'manual-pass',
        expireAt: null,
        allowDownload: true,
        allowPreview: true,
      },
    }));

    const wrapper = await openDialog();
    await wrapper.find('.switch input[type="checkbox"]').setValue(true);

    const settingChecks = wrapper.findAll('.settings-grid .setting-check input[type="checkbox"]');
    await settingChecks[0].setValue(true);
    await wrapper.find('.password-row input').setValue('manual-pass');
    await wrapper.find('.done-btn').trigger('click');
    await flush();

    expect(updateShareSettingsMock).toHaveBeenCalledTimes(1);
    const payload = updateShareSettingsMock.mock.calls[0]?.[1] as Record<string, unknown> | undefined;
    expect(payload?.password).toBe('manual-pass');
    expect(copyTextMock).not.toHaveBeenCalled();
    expect(wrapper.emitted('close')).toBeTruthy();
  });

  it('keeps dialog open and refreshes state when submit fails', async () => {
    createPermissionMock.mockRejectedValueOnce(new Error('boom'));
    const wrapper = await openDialog();
    const initialShareCalls = getSharesMock.mock.calls.length;
    const initialPermissionCalls = getPermissionsMock.mock.calls.length;

    const switchInput = wrapper.find('.switch input[type="checkbox"]');
    await switchInput.setValue(true);
    await addDraftCollaborator(wrapper);
    await wrapper.find('.done-btn').trigger('click');
    await flush();

    expect(wrapper.emitted('close')).toBeFalsy();
    expect(getSharesMock.mock.calls.length).toBeGreaterThan(initialShareCalls);
    expect(getPermissionsMock.mock.calls.length).toBeGreaterThan(initialPermissionCalls);
  });
});
