import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import TextField from './TextField.vue';

describe('molecules/TextField', () => {
  it('renders a <label> tied to the <input> via for/id', () => {
    const w = mount(TextField, { props: { modelValue: '', label: 'Username' } });
    const labelEl = w.find('label');
    const inputEl = w.find('input');
    expect(labelEl.text()).toContain('Username');
    expect(labelEl.attributes('for')).toBeTruthy();
    expect(labelEl.attributes('for')).toBe(inputEl.attributes('id'));
  });

  it('binds modelValue via v-model', async () => {
    const w = mount(TextField, { props: { modelValue: 'a', label: 'L' } });
    expect((w.find('input').element as HTMLInputElement).value).toBe('a');
    await w.find('input').setValue('b');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['b']);
  });

  it('error prop renders the error message and applies invalid input class', () => {
    const w = mount(TextField, {
      props: { modelValue: '', label: 'L', error: 'Required' },
    });
    expect(w.text()).toContain('Required');
    expect(w.find('input').classes()).toContain('ff-input--invalid');
  });

  it('hint prop renders helper text below the input', () => {
    const w = mount(TextField, {
      props: { modelValue: '', label: 'L', hint: 'Min 8 chars' },
    });
    expect(w.text()).toContain('Min 8 chars');
  });

  it('error takes precedence over hint when both are set', () => {
    const w = mount(TextField, {
      props: { modelValue: '', label: 'L', hint: 'helper', error: 'oops' },
    });
    expect(w.text()).toContain('oops');
    expect(w.text()).not.toContain('helper');
  });

  it('forwards type prop (e.g. password)', () => {
    const w = mount(TextField, {
      props: { modelValue: '', label: 'L', type: 'password' },
    });
    expect(w.find('input').attributes('type')).toBe('password');
  });

  it('disabled prop disables the underlying input', () => {
    const w = mount(TextField, {
      props: { modelValue: '', label: 'L', disabled: true },
    });
    expect(w.find('input').attributes('disabled')).toBeDefined();
  });
});
