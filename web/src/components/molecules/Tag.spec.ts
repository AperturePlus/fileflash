import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Tag from './Tag.vue';

describe('molecules/Tag', () => {
  it('renders the slot text', () => {
    const w = mount(Tag, { slots: { default: 'design' } });
    expect(w.text()).toContain('design');
  });

  it('not removable by default — no button rendered', () => {
    const w = mount(Tag, { slots: { default: 'design' } });
    expect(w.find('button').exists()).toBe(false);
  });

  it('removable=true renders a Remove button', () => {
    const w = mount(Tag, { props: { removable: true }, slots: { default: 'x' } });
    expect(w.find('button[aria-label="Remove"]').exists()).toBe(true);
  });

  it('clicking the Remove button emits remove event', async () => {
    const w = mount(Tag, { props: { removable: true }, slots: { default: 'x' } });
    await w.find('button[aria-label="Remove"]').trigger('click');
    expect(w.emitted('remove')).toHaveLength(1);
  });
});
