import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Input from './Input.vue';

describe('atoms/Input', () => {
  it('renders an <input type="text"> by default', () => {
    const w = mount(Input);
    const input = w.find('input');
    expect(input.exists()).toBe(true);
    expect(input.attributes('type')).toBe('text');
    expect(input.classes()).toContain('ff-input');
  });

  it('binds modelValue via v-model', async () => {
    const w = mount(Input, { props: { modelValue: 'hello' } });
    expect((w.find('input').element as HTMLInputElement).value).toBe('hello');
    await w.find('input').setValue('world');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['world']);
  });

  it('disabled prop disables the input', () => {
    const w = mount(Input, { props: { disabled: true } });
    expect(w.find('input').attributes('disabled')).toBeDefined();
  });

  it('invalid prop applies the invalid class', () => {
    const w = mount(Input, { props: { invalid: true } });
    expect(w.find('input').classes()).toContain('ff-input--invalid');
  });

  it('forwards type prop (e.g. password)', () => {
    const w = mount(Input, { props: { type: 'password' } });
    expect(w.find('input').attributes('type')).toBe('password');
  });

  it('passes placeholder through', () => {
    const w = mount(Input, { props: { placeholder: 'Type here' } });
    expect(w.find('input').attributes('placeholder')).toBe('Type here');
  });
});
