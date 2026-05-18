import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FolderTreeNode from './FolderTreeNode.vue';
import type { FolderItem } from '../../../types/file';

describe('FolderTreeNode', () => {
  it('renders folder name', () => {
    const node: FolderItem = {
      id: 'f1',
      name: 'Documents',
      itemType: 'folder',
    } as FolderItem;
    const wrapper = mount(FolderTreeNode, {
      props: { node, selectedFolderId: null },
    });
    expect(wrapper.text()).toContain('Documents');
  });
});
