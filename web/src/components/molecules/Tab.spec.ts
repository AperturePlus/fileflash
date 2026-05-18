import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Tab from './Tab.vue';

describe('molecules/Tab', () => {
  it('renders a <button> with the slot label', () => {
    const w = mount(Tab, { props: { active: false }, slots: { default: 'Files' } });
    expect(w.find('button').text()).toBe('Files');
  });

  it('active=true applies the active class', () => {
    const w = mount(Tab, { props: { active: true }, slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-tab--active');
  });

  it('active=false does not apply the active class', () => {
    const w = mount(Tab, { props: { active: false }, slots: { default: 'x' } });
    expect(w.classes()).not.toContain('ff-tab--active');
  });

  it('emits click when pressed', async () => {
    const w = mount(Tab, { props: { active: false }, slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });
});
