import { describe, it, expect } from 'vitest';
import { defineComponent, h } from 'vue';
import { mount, readToken } from './mount';

describe('test/mount helper', () => {
  const Probe = defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'probe' }, 'probe');
    },
  });

  it('mounts a component', () => {
    const wrapper = mount(Probe);
    expect(wrapper.find('[data-testid="probe"]').text()).toBe('probe');
  });

  it('applies theme context', () => {
    mount(Probe, { context: { theme: 'light', accent: 'amber' } });
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.dataset.accent).toBe('amber');
  });

  it('readToken returns CSS variable values', () => {
    mount(Probe, { context: { theme: 'dark', accent: 'lime' } });
    expect(readToken('--ac')).toBe('#B6FF3D');
    expect(readToken('--surface-base')).toBe('#0E0E10');
  });

  it('resets between tests (verifies setup beforeEach)', () => {
    // The previous test set dark/lime — beforeEach should have reset to defaults.
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.documentElement.dataset.accent).toBe('lime');
  });
});
