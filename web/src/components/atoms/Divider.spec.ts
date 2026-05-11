import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Divider from './Divider.vue';

describe('atoms/Divider', () => {
  it('renders an <hr> by default (horizontal)', () => {
    const w = mount(Divider);
    expect(w.find('hr').exists()).toBe(true);
    expect(w.classes()).toContain('ff-divider--h');
  });

  it('renders a <span> when orientation=vertical', () => {
    const w = mount(Divider, { props: { orientation: 'vertical' } });
    expect(w.find('hr').exists()).toBe(false);
    const span = w.find('span');
    expect(span.exists()).toBe(true);
    expect(span.classes()).toContain('ff-divider--v');
  });

  it('vertical orientation marks itself aria-hidden', () => {
    const w = mount(Divider, { props: { orientation: 'vertical' } });
    expect(w.find('span').attributes('aria-hidden')).toBe('true');
  });

  it('always carries the base ff-divider class', () => {
    const h = mount(Divider);
    const v = mount(Divider, { props: { orientation: 'vertical' } });
    expect(h.classes()).toContain('ff-divider');
    expect(v.classes()).toContain('ff-divider');
  });
});
