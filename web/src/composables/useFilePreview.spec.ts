import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { nextTick } from 'vue';
import { useFilePreview } from './useFilePreview';
import type { FileItem } from '../types/file';

const sampleFile = (over: Partial<FileItem> = {}): FileItem => ({
  itemType: 'file',
  id: 'f1',
  name: 'a.txt',
  size: 100,
  mimeType: 'text/plain',
  ownerName: 'me',
  updatedAt: '2026-01-01T00:00:00Z',
  createdAt: '2026-01-01T00:00:00Z',
  folderId: 'root',
  ...over,
} as FileItem);

describe('useFilePreview', () => {
  beforeEach(() => {
    document.body.style.overflow = '';
    document.body.replaceChildren();
    const btn = document.createElement('button');
    btn.id = 'trigger';
    btn.textContent = 'trigger';
    document.body.appendChild(btn);
  });

  afterEach(() => {
    document.body.style.overflow = '';
  });

  it('openPreview sets previewFile and locks body scroll', async () => {
    const p = useFilePreview();
    p.openPreview(sampleFile());
    await nextTick();
    await nextTick();
    expect(p.previewFile.value?.id).toBe('f1');
    expect(document.body.style.overflow).toBe('hidden');
  });

  it('closePreview clears file and restores body scroll', async () => {
    const p = useFilePreview();
    p.openPreview(sampleFile());
    await nextTick();
    await nextTick();
    p.closePreview();
    expect(p.previewFile.value).toBe(null);
    expect(document.body.style.overflow).toBe('');
  });

  it('reopening the same file flushes via a null tick (forces watch re-run)', async () => {
    const p = useFilePreview();
    p.openPreview(sampleFile({ id: 'f1' }));
    await nextTick();
    await nextTick();

    const seen: Array<string | null> = [];
    p.openPreview(sampleFile({ id: 'f1' }));
    seen.push(p.previewFile.value?.id ?? null);
    await nextTick();
    seen.push(p.previewFile.value?.id ?? null);
    expect(seen[0]).toBe(null);
    expect(seen[1]).toBe('f1');
  });

  it('closePreview restores focus to the triggering element', async () => {
    const trigger = document.getElementById('trigger') as HTMLButtonElement;
    trigger.focus();
    const p = useFilePreview();
    p.openPreview(sampleFile());
    await nextTick();
    await nextTick();
    (document.body as HTMLElement).focus();
    p.closePreview();
    expect(document.activeElement?.id).toBe('trigger');
  });
});
