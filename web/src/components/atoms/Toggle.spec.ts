import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Toggle from './Toggle.vue';

describe('atoms/Toggle', () => {
  it('renders a button with role=switch', () => {
    const w = mount(Toggle, { props: { modelValue: false } });
    const btn = w.find('button');
    expect(btn.exists()).toBe(true);
    expect(btn.attributes('role')).toBe('switch');
  });

  it('aria-checked reflects modelValue', () => {
    const off = mount(Toggle, { props: { modelValue: false } });
    const on = mount(Toggle, { props: { modelValue: true } });
    expect(off.find('button').attributes('aria-checked')).toBe('false');
    expect(on.find('button').attributes('aria-checked')).toBe('true');
  });

  it('on state applies ff-toggle--on class', () => {
    const w = mount(Toggle, { props: { modelValue: true } });
    expect(w.classes()).toContain('ff-toggle--on');
  });

  it('emits update with negated value on click', async () => {
    const w = mount(Toggle, { props: { modelValue: false } });
    await w.find('button').trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true]);
  });

  it('disabled prop blocks click emission', async () => {
    const w = mount(Toggle, { props: { modelValue: false, disabled: true } });
    await w.find('button').trigger('click');
    expect(w.emitted('update:modelValue')).toBeUndefined();
    expect(w.find('button').attributes('disabled')).toBeDefined();
    expect(w.classes()).toContain('ff-toggle--disabled');
  });

  it('renders label text when provided', () => {
    const w = mount(Toggle, { props: { modelValue: false, label: 'Notifications' } });
    expect(w.text()).toContain('Notifications');
  });
});
