import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Radio from './Radio.vue';

describe('atoms/Radio', () => {
  it('renders a native radio input and decorative dot', () => {
    const w = mount(Radio, { props: { modelValue: 'a', value: 'a', name: 'g' } });
    expect(w.find('input[type="radio"]').exists()).toBe(true);
    expect(w.find('.ff-radio-dot').exists()).toBe(true);
  });

  it('selected when modelValue === value', () => {
    const selected = mount(Radio, { props: { modelValue: 'a', value: 'a', name: 'g' } });
    const other = mount(Radio, { props: { modelValue: 'b', value: 'a', name: 'g' } });
    expect(selected.classes()).toContain('ff-radio--checked');
    expect(other.classes()).not.toContain('ff-radio--checked');
  });

  it('emits update with own value on change', async () => {
    const w = mount(Radio, { props: { modelValue: 'b', value: 'a', name: 'g' } });
    await w.find('input').setValue(true);
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['a']);
  });

  it('binds <label for> to the native input id', () => {
    const w = mount(Radio, { props: { modelValue: 'a', value: 'a', name: 'g' } });
    const labelFor = w.find('label').attributes('for');
    const inputId = w.find('input').attributes('id');
    expect(labelFor).toBe(inputId);
  });

  it('disabled prop disables native input + applies disabled class', () => {
    const w = mount(Radio, { props: { modelValue: 'a', value: 'a', name: 'g', disabled: true } });
    expect(w.find('input').attributes('disabled')).toBeDefined();
    expect(w.classes()).toContain('ff-radio--disabled');
  });
});
