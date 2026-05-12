import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import TrashTable from './TrashTable.vue';
import type { RecycleBinItem } from '../../../types/file';

const items: RecycleBinItem[] = [
  { itemType: 'file', id: 'a', name: 'a.txt', originalPath: '/foo/bar', size: 100, deletedAt: '2026-05-01T00:00:00Z', autoDeleteAt: '2026-06-01T00:00:00Z', daysUntilPermanentDelete: 14, canRestore: true, restoreConflicts: false },
  { itemType: 'file', id: 'b', name: 'b.txt', originalPath: '/foo', size: 200, deletedAt: '2026-05-05T00:00:00Z', autoDeleteAt: '2026-05-15T00:00:00Z', daysUntilPermanentDelete: 3, canRestore: true, restoreConflicts: false },
];

describe('TrashTable', () => {
  it('renders rows', () => {
    const w = mount(TrashTable, { props: { items } });
    expect(w.text()).toContain('a.txt');
    expect(w.text()).toContain('/foo/bar');
    expect(w.text()).toContain('14 days');
  });

  it('flags near-expiry items', () => {
    const w = mount(TrashTable, { props: { items } });
    expect(w.findAll('.trash-table__cell--warning').length).toBeGreaterThan(0);
  });

  it('emits restore + permanent-delete', async () => {
    const w = mount(TrashTable, { props: { items } });
    const buttons = w.findAll('button');
    await buttons.filter((b) => b.text().includes('Restore'))[0].trigger('click');
    await buttons.filter((b) => b.text().includes('Delete'))[0].trigger('click');
    expect(w.emitted('restore')).toBeTruthy();
    expect(w.emitted('permanent-delete')).toBeTruthy();
  });
});
