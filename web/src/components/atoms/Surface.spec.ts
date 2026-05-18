import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Surface from './Surface.vue';

describe('atoms/Surface', () => {
  it('renders a div with the base elevation class by default', () => {
    const w = mount(Surface, { slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-surface');
    expect(w.classes()).toContain('ff-surface--base');
  });

  it.each(['base', 'raised', 'inset'] as const)(
    'elevation=%s applies the matching class',
    (elevation) => {
      const w = mount(Surface, { props: { elevation }, slots: { default: 'x' } });
      expect(w.classes()).toContain(`ff-surface--${elevation}`);
    },
  );

  it('bordered prop toggles the bordered class', () => {
    const plain = mount(Surface, { slots: { default: 'x' } });
    const bordered = mount(Surface, { props: { bordered: true }, slots: { default: 'x' } });
    expect(plain.classes()).not.toContain('ff-surface--bordered');
    expect(bordered.classes()).toContain('ff-surface--bordered');
  });

  it('renders slot content', () => {
    const w = mount(Surface, { slots: { default: 'inner content' } });
    expect(w.text()).toBe('inner content');
  });
});
