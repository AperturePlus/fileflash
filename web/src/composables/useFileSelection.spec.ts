import { describe, it, expect } from 'vitest';
import { useFileSelection } from './useFileSelection';

const items = [
  { id: 'a' }, { id: 'b' }, { id: 'c' }, { id: 'd' }, { id: 'e' },
];

describe('useFileSelection', () => {
  it('toggleAdd adds and removes individual items, updates lastSelectedId', () => {
    const s = useFileSelection();
    s.toggleAdd('a');
    expect(s.selectedItems.value.has('a')).toBe(true);
    expect(s.lastSelectedId.value).toBe('a');

    s.toggleAdd('b');
    expect(s.selectedCount.value).toBe(2);
    expect(s.lastSelectedId.value).toBe('b');

    s.toggleAdd('a');
    expect(s.selectedItems.value.has('a')).toBe(false);
    expect(s.lastSelectedId.value).toBe('a');
  });

  it('selectRange selects everything between lastSelectedId and target inclusive', () => {
    const s = useFileSelection();
    s.toggleAdd('b');
    s.selectRange('d', items);
    expect(Array.from(s.selectedItems.value).sort()).toEqual(['b', 'c', 'd']);
    expect(s.lastSelectedId.value).toBe('d');
  });

  it('selectRange degrades to toggleAdd when no anchor', () => {
    const s = useFileSelection();
    s.selectRange('c', items);
    expect(s.selectedItems.value.has('c')).toBe(true);
    expect(s.selectedCount.value).toBe(1);
    expect(s.lastSelectedId.value).toBe('c');
  });

  it('selectRange supports reverse direction', () => {
    const s = useFileSelection();
    s.toggleAdd('d');
    s.selectRange('a', items);
    expect(Array.from(s.selectedItems.value).sort()).toEqual(['a', 'b', 'c', 'd']);
  });

  it('clear empties selection and anchor', () => {
    const s = useFileSelection();
    s.toggleAdd('a');
    s.toggleAdd('b');
    s.clear();
    expect(s.selectedCount.value).toBe(0);
    expect(s.lastSelectedId.value).toBe(null);
  });

  it('toggleSelection (legacy checkbox path) does not move anchor', () => {
    const s = useFileSelection();
    s.toggleAdd('a');
    s.toggleSelection('b');
    expect(s.selectedItems.value.has('b')).toBe(true);
    expect(s.lastSelectedId.value).toBe('a');
  });
});
