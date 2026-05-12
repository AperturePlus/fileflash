import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import KeyHint from './KeyHint.vue';

describe('atoms/KeyHint', () => {
  it('renders each key inside a <kbd>', () => {
    const w = mount(KeyHint, { props: { keys: ['Ctrl', 'K'] } });
    const kbds = w.findAll('kbd');
    expect(kbds).toHaveLength(2);
    expect(kbds[0].text()).toBe('Ctrl');
    expect(kbds[1].text()).toBe('K');
  });

  it('renders a + separator between keys (not after the last)', () => {
    const w = mount(KeyHint, { props: { keys: ['Shift', 'Enter'] } });
    expect(w.findAll('.ff-keyhint-sep')).toHaveLength(1);
    expect(w.text()).toContain('+');
  });

  it('single key: no separator', () => {
    const w = mount(KeyHint, { props: { keys: ['Esc'] } });
    expect(w.findAll('kbd')).toHaveLength(1);
    expect(w.findAll('.ff-keyhint-sep')).toHaveLength(0);
  });

  it('marks itself aria-hidden (decorative)', () => {
    const w = mount(KeyHint, { props: { keys: ['Esc'] } });
    expect(w.attributes('aria-hidden')).toBe('true');
  });
});
