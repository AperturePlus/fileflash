import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Icon from './Icon.vue';

describe('atoms/Icon', () => {
  it('renders an <svg> containing a <path> for the requested icon', () => {
    const w = mount(Icon, { props: { name: 'search' } });
    const svg = w.find('svg');
    expect(svg.exists()).toBe(true);
    const path = svg.find('path');
    expect(path.exists()).toBe(true);
    expect(path.attributes('d')).toContain('M11 4a7 7 0 1 0');
  });

  it('default size is 18px (width + height attrs)', () => {
    const w = mount(Icon, { props: { name: 'check' } });
    expect(w.find('svg').attributes('width')).toBe('18');
    expect(w.find('svg').attributes('height')).toBe('18');
  });

  it('respects custom size prop', () => {
    const w = mount(Icon, { props: { name: 'check', size: 24 } });
    expect(w.find('svg').attributes('width')).toBe('24');
    expect(w.find('svg').attributes('height')).toBe('24');
  });

  it('uses currentColor for stroke', () => {
    const w = mount(Icon, { props: { name: 'check' } });
    expect(w.find('svg').attributes('stroke')).toBe('currentColor');
  });

  it('decorative by default — aria-hidden="true" with no role/label', () => {
    const w = mount(Icon, { props: { name: 'check' } });
    const svg = w.find('svg');
    expect(svg.attributes('aria-hidden')).toBe('true');
    expect(svg.attributes('role')).toBeUndefined();
    expect(svg.attributes('aria-label')).toBeUndefined();
  });

  it('label prop exposes accessibility attributes', () => {
    const w = mount(Icon, { props: { name: 'check', label: 'Done' } });
    const svg = w.find('svg');
    expect(svg.attributes('aria-hidden')).toBeUndefined();
    expect(svg.attributes('role')).toBe('img');
    expect(svg.attributes('aria-label')).toBe('Done');
  });

  it('renders the list icon (three rows with leading dots)', () => {
    const w = mount(Icon, { props: { name: 'list' } });
    const d = w.find('svg path').attributes('d') ?? '';
    expect(d).toContain('M3 6h.01');
    expect(d).toContain('M8 6h13');
  });

  it('renders the grid icon (four 7x7 squares)', () => {
    const w = mount(Icon, { props: { name: 'grid' } });
    const d = w.find('svg path').attributes('d') ?? '';
    expect(d).toContain('M4 4h7v7H4z');
    expect(d).toContain('M13 13h7v7h-7z');
  });
});
