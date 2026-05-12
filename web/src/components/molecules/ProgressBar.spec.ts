import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import ProgressBar from './ProgressBar.vue';

describe('molecules/ProgressBar', () => {
  it('renders the Bar atom and a rounded percent value', () => {
    const w = mount(ProgressBar, { props: { value: 0.64 } });
    expect(w.text()).toContain('64%');
    expect(w.find('.ff-bar').exists()).toBe(true);
  });

  it('clamps value above 1 to 100%', () => {
    const w = mount(ProgressBar, { props: { value: 1.5 } });
    expect(w.text()).toContain('100%');
  });

  it('clamps value below 0 to 0%', () => {
    const w = mount(ProgressBar, { props: { value: -0.2 } });
    expect(w.text()).toContain('0%');
  });

  it('default label slot shows "PROGRESS"', () => {
    const w = mount(ProgressBar, { props: { value: 0.5 } });
    expect(w.text()).toContain('PROGRESS');
  });

  it('label slot override renders custom content', () => {
    const w = mount(ProgressBar, {
      props: { value: 0.5 },
      slots: { label: 'Uploading' },
    });
    expect(w.text()).toContain('Uploading');
    expect(w.text()).not.toContain('PROGRESS');
  });

  it('tone is forwarded to the Bar atom', () => {
    const w = mount(ProgressBar, { props: { value: 0.5, tone: 'error' } });
    expect(w.find('.ff-bar').classes()).toContain('ff-bar--error');
  });
});
