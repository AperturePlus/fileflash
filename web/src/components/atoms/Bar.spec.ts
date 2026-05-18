import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Bar from './Bar.vue';

describe('atoms/Bar', () => {
  it('renders a <div> with inline width derived from value', () => {
    const w = mount(Bar, { props: { value: 0.64 } });
    expect((w.element as HTMLElement).style.width).toBe('64%');
  });

  it('clamps value below 0 to 0%', () => {
    const w = mount(Bar, { props: { value: -0.5 } });
    expect((w.element as HTMLElement).style.width).toBe('0%');
  });

  it('clamps value above 1 to 100%', () => {
    const w = mount(Bar, { props: { value: 1.5 } });
    expect((w.element as HTMLElement).style.width).toBe('100%');
  });

  it('default tone class is accent', () => {
    const w = mount(Bar, { props: { value: 0.5 } });
    expect(w.classes()).toContain('ff-bar--accent');
  });

  it.each(['accent', 'success', 'warning', 'error', 'info'] as const)(
    'tone=%s applies the matching class',
    (tone) => {
      const w = mount(Bar, { props: { value: 0.5, tone } });
      expect(w.classes()).toContain(`ff-bar--${tone}`);
    },
  );
});
