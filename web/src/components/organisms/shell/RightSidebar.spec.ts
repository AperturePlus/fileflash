import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import RightSidebar from './RightSidebar.vue';

describe('components/organisms/shell/RightSidebar', () => {
  it('renders a placeholder when visible', () => {
    const w = mount(RightSidebar, { props: { visible: true } });
    expect(w.find('.right-sidebar').exists()).toBe(true);
    expect(w.text()).toContain('Reserved');
  });

  it('hides via class when not visible', () => {
    const w = mount(RightSidebar, { props: { visible: false } });
    expect(w.find('.right-sidebar.visible').exists()).toBe(false);
  });
});
