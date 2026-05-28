import { beforeEach, describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import SharedLinksTable from './SharedLinksTable.vue';
import type { Share } from '../../../types/share';

const makeShare = (overrides: Partial<Share> = {}): Share => {
  const base: Share = {
    shareId: 's1',
    shareLink: 'abc123',
    itemType: 'file',
    itemInfo: { id: 'f1', name: 'report.pdf', size: 1024, mimeType: 'application/pdf' },
    settings: { passwordProtected: false, expireAt: null, allowDownload: true, allowPreview: true },
    createdAt: '2026-05-01T00:00:00Z',
    visitCount: 3,
    downloadCount: 1,
  };
  return {
    ...base,
    ...overrides,
    itemInfo: { ...base.itemInfo, ...(overrides.itemInfo || {}) },
    settings: { ...base.settings, ...(overrides.settings || {}) },
  };
};

const plainShare = makeShare();
const protectedShare = makeShare({
  shareId: 's2',
  shareLink: 'pw789',
  settings: { passwordProtected: true, expireAt: null, allowDownload: true, allowPreview: true },
});

describe('SharedLinksTable', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
  });

  it('renders rows', () => {
    const w = mount(SharedLinksTable, { props: { items: [plainShare, protectedShare] } });
    expect(w.text()).toContain('report.pdf');
    expect(w.text()).toContain('abc123');
    expect(w.text()).toContain('pw789');
    expect(w.text()).toContain('3 / 1');
  });

  it('emits copy + delete', async () => {
    const w = mount(SharedLinksTable, { props: { items: [protectedShare] } });
    const buttons = w.findAll('button');
    await buttons.filter((b) => b.text().includes('Copy'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Reset & Show Password'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Delete'))[0].trigger('click');
    expect(w.emitted('copy')).toBeTruthy();
    expect(w.emitted('regenerate-password')).toBeTruthy();
    expect(w.emitted('delete')).toBeTruthy();
  });

  it('shows regenerate button only for password protected links', () => {
    const w = mount(SharedLinksTable, { props: { items: [plainShare, protectedShare] } });
    const regenerateButtons = w.findAll('button').filter((button) => button.text().includes('Reset & Show Password'));
    expect(regenerateButtons).toHaveLength(1);
  });
});
