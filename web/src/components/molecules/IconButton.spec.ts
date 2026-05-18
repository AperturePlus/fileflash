import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import IconButton from './IconButton.vue';

describe('molecules/IconButton', () => {
  it('renders a button containing the requested icon and no visible text', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'Close' } });
    expect(w.find('svg').exists()).toBe(true);
    expect(w.find('button').text()).toBe('');
  });

  it('label prop is required for a11y (used as aria-label)', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'Close dialog' } });
    expect(w.find('button').attributes('aria-label')).toBe('Close dialog');
  });

  it('default variant is ghost', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'x' } });
    expect(w.classes()).toContain('ff-iconbtn--ghost');
  });

  it.each(['ghost', 'primary'] as const)('variant=%s applies matching class', (variant) => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'x', variant } });
    expect(w.classes()).toContain(`ff-iconbtn--${variant}`);
  });

  it('emits click when pressed', async () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });

  it('disabled prop disables button', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'x', disabled: true } });
    expect(w.find('button').attributes('disabled')).toBeDefined();
  });
});
