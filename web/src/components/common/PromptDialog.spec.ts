import { afterEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../test/mount';
import PromptDialog from './PromptDialog.vue';
import { ui, uiState } from '../../utils/ui';

const flush = async () => {
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
};

describe('PromptDialog', () => {
  afterEach(() => {
    uiState.prompt = null;
  });

  it('shows one footer close button for copyText flow and keeps top-right close button', async () => {
    const wrapper = mount(PromptDialog);
    const pending = ui.copyText({
      title: 'Generated Password',
      message: 'Copy this password:',
      text: 'AUTO-112233',
    });
    await flush();

    expect(wrapper.find('.modal-close').exists()).toBe(true);
    const footerButtons = wrapper.findAll('.modal-footer .btn');
    expect(footerButtons).toHaveLength(1);
    expect(footerButtons[0]?.text()).toBe('Close');

    await wrapper.find('.modal-close').trigger('click');
    await pending;
    expect(uiState.prompt).toBeNull();
  });

  it('keeps cancel + confirm buttons for normal promptText flow', async () => {
    const wrapper = mount(PromptDialog);
    const pending = ui.promptText({ message: 'Type value' });
    await flush();

    const footerButtons = wrapper.findAll('.modal-footer .btn');
    expect(footerButtons).toHaveLength(2);
    expect(footerButtons[0]?.text()).toBe('Cancel');
    expect(footerButtons[1]?.text()).toBe('Confirm');

    await footerButtons[1]!.trigger('click');
    await expect(pending).resolves.toBe('');
  });
});
