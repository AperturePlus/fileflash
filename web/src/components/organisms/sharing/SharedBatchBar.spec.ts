import { beforeEach, describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import SharedBatchBar from './SharedBatchBar.vue';

describe('SharedBatchBar', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
  });

  it('hidden when count = 0', () => {
    const w = mount(SharedBatchBar, { props: { count: 0 } });
    expect(w.find('.shared-batch').exists()).toBe(false);
  });

  it('emits accept + clear', async () => {
    const w = mount(SharedBatchBar, { props: { count: 2 } });
    expect(w.text()).toContain('2');
    const buttons = w.findAll('button');
    await buttons.filter((b) => b.text().includes('Accept'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Clear'))[0].trigger('click');
    expect(w.emitted('accept')).toBeTruthy();
    expect(w.emitted('clear')).toBeTruthy();
  });
});
