import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Checkbox from './Checkbox.vue';

describe('atoms/Checkbox', () => {
  it('renders a hidden native checkbox + custom box', () => {
    const w = mount(Checkbox, { props: { modelValue: false } });
    expect(w.find('input[type="checkbox"]').exists()).toBe(true);
    expect(w.find('.ff-checkbox-box').exists()).toBe(true);
  });

  it('checked state applies the checked class on the label', () => {
    const off = mount(Checkbox, { props: { modelValue: false } });
    const on = mount(Checkbox, { props: { modelValue: true } });
    expect(off.classes()).not.toContain('ff-checkbox--checked');
    expect(on.classes()).toContain('ff-checkbox--checked');
  });

  it('shows the check icon only when checked', () => {
    const off = mount(Checkbox, { props: { modelValue: false } });
    const on = mount(Checkbox, { props: { modelValue: true } });
    expect(off.findAll('svg')).toHaveLength(0);
    expect(on.findAll('svg')).toHaveLength(1);
  });

  it('emits update:modelValue with new boolean on change', async () => {
    const w = mount(Checkbox, { props: { modelValue: false } });
    await w.find('input').setValue(true);
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true]);
  });

  it('disabled prop blocks native input', () => {
    const w = mount(Checkbox, { props: { modelValue: false, disabled: true } });
    expect(w.find('input').attributes('disabled')).toBeDefined();
    expect(w.classes()).toContain('ff-checkbox--disabled');
  });

  it('renders the label text when provided', () => {
    const w = mount(Checkbox, { props: { modelValue: false, label: 'Accept' } });
    expect(w.text()).toContain('Accept');
  });

  it('binds <label for> to the native input id', () => {
    const w = mount(Checkbox, { props: { modelValue: false } });
    const labelFor = w.find('label').attributes('for');
    const inputId = w.find('input').attributes('id');
    expect(labelFor).toBeTruthy();
    expect(labelFor).toBe(inputId);
  });
});
