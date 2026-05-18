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

const baseProps = {
  mode: 'list' as const,
  items,
  selection: new Set<string>(),
  renamingId: null,
  renameValue: '',
  sortKey: 'name' as const,
  sortDirection: 'asc' as const,
};

describe('FileTable', () => {
  it('renders one FileRow per item in list mode', () => {
    const wrapper = mount(FileTable, { props: baseProps });
    expect(wrapper.findAllComponents(FileRow)).toHaveLength(2);
  });

  it('renders cards in grid mode', () => {
    const wrapper = mount(FileTable, { props: { ...baseProps, mode: 'grid' as const } });
    expect(wrapper.findAll('.card')).toHaveLength(2);
  });

  it('emits sort when list header column clicked', async () => {
    const wrapper = mount(FileTable, { props: baseProps });
    await wrapper.find('[data-sort-key="size"]').trigger('click');
    expect(wrapper.emitted('sort')?.[0]?.[0]).toBe('size');
  });

  it('forwards FileRow select events', async () => {
    const wrapper = mount(FileTable, { props: baseProps });
    await wrapper.findAll('.row')[0].trigger('click', { shiftKey: false });
    const ev = wrapper.emitted('select');
    expect(ev).toBeTruthy();
    expect((ev![0][0] as { item: { id: string } }).item.id).toBe('a');
  });

  it('forwards FileRow activate (dblclick)', async () => {
    const wrapper = mount(FileTable, { props: baseProps });
    await wrapper.findAll('.row')[0].trigger('dblclick');
    expect(wrapper.emitted('activate')?.[0]?.[0]).toStrictEqual(items[0]);
  });

  it('container click on blank area emits clear-selection', async () => {
    const wrapper = mount(FileTable, { props: baseProps });
    await wrapper.find('.table').trigger('click');
    expect(wrapper.emitted('clear-selection')).toBeTruthy();
  });

  it('FileRow click does NOT bubble to clear-selection', async () => {
    const wrapper = mount(FileTable, { props: baseProps });
    await wrapper.findAll('.row')[0].trigger('click');
    expect(wrapper.emitted('clear-selection')).toBeUndefined();
  });

  it('resize handles render in header for name/size/time', () => {
    const wrapper = mount(FileTable, { props: baseProps });
    const handles = wrapper.findAll('.resize-handle');
    expect(handles.length).toBe(3);
  });

  it('grid mode: dblclick on card emits activate', async () => {
    const wrapper = mount(FileTable, { props: { ...baseProps, mode: 'grid' as const } });
    await wrapper.findAll('.card')[0].trigger('dblclick');
    expect(wrapper.emitted('activate')?.[0]?.[0]).toStrictEqual(items[0]);
  });

  it('grid mode: single click on card emits select with modifiers', async () => {
    const wrapper = mount(FileTable, { props: { ...baseProps, mode: 'grid' as const } });
    await wrapper.findAll('.card')[0].trigger('click', { shiftKey: true });
    const p = wrapper.emitted('select')![0][0] as { modifiers: { shift: boolean } };
    expect(p.modifiers.shift).toBe(true);
  });

  it('grid mode: temp folder in renaming state has temp row marker', () => {
    const tempItems = [
      {
        id: 'temp-new-folder-1',
        name: '新建文件夹-20260513-120000',
        itemType: 'folder' as const,
        size: 0,
        ownerName: '',
        createdAt: '2026-05-13T12:00:00Z',
        updatedAt: '2026-05-13T12:00:00Z',
        parentFolderId: 'root',
        isStarred: false,
      },
    ];
    const wrapper = mount(FileTable, {
      props: {
        ...baseProps,
        mode: 'grid' as const,
        items: tempItems,
        renamingId: 'temp-new-folder-1',
        renameValue: '新建文件夹-20260513-120000',
      },
    });

    expect(wrapper.find('[data-temp-folder-row="temp-new-folder-1"]').exists()).toBe(true);
  });
});
