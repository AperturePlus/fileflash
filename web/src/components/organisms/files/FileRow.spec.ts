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
  it('renders name and emits click', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    expect(wrapper.text()).toContain('report.pdf');
    await wrapper.find('.row').trigger('click');
    expect(wrapper.emitted('click')?.[0]?.[0]).toStrictEqual(file);
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
});
