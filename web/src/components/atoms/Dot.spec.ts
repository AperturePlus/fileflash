import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Dot from './Dot.vue';

describe('atoms/Dot', () => {
  it('renders a <span> with aria-hidden', () => {
    const w = mount(Dot);
    const el = w.find('span');
    expect(el.exists()).toBe(true);
    expect(el.attributes('aria-hidden')).toBe('true');
  });

  it('default tone is accent', () => {
    const w = mount(Dot);
    expect(w.classes()).toContain('ff-dot--accent');
  });

  it.each(['accent', 'success', 'warning', 'error', 'info'] as const)(
    'tone=%s applies the matching class',
    (tone) => {
      const w = mount(Dot, { props: { tone } });
      expect(w.classes()).toContain(`ff-dot--${tone}`);
    },
  );

  it('always carries the base ff-dot class', () => {
    const w = mount(Dot, { props: { tone: 'error' } });
    expect(w.classes()).toContain('ff-dot');
  });
});
