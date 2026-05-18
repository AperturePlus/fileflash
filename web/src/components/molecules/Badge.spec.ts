import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Badge from './Badge.vue';

describe('molecules/Badge', () => {
  it('renders the slot text', () => {
    const w = mount(Badge, { slots: { default: 'LIVE' } });
    expect(w.text()).toBe('LIVE');
  });

  it('default tone is success', () => {
    const w = mount(Badge, { slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-badge--success');
  });

  it.each(['success', 'warning', 'error', 'info', 'accent'] as const)(
    'tone=%s applies the matching class',
    (tone) => {
      const w = mount(Badge, { props: { tone }, slots: { default: 'x' } });
      expect(w.classes()).toContain(`ff-badge--${tone}`);
    },
  );

  it('always carries the base ff-badge class', () => {
    const w = mount(Badge, { props: { tone: 'error' }, slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-badge');
  });
});
