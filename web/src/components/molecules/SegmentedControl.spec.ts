import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import SegmentedControl from './SegmentedControl.vue';

describe('molecules/SegmentedControl', () => {
  it('renders one button per option', () => {
    const opts = [
      { value: 'a', label: 'A' },
      { value: 'b', label: 'B' },
      { value: 'c', label: 'C' },
    ];
    const w = mount(SegmentedControl, { props: { modelValue: 'a', options: opts } });
    expect(w.findAll('button')).toHaveLength(3);
  });

  it('marks the active option with aria-pressed=true and the matching class', () => {
    const opts = [
      { value: 'a', label: 'A' },
      { value: 'b', label: 'B' },
    ];
    const w = mount(SegmentedControl, { props: { modelValue: 'b', options: opts } });
    const buttons = w.findAll('button');
    expect(buttons[0].attributes('aria-pressed')).toBe('false');
    expect(buttons[1].attributes('aria-pressed')).toBe('true');
    expect(buttons[1].classes()).toContain('ff-segmented-option--active');
    expect(buttons[0].classes()).not.toContain('ff-segmented-option--active');
  });

  it('clicking a button emits update with that option value', async () => {
    const opts = [
      { value: 'a', label: 'A' },
      { value: 'b', label: 'B' },
    ];
    const w = mount(SegmentedControl, { props: { modelValue: 'a', options: opts } });
    await w.findAll('button')[1].trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['b']);
  });

  it('renders the role=group on the wrapper', () => {
    const w = mount(SegmentedControl, {
      props: { modelValue: 'a', options: [{ value: 'a', label: 'A' }] },
    });
    expect(w.attributes('role')).toBe('group');
  });

  it('disabled prop disables every button', () => {
    const opts = [
      { value: 'a', label: 'A' },
      { value: 'b', label: 'B' },
    ];
    const w = mount(SegmentedControl, {
      props: { modelValue: 'a', options: opts, disabled: true },
    });
    const buttons = w.findAll('button');
    expect(buttons[0].attributes('disabled')).toBeDefined();
    expect(buttons[1].attributes('disabled')).toBeDefined();
  });

  it('renders <Icon> when option has icon set', () => {
    const opts = [
      { value: 'list', label: '', icon: 'list' as const, ariaLabel: 'List view' },
      { value: 'grid', label: '', icon: 'grid' as const, ariaLabel: 'Grid view' },
    ];
    const w = mount(SegmentedControl, {
      props: { modelValue: 'list', options: opts },
    });
    const buttons = w.findAll('button');
    expect(buttons[0].find('svg').exists()).toBe(true);
    expect(buttons[1].find('svg').exists()).toBe(true);
  });

  it('exposes ariaLabel as aria-label attribute', () => {
    const opts = [
      { value: 'list', label: '', icon: 'list' as const, ariaLabel: 'List view' },
      { value: 'grid', label: '', icon: 'grid' as const, ariaLabel: 'Grid view' },
    ];
    const w = mount(SegmentedControl, {
      props: { modelValue: 'list', options: opts },
    });
    const buttons = w.findAll('button');
    expect(buttons[0].attributes('aria-label')).toBe('List view');
    expect(buttons[1].attributes('aria-label')).toBe('Grid view');
  });
});
