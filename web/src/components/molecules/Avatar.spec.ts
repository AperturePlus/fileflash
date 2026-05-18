import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Avatar from './Avatar.vue';

describe('molecules/Avatar', () => {
  it('renders an <img> when src is provided, with alt=name', () => {
    const w = mount(Avatar, { props: { src: '/x.png', name: 'Alice' } });
    const img = w.find('img');
    expect(img.exists()).toBe(true);
    expect(img.attributes('src')).toBe('/x.png');
    expect(img.attributes('alt')).toBe('Alice');
  });

  it('renders initials fallback (first + last) when no src', () => {
    const w = mount(Avatar, { props: { name: 'Alice Wong' } });
    expect(w.find('img').exists()).toBe(false);
    expect(w.text()).toBe('AW');
  });

  it('single-name fallback uses first two letters', () => {
    const w = mount(Avatar, { props: { name: 'alice' } });
    expect(w.text()).toBe('AL');
  });

  it('falls back to "?" when name is empty', () => {
    const w = mount(Avatar, { props: { name: '' } });
    expect(w.text()).toBe('?');
  });

  it('default size class is md', () => {
    const w = mount(Avatar, { props: { name: 'A' } });
    expect(w.classes()).toContain('ff-avatar--md');
  });

  it.each(['sm', 'md'] as const)('size=%s applies the matching class', (size) => {
    const w = mount(Avatar, { props: { name: 'A', size } });
    expect(w.classes()).toContain(`ff-avatar--${size}`);
  });
});
