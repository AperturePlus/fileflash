import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import BulkActionBar from './BulkActionBar.vue';

describe('BulkActionBar', () => {
  it('renders nothing when count is 0', () => {
    const wrapper = mount(BulkActionBar, { props: { count: 0 } });
    expect(wrapper.find('.bulk').exists()).toBe(false);
  });

  it('renders count when > 0 and emits delete', async () => {
    const wrapper = mount(BulkActionBar, { props: { count: 3 } });
    expect(wrapper.text()).toContain('3');
    await wrapper.find('[data-test="bulk-delete"]').trigger('click');
    expect(wrapper.emitted('delete')).toHaveLength(1);
  });

  it('emits move, download, clear', async () => {
    const wrapper = mount(BulkActionBar, { props: { count: 2 } });
    await wrapper.find('[data-test="bulk-move"]').trigger('click');
    await wrapper.find('[data-test="bulk-download"]').trigger('click');
    await wrapper.find('[data-test="bulk-clear"]').trigger('click');
    expect(wrapper.emitted('move')).toHaveLength(1);
    expect(wrapper.emitted('download')).toHaveLength(1);
    expect(wrapper.emitted('clear')).toHaveLength(1);
  });
});
