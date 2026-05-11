import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileTable from './FileTable.vue';
import FileRow from './FileRow.vue';

const items = [
  {
    id: 'a', name: 'alpha.txt', itemType: 'file' as const,
    size: 1024, mimeType: 'text/plain', ownerName: '',
    createdAt: '2026-05-01T00:00:00Z', updatedAt: '2026-05-01T00:00:00Z',
    folderId: 'root', isStarred: false,
  },
  {
    id: 'b', name: 'beta', itemType: 'folder' as const,
    size: 0, ownerName: '',
    createdAt: '2026-05-02T00:00:00Z', updatedAt: '2026-05-02T00:00:00Z',
    parentFolderId: null, isStarred: false,
  },
];

describe('FileTable', () => {
  it('renders one FileRow per item in list mode', () => {
    const wrapper = mount(FileTable, {
      props: {
        mode: 'list', items,
        selection: new Set<string>(), renamingId: null, renameValue: '',
        sortKey: 'name', sortDirection: 'asc',
      },
    });
    expect(wrapper.findAllComponents(FileRow)).toHaveLength(2);
  });

  it('renders cards in grid mode', () => {
    const wrapper = mount(FileTable, {
      props: {
        mode: 'grid', items,
        selection: new Set<string>(), renamingId: null, renameValue: '',
        sortKey: 'name', sortDirection: 'asc',
      },
    });
    expect(wrapper.findAll('.card')).toHaveLength(2);
  });

  it('emits sort when list header column clicked', async () => {
    const wrapper = mount(FileTable, {
      props: {
        mode: 'list', items,
        selection: new Set<string>(), renamingId: null, renameValue: '',
        sortKey: 'name', sortDirection: 'asc',
      },
    });
    await wrapper.find('[data-sort-key="size"]').trigger('click');
    expect(wrapper.emitted('sort')?.[0]?.[0]).toBe('size');
  });
});
