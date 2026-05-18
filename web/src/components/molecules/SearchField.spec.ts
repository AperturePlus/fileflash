import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import SearchField from './SearchField.vue';

describe('molecules/SearchField', () => {
  it('renders an input with a leading search icon', () => {
    const w = mount(SearchField, { props: { modelValue: '' } });
    expect(w.find('input').exists()).toBe(true);
    expect(w.find('svg').exists()).toBe(true);
  });

  it('default placeholder is "Search…"', () => {
    const w = mount(SearchField, { props: { modelValue: '' } });
    expect(w.find('input').attributes('placeholder')).toBe('Search…');
  });

  it('respects custom placeholder', () => {
    const w = mount(SearchField, {
      props: { modelValue: '', placeholder: 'Find files' },
    });
    expect(w.find('input').attributes('placeholder')).toBe('Find files');
  });

  it('emits update on typing', async () => {
    const w = mount(SearchField, { props: { modelValue: '' } });
    await w.find('input').setValue('hello');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['hello']);
  });

  it('renders the clear button when modelValue is non-empty', () => {
    const w = mount(SearchField, { props: { modelValue: 'q' } });
    expect(w.find('button[aria-label="Clear"]').exists()).toBe(true);
  });

  it('hides the clear button when modelValue is empty', () => {
    const w = mount(SearchField, { props: { modelValue: '' } });
    expect(w.find('button[aria-label="Clear"]').exists()).toBe(false);
  });

  it('clicking clear emits update with empty string', async () => {
    const w = mount(SearchField, { props: { modelValue: 'query' } });
    await w.find('button[aria-label="Clear"]').trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['']);
  });
});
