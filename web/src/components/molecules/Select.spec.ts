import { describe, it, expect, afterEach, vi } from 'vitest';
import { mount } from '../../test/mount';
import Select from './Select.vue';

const cleanup = () => document.body.replaceChildren();

const OPTS = [
  { value: 'a', label: 'Apple' },
  { value: 'b', label: 'Banana' },
  { value: 'c', label: 'Cherry' },
];

describe('molecules/Select', () => {
  afterEach(cleanup);

  it('renders the label of the option whose value === modelValue', () => {
    const w = mount(Select, { props: { modelValue: 'b', options: OPTS } });
    expect(w.text()).toContain('Banana');
  });

  it('renders the placeholder when no option matches', () => {
    const w = mount(Select, {
      props: { modelValue: 'zz', options: OPTS, placeholder: 'Pick one' },
    });
    expect(w.text()).toContain('Pick one');
  });

  it('click trigger opens menu; click option emits and hides menu', async () => {
    const w = mount(Select, {
      props: { modelValue: 'a', options: OPTS },
      attachTo: document.body,
    });
    expect(w.find('.ff-select__menu').exists()).toBe(false);
    await w.find('.ff-select__trigger').trigger('click');
    expect(w.find('.ff-select__menu').exists()).toBe(true);
    const items = w.findAll('.ff-select__option');
    expect(items.length).toBe(3);
    await items[2].trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['c']);
    expect(w.find('.ff-select__menu').exists()).toBe(false);
  });

  it('Esc on open menu closes it', async () => {
    const w = mount(Select, {
      props: { modelValue: 'a', options: OPTS },
      attachTo: document.body,
    });
    await w.find('.ff-select__trigger').trigger('click');
    expect(w.find('.ff-select__menu').exists()).toBe(true);
    await w.find('.ff-select').trigger('keydown', { key: 'Escape' });
    expect(w.find('.ff-select__menu').exists()).toBe(false);
  });

  it('opens upward when there is not enough room below the trigger', async () => {
    const originalInner = window.innerHeight;
    Object.defineProperty(window, 'innerHeight', { value: 600, configurable: true });
    const w = mount(Select, {
      props: { modelValue: 'a', options: OPTS },
      attachTo: document.body,
    });
    const root = w.find('.ff-select').element as HTMLElement;
    vi.spyOn(root, 'getBoundingClientRect').mockReturnValue({
      x: 0, y: 580, top: 580, bottom: 596,
      left: 0, right: 120, width: 120, height: 16,
      toJSON: () => undefined,
    } as DOMRect);

    await w.find('.ff-select__trigger').trigger('click');
    const menu = w.find('.ff-select__menu');
    expect(menu.exists()).toBe(true);
    expect(menu.classes()).toContain('ff-select__menu--up');

    Object.defineProperty(window, 'innerHeight', { value: originalInner, configurable: true });
  });

  it('opens downward when there is room below the trigger', async () => {
    const originalInner = window.innerHeight;
    Object.defineProperty(window, 'innerHeight', { value: 800, configurable: true });
    const w = mount(Select, {
      props: { modelValue: 'a', options: OPTS },
      attachTo: document.body,
    });
    const root = w.find('.ff-select').element as HTMLElement;
    vi.spyOn(root, 'getBoundingClientRect').mockReturnValue({
      x: 0, y: 100, top: 100, bottom: 132,
      left: 0, right: 120, width: 120, height: 32,
      toJSON: () => undefined,
    } as DOMRect);

    await w.find('.ff-select__trigger').trigger('click');
    const menu = w.find('.ff-select__menu');
    expect(menu.exists()).toBe(true);
    expect(menu.classes()).toContain('ff-select__menu--down');

    Object.defineProperty(window, 'innerHeight', { value: originalInner, configurable: true });
  });
});
