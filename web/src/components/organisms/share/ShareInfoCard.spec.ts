import { beforeEach, describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import ShareInfoCard from './ShareInfoCard.vue';
import type { Share } from '../../../types/share';

const share: Share = {
  shareId: 's1', shareLink: 'abc', itemType: 'file',
  itemInfo: { id: 'f', name: 'doc.pdf', size: 2048, mimeType: 'application/pdf' },
  settings: { passwordProtected: true, expireAt: '2026-12-01', allowDownload: true, allowPreview: true },
  createdAt: '2026-05-01T00:00:00Z',
};

describe('ShareInfoCard', () => {
  beforeEach(() => {
    localStorage.setItem('fileflash-locale', 'en-US');
  });

  it('renders all metadata rows', () => {
    const w = mount(ShareInfoCard, { props: { share } });
    expect(w.text()).toContain('File');
    expect(w.text()).toContain('doc.pdf');
    expect(w.text()).toContain('Required');
    expect(w.text()).toContain('2026-12-01');
  });

  it('shows Never when no expiry', () => {
    const noExpiry = { ...share, settings: { ...share.settings, expireAt: null, passwordProtected: false } };
    const w = mount(ShareInfoCard, { props: { share: noExpiry } });
    expect(w.text()).toContain('Never');
    expect(w.text()).toContain('Not required');
  });
});
