import { beforeEach, describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import ShareAccessPanel from './ShareAccessPanel.vue';

describe('ShareAccessPanel', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
  });

  it('shows password form when protected', () => {
    const w = mount(ShareAccessPanel, {
      props: { passwordProtected: true, password: '', isAccessing: false },
    });
    expect(w.find('input[type="password"]').exists()).toBe(true);
    expect(w.text()).toContain('Unlock');
  });

  it('shows open-access form when not protected', () => {
    const w = mount(ShareAccessPanel, {
      props: { passwordProtected: false, password: '', isAccessing: false },
    });
    expect(w.find('input[type="password"]').exists()).toBe(false);
    expect(w.text()).toContain('Get Access');
  });

  it('emits request-access on button click', async () => {
    const w = mount(ShareAccessPanel, {
      props: { passwordProtected: false, password: '', isAccessing: false },
    });
    await w.find('button').trigger('click');
    expect(w.emitted('request-access')).toBeTruthy();
  });
});
