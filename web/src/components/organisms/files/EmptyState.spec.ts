import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import EmptyState from './EmptyState.vue';

describe('EmptyState', () => {
  it('renders loading variant with spinner role', () => {
    const wrapper = mount(EmptyState, { props: { variant: 'loading' } });
    expect(wrapper.find('[data-variant="loading"]').exists()).toBe(true);
    expect(wrapper.find('.ff-spinner').exists()).toBe(true);
  });

  it('renders empty variant copy', () => {
    const wrapper = mount(EmptyState, { props: { variant: 'empty' } });
    expect(wrapper.text()).toMatch(/This folder is empty|此文件夹为空/);
  });

  it('renders no-results variant with quoted query', () => {
    const wrapper = mount(EmptyState, {
      props: { variant: 'no-results', query: 'foo.txt' },
    });
    expect(wrapper.text()).toContain('"foo.txt"');
  });
});
