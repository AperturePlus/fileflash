import { describe, it, expect, afterEach } from 'vitest';
import { mount } from '../../test/mount';
import Modal from './Modal.vue';

const cleanup = () => {
  // Teleport leaves nodes in document.body; clear between tests.
  document.body.replaceChildren();
};

describe('molecules/Modal', () => {
  afterEach(cleanup);

  it('open=false does not mount the body content', () => {
    mount(Modal, {
      props: { open: false },
      slots: { default: () => 'Hello' },
      attachTo: document.body,
    });
    expect(document.querySelector('.ff-modal__body')).toBeNull();
  });

  it('open=true renders header / default / footer slots', () => {
    mount(Modal, {
      props: { open: true },
      slots: {
        header: () => 'Title',
        default: () => 'Body',
        footer: () => 'Foot',
      },
      attachTo: document.body,
    });
    expect(document.querySelector('.ff-modal__head')?.textContent).toContain('Title');
    expect(document.querySelector('.ff-modal__body')?.textContent).toContain('Body');
    expect(document.querySelector('.ff-modal__foot')?.textContent).toContain('Foot');
  });

  it('ESC keypress emits close', async () => {
    const w = mount(Modal, {
      props: { open: true },
      slots: { default: () => 'x' },
      attachTo: document.body,
    });
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    await w.vm.$nextTick();
    expect(w.emitted('close')).toHaveLength(1);
  });

  it('click on scrim emits close; click on panel does not', async () => {
    const w = mount(Modal, {
      props: { open: true },
      slots: { default: () => 'x' },
      attachTo: document.body,
    });
    const scrim = document.querySelector('.ff-modal__scrim') as HTMLElement;
    const panel = document.querySelector('.ff-modal__panel') as HTMLElement;
    expect(scrim).not.toBeNull();
    expect(panel).not.toBeNull();
    scrim.click();
    panel.click();
    await w.vm.$nextTick();
    expect(w.emitted('close')).toHaveLength(1);
  });
});
