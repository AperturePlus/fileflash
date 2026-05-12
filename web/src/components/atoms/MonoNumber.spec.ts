import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import MonoNumber from './MonoNumber.vue';

describe('atoms/MonoNumber', () => {
  it('renders the value inside a span', () => {
    const w = mount(MonoNumber, { props: { value: '2.4 MB' } });
    const el = w.find('span');
    expect(el.exists()).toBe(true);
    expect(el.text()).toBe('2.4 MB');
  });

  it('accepts numeric values', () => {
    const w = mount(MonoNumber, { props: { value: 42 } });
    expect(w.find('span').text()).toBe('42');
  });

  it('applies the ff-num base class always', () => {
    const w = mount(MonoNumber, { props: { value: '1' } });
    expect(w.classes()).toContain('ff-num');
  });

  it('accent prop toggles the accent class', () => {
    const plain = mount(MonoNumber, { props: { value: '1' } });
    const accent = mount(MonoNumber, { props: { value: '1', accent: true } });
    expect(plain.classes()).not.toContain('ff-num--accent');
    expect(accent.classes()).toContain('ff-num--accent');
  });
});
