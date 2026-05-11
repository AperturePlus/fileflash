import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileToolbar from './FileToolbar.vue';

const baseProps = {
  viewMode: 'list' as const,
  sortKey: 'name' as const,
  sortDirection: 'asc' as const,
  searchQuery: '',
  isSearching: false,
};

describe('FileToolbar', () => {
  it('emits update:viewMode when switcher toggled', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    const options = wrapper.findAll('.ff-segmented-option');
    expect(options).toHaveLength(2);
    await options[1].trigger('click');
    expect(wrapper.emitted('update:viewMode')?.[0]?.[0]).toBe('grid');
  });

  it('emits create-folder on new folder click', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    await wrapper.find('[data-test="new-folder"]').trigger('click');
    expect(wrapper.emitted('create-folder')).toHaveLength(1);
  });

  it('emits upload on upload click', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    await wrapper.find('[data-test="upload"]').trigger('click');
    expect(wrapper.emitted('upload')).toHaveLength(1);
  });

  it('emits sort to next key when clicked', async () => {
    const wrapper = mount(FileToolbar, { props: { ...baseProps, sortKey: 'name' } });
    await wrapper.find('[data-test="sort"]').trigger('click');
    expect(wrapper.emitted('sort')?.[0]?.[0]).toBe('size');
  });
});
