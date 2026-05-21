import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Pagination from './Pagination.vue';

describe('molecules/Pagination', () => {
  it('renders 5 page buttons when total=50, pageSize=10', () => {
    const w = mount(Pagination, { props: { page: 1, pageSize: 10, total: 50 } });
    // 5 numeric page buttons + prev + next = 7
    const buttons = w.findAll('button');
    expect(buttons.length).toBe(7);
    // Numeric labels 1..5 present
    const labels = buttons.map((b) => b.text());
    for (const n of ['1', '2', '3', '4', '5']) {
      expect(labels).toContain(n);
    }
  });

  it('prev disabled at page 1, next disabled at last page', () => {
    const a = mount(Pagination, { props: { page: 1, pageSize: 10, total: 50 } });
    const aButtons = a.findAll('button');
    expect(aButtons[0].attributes('disabled')).toBeDefined();
    expect(aButtons[aButtons.length - 1].attributes('disabled')).toBeUndefined();

    const b = mount(Pagination, { props: { page: 5, pageSize: 10, total: 50 } });
    const bButtons = b.findAll('button');
    expect(bButtons[0].attributes('disabled')).toBeUndefined();
    expect(bButtons[bButtons.length - 1].attributes('disabled')).toBeDefined();
  });

  it('clicking a numeric page button emits update:page with that number', async () => {
    const w = mount(Pagination, { props: { page: 1, pageSize: 10, total: 50 } });
    const btn3 = w.findAll('button').find((b) => b.text() === '3');
    expect(btn3).toBeTruthy();
    await btn3!.trigger('click');
    expect(w.emitted('update:page')?.[0]).toEqual([3]);
  });

  it('renders nothing when total <= pageSize', () => {
    const w = mount(Pagination, { props: { page: 1, pageSize: 10, total: 5 } });
    expect(w.find('nav').exists()).toBe(false);
  });
});
