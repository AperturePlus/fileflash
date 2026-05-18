import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import StatBlock from './StatBlock.vue';

describe('molecules/StatBlock', () => {
  it('renders the label and value', () => {
    const w = mount(StatBlock, { props: { label: 'TOTAL', value: '2,486' } });
    expect(w.text()).toContain('TOTAL');
    expect(w.text()).toContain('2,486');
  });

  it('value is rendered via MonoNumber atom (.ff-num)', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100' } });
    expect(w.find('.ff-num').exists()).toBe(true);
  });

  it('no delta: no delta indicator rendered', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100' } });
    expect(w.find('.ff-statblock-delta').exists()).toBe(false);
  });

  it('positive delta shows up arrow + up tone', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100', delta: 5 } });
    const delta = w.find('.ff-statblock-delta');
    expect(delta.exists()).toBe(true);
    expect(delta.classes()).toContain('ff-statblock-delta--up');
    expect(delta.text()).toContain('↑');
    expect(delta.text()).toContain('5');
  });

  it('negative delta shows down arrow + down tone with absolute value', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100', delta: -3 } });
    const delta = w.find('.ff-statblock-delta');
    expect(delta.exists()).toBe(true);
    expect(delta.classes()).toContain('ff-statblock-delta--down');
    expect(delta.text()).toContain('↓');
    expect(delta.text()).toContain('3');
  });
});
