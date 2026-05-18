import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import MenuItem from './MenuItem.vue';

describe('molecules/MenuItem', () => {
  it('renders a <button> with the slot label', () => {
    const w = mount(MenuItem, { slots: { default: 'Settings' } });
    expect(w.find('button').exists()).toBe(true);
    expect(w.text()).toContain('Settings');
  });

  it('icon prop renders an Icon atom before the label', () => {
    const w = mount(MenuItem, { props: { icon: 'trash' }, slots: { default: 'Delete' } });
    expect(w.find('svg').exists()).toBe(true);
  });

  it('keyHint prop renders KeyHint kbd elements on the right', () => {
    const w = mount(MenuItem, {
      props: { keyHint: ['Ctrl', 'K'] },
      slots: { default: 'Search' },
    });
    expect(w.findAll('kbd').length).toBeGreaterThanOrEqual(2);
  });

  it('default variant applies ff-menuitem--default class', () => {
    const w = mount(MenuItem, { slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-menuitem--default');
  });

  it('variant=danger applies the danger class', () => {
    const w = mount(MenuItem, { props: { variant: 'danger' }, slots: { default: 'Delete' } });
    expect(w.classes()).toContain('ff-menuitem--danger');
  });

  it('emits click when pressed', async () => {
    const w = mount(MenuItem, { slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });

  it('disabled prop disables button + applies disabled class', () => {
    const w = mount(MenuItem, { props: { disabled: true }, slots: { default: 'x' } });
    expect(w.find('button').attributes('disabled')).toBeDefined();
    expect(w.classes()).toContain('ff-menuitem--disabled');
  });
});
