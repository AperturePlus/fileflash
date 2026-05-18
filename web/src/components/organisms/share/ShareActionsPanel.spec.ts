import { beforeEach, describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import ShareActionsPanel from './ShareActionsPanel.vue';

const baseProps = {
  isFile: true, isFolder: false,
  canPreview: true, canDownload: true,
  isPreviewing: false, isDownloading: false, isSaving: false,
};

describe('ShareActionsPanel', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
  });

  it('renders preview + download for file mode', () => {
    const w = mount(ShareActionsPanel, { props: baseProps });
    expect(w.text()).toContain('Preview');
    expect(w.text()).toContain('Download');
    expect(w.text()).toContain('Save to My Space');
  });

  it('hides preview + download for folder mode', () => {
    const w = mount(ShareActionsPanel, { props: { ...baseProps, isFile: false, isFolder: true } });
    expect(w.text()).not.toContain('Preview');
    expect(w.text()).not.toContain('Download');
    expect(w.text()).toContain('Save Folder');
  });

  it('emits preview/download/save', async () => {
    const w = mount(ShareActionsPanel, { props: baseProps });
    const buttons = w.findAll('button');
    await buttons.filter((b) => b.text().includes('Preview'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Download'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Save'))[0].trigger('click');
    expect(w.emitted('preview')).toBeTruthy();
    expect(w.emitted('download')).toBeTruthy();
    expect(w.emitted('save')).toBeTruthy();
  });
});
