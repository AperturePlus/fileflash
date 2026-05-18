import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import BreadcrumbItem from './BreadcrumbItem.vue';

describe('molecules/BreadcrumbItem', () => {
  it('renders an <a> when href is provided', () => {
    const w = mount(BreadcrumbItem, {
      props: { href: '/files' },
      slots: { default: 'Files' },
    });
    const a = w.find('a');
    expect(a.exists()).toBe(true);
    expect(a.attributes('href')).toBe('/files');
    expect(a.text()).toBe('Files');
  });

  it('renders a current span (no <a>) when href is omitted', () => {
    const w = mount(BreadcrumbItem, { slots: { default: 'Current' } });
    expect(w.find('a').exists()).toBe(false);
    expect(w.find('.ff-breadcrumb-current').text()).toBe('Current');
  });

  it('renders the chevron separator when href is set', () => {
    const w = mount(BreadcrumbItem, {
      props: { href: '/files' },
      slots: { default: 'Files' },
    });
    expect(w.find('svg').exists()).toBe(true);
  });

  it('omits the chevron when href is not set (last item)', () => {
    const w = mount(BreadcrumbItem, { slots: { default: 'Current' } });
    expect(w.find('svg').exists()).toBe(false);
  });
});
