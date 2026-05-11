import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileRow from './FileRow.vue';

const folder = {
  id: 'fo1',
  name: 'Pics',
  itemType: 'folder' as const,
  size: 0,
  ownerName: '',
  updatedAt: '2026-05-01T12:00:00Z',
  createdAt: '2026-05-01T12:00:00Z',
  parentFolderId: null,
  isStarred: false,
};
const file = {
  id: 'fi1',
  name: 'report.pdf',
  itemType: 'file' as const,
  size: 2048,
  mimeType: 'application/pdf',
  ownerName: '',
  updatedAt: '2026-05-02T08:30:00Z',
  createdAt: '2026-05-02T08:30:00Z',
  folderId: 'fo1',
  isStarred: true,
};

describe('FileRow', () => {
  it('renders name', () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    expect(wrapper.text()).toContain('report.pdf');
  });

  it('single click emits select with item + modifiers (shift=false default)', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('.row').trigger('click', { shiftKey: false });
    const payloads = wrapper.emitted('select');
    expect(payloads).toHaveLength(1);
    const p = payloads![0][0] as { item: { id: string }; modifiers: { shift: boolean } };
    expect(p.item.id).toBe('fi1');
    expect(p.modifiers.shift).toBe(false);
  });

  it('shift+click sets modifiers.shift = true', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('.row').trigger('click', { shiftKey: true });
    const p = wrapper.emitted('select')![0][0] as { modifiers: { shift: boolean } };
    expect(p.modifiers.shift).toBe(true);
  });

  it('dblclick emits activate with the item', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('.row').trigger('dblclick');
    expect(wrapper.emitted('activate')?.[0]?.[0]).toStrictEqual(file);
  });

  it('renaming suppresses dblclick activate and single-click select', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: true, renameValue: 'report.pdf' },
    });
    await wrapper.find('.row').trigger('click');
    await wrapper.find('.row').trigger('dblclick');
    expect(wrapper.emitted('activate')).toBeUndefined();
    expect(wrapper.emitted('select')).toBeUndefined();
  });

  it('emits toggleSelect when checkbox toggled', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('input[type="checkbox"]').setValue(true);
    expect(wrapper.emitted('toggleSelect')?.[0]?.[0]).toBe(file.id);
  });

  it('shows "--" for folder size', () => {
    const wrapper = mount(FileRow, {
      props: { item: folder, selected: false, renaming: false, renameValue: '' },
    });
    expect(wrapper.text()).toContain('--');
  });

  it('emits toggleStar', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('.row__star').trigger('click');
    expect(wrapper.emitted('toggleStar')?.[0]?.[0]).toStrictEqual(file);
  });

  it('temp folder while renaming carries data-temp-folder-row', () => {
    const tempFolder = { ...folder, id: 'temp-new-folder-1', name: '' };
    const wrapper = mount(FileRow, {
      props: { item: tempFolder, selected: false, renaming: true, renameValue: '' },
    });
    expect(wrapper.find('.row').attributes('data-temp-folder-row')).toBe('temp-new-folder-1');
  });

  it('non-temp folder while renaming does NOT carry data-temp-folder-row', () => {
    const wrapper = mount(FileRow, {
      props: { item: folder, selected: false, renaming: true, renameValue: 'Pics' },
    });
    expect(wrapper.find('.row').attributes('data-temp-folder-row')).toBeUndefined();
  });
});
