import { beforeEach, describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import SharedLinksTable from './SharedLinksTable.vue';
import type { Share } from '../../../types/share';

const items: Share[] = [
  {
    shareId: 's1', shareLink: 'abc123', itemType: 'file',
    itemInfo: { id: 'f1', name: 'report.pdf', size: 1024, mimeType: 'application/pdf' },
    settings: { passwordProtected: false, expireAt: null, allowDownload: true, allowPreview: true },
    createdAt: '2026-05-01T00:00:00Z', visitCount: 3, downloadCount: 1,
  },
];

describe('SharedLinksTable', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
  });

  it('renders rows', () => {
    const w = mount(SharedLinksTable, { props: { items } });
    expect(w.text()).toContain('report.pdf');
    expect(w.text()).toContain('abc123');
    expect(w.text()).toContain('3 / 1');
  });

  it('emits copy + delete', async () => {
    const w = mount(SharedLinksTable, { props: { items } });
    const buttons = w.findAll('button');
    await buttons.filter((b) => b.text().includes('Copy'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Delete'))[0].trigger('click');
    expect(w.emitted('copy')).toBeTruthy();
    expect(w.emitted('delete')).toBeTruthy();
  });
});
