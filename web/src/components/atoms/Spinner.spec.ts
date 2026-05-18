import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Spinner from './Spinner.vue';

describe('atoms/Spinner', () => {
  it('renders a div with role=status', () => {
    const w = mount(Spinner);
    expect(w.attributes('role')).toBe('status');
  });

  it('default label is "Loading" inside the visually-hidden region', () => {
    const w = mount(Spinner);
    expect(w.find('.ff-visually-hidden').text()).toBe('Loading');
  });

  it('custom label propagates to the visually-hidden region', () => {
    const w = mount(Spinner, { props: { label: 'Uploading file' } });
    expect(w.find('.ff-visually-hidden').text()).toBe('Uploading file');
  });

  it('renders 3 scan bars (the B-style indicator)', () => {
    const w = mount(Spinner);
    expect(w.findAll('.ff-spinner-bar')).toHaveLength(3);
  });
});
