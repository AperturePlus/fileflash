import { describe, it, expect, afterEach } from 'vitest';
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
});
