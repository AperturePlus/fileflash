import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../test/mount';
import SelectFolderDialog from './SelectFolderDialog.vue';

const { getFolderContentsMock } = vi.hoisted(() => ({
  getFolderContentsMock: vi.fn(async () => ({
    items: [],
    pagination: {
      totalItems: 0,
      totalPages: 1,
      perPage: 20,
      currentPage: 1,
      hasPrev: false,
      hasNext: false,
    },
  })),
}));

vi.mock('../../api/folder', () => ({
  getFolderContents: getFolderContentsMock,
}));

const flush = async () => {
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
};

describe('SelectFolderDialog', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
    getFolderContentsMock.mockClear();
  });

  it('shows and preselects root when there are no subfolders, then confirms root', async () => {
    getFolderContentsMock.mockResolvedValueOnce({
      items: [],
      pagination: {
        totalItems: 0,
        totalPages: 1,
        perPage: 20,
        currentPage: 1,
        hasPrev: false,
        hasNext: false,
      },
    });

    const wrapper = mount(SelectFolderDialog, {
      props: {
        isVisible: true,
        title: 'Save to My Space',
        confirmText: 'Save Here',
      },
    });
    await flush();

    const rootRow = wrapper.find('.root-folder-item');
    expect(rootRow.exists()).toBe(true);
    expect(rootRow.classes()).toContain('selected');

    const confirmButton = wrapper.find('.btn-primary');
    expect(confirmButton.attributes('disabled')).toBeUndefined();
    await confirmButton.trigger('click');

    expect(wrapper.emitted('confirm')).toBeTruthy();
    expect(wrapper.emitted('confirm')?.[0]).toEqual(['root']);
  });

  it('keeps root selectable when folder loading fails', async () => {
    getFolderContentsMock.mockRejectedValueOnce(new Error('network'));

    const wrapper = mount(SelectFolderDialog, {
      props: {
        isVisible: true,
        title: 'Save to My Space',
        confirmText: 'Save Here',
      },
    });
    await flush();

    expect(wrapper.find('.root-folder-item').exists()).toBe(true);
    expect(wrapper.find('.root-folder-item').classes()).toContain('selected');
    await wrapper.find('.btn-primary').trigger('click');

    expect(wrapper.emitted('confirm')).toBeTruthy();
    expect(wrapper.emitted('confirm')?.[0]).toEqual(['root']);
  });
});
