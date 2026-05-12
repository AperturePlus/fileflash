import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Text from './Text.vue';

// Test strategy note (applies to all atoms/molecules in P1):
// happy-dom and jsdom both fail to resolve var() inside class-based CSS rules
// from getComputedStyle. We therefore test the *contract* of the component —
// the class name applied for each variant — rather than the resolved computed
// style. The CSS-variable wiring itself is verified statically (every rule
// lives in `web/src/styles/tokens/*.css` and the component's <style scoped>
// block) and visually via the dev library page in P1 Task 22.

describe('atoms/Text', () => {
  it('renders default body variant in a <span>', () => {
    const w = mount(Text, { slots: { default: 'hello' } });
    const el = w.find('span');
    expect(el.exists()).toBe(true);
    expect(el.text()).toBe('hello');
  });

  it.each([
    'display',
    'h1',
    'h2',
    'body',
    'small',
    'label',
    'data',
  ] as const)('variant=%s applies the matching class', (variant) => {
    const w = mount(Text, { props: { variant }, slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-text');
    expect(w.classes()).toContain(`ff-text--${variant}`);
  });

  it('renders as <h1> when as="h1" is passed', () => {
    const w = mount(Text, { props: { as: 'h1', variant: 'display' }, slots: { default: 'Title' } });
    expect(w.find('h1').exists()).toBe(true);
  });

  it('renders custom element when as="p"', () => {
    const w = mount(Text, { props: { as: 'p' }, slots: { default: 'paragraph' } });
    expect(w.find('p').exists()).toBe(true);
    expect(w.find('p').text()).toBe('paragraph');
  });

  it('forwards slot content unchanged', () => {
    const w = mount(Text, { slots: { default: 'mixed 中英 12.5%' } });
    expect(w.text()).toBe('mixed 中英 12.5%');
  });
});
