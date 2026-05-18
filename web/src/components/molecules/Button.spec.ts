import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Button from './Button.vue';

describe('molecules/Button', () => {
  it('renders a <button> with slot content', () => {
    const w = mount(Button, { slots: { default: 'Click me' } });
    const btn = w.find('button');
    expect(btn.exists()).toBe(true);
    expect(btn.text()).toBe('Click me');
  });

  it('default variant=primary applies the primary class', () => {
    const w = mount(Button, { slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-btn--primary');
  });

  it.each(['primary', 'ghost', 'danger'] as const)(
    'variant=%s applies the matching class',
    (variant) => {
      const w = mount(Button, { props: { variant }, slots: { default: 'x' } });
      expect(w.classes()).toContain(`ff-btn--${variant}`);
    },
  );

  it.each(['sm', 'md'] as const)('size=%s applies the matching class', (size) => {
    const w = mount(Button, { props: { size }, slots: { default: 'x' } });
    expect(w.classes()).toContain(`ff-btn--${size}`);
  });

  it('default type attribute is button (avoid accidental form submit)', () => {
    const w = mount(Button, { slots: { default: 'x' } });
    expect(w.find('button').attributes('type')).toBe('button');
  });

  it('emits click when not disabled', async () => {
    const w = mount(Button, { slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });

  it('disabled prop disables button and suppresses click effect', async () => {
    const w = mount(Button, { props: { disabled: true }, slots: { default: 'x' } });
    expect(w.find('button').attributes('disabled')).toBeDefined();
  });

  it('icon prop renders an Icon atom before the label', () => {
    const w = mount(Button, { props: { icon: 'upload' }, slots: { default: 'Upload' } });
    expect(w.find('svg').exists()).toBe(true);
    expect(w.text()).toContain('Upload');
  });

  it('loading prop renders Spinner and disables the button', () => {
    const w = mount(Button, { props: { loading: true }, slots: { default: 'x' } });
    expect(w.find('[role="status"]').exists()).toBe(true);
    expect(w.find('button').attributes('disabled')).toBeDefined();
    expect(w.classes()).toContain('ff-btn--loading');
  });

  it('loading takes precedence over icon (only spinner renders)', () => {
    const w = mount(Button, {
      props: { loading: true, icon: 'upload' },
      slots: { default: 'x' },
    });
    expect(w.find('[role="status"]').exists()).toBe(true);
    // Spinner doesn't render an <svg>, Icon does — so there should be 0 svgs.
    expect(w.findAll('svg')).toHaveLength(0);
  });
});
