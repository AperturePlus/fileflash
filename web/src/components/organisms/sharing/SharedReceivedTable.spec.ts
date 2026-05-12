import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import SharedReceivedTable from './SharedReceivedTable.vue';
import type { SharedItem } from '../../../types/share';

const items: SharedItem[] = [
  { itemType: 'file', id: 'a', name: 'a.txt', size: 100, sharedBy: 'alice', permission: 'read', sharedAt: '2026-05-01T00:00:00Z' },
  { itemType: 'folder', id: 'b', name: 'docs', size: 0, sharedBy: 'bob', permission: 'write', sharedAt: '2026-05-02T00:00:00Z' },
];

describe('SharedReceivedTable', () => {
  it('renders header + rows', () => {
    const w = mount(SharedReceivedTable, { props: { items, selection: new Set() } });
    expect(w.findAll('.shared-table__row')).toHaveLength(2);
    expect(w.text()).toContain('a.txt');
    expect(w.text()).toContain('alice');
  });

  it('emits accept when accept button clicked', async () => {
    const w = mount(SharedReceivedTable, { props: { items, selection: new Set() } });
    await w.findAll('button').filter((b) => b.text().includes('Accept'))[0].trigger('click');
    expect(w.emitted('accept')).toBeTruthy();
  });
});
