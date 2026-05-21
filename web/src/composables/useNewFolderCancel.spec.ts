import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ref } from 'vue';
import { useNewFolderCancel } from './useNewFolderCancel';

beforeEach(() => {
  document.body.replaceChildren();
});

function makeRow(tempId: string) {
  const row = document.createElement('div');
  row.setAttribute('data-temp-folder-row', tempId);
  const input = document.createElement('input');
  input.className = 'row__rename';
  row.appendChild(input);
  document.body.appendChild(row);
  return row;
}

function makeGridCard(tempId: string) {
  const card = document.createElement('div');
  card.className = 'card';
  card.setAttribute('data-temp-folder-row', tempId);
  const input = document.createElement('input');
  input.className = 'card__rename';
  card.appendChild(input);
  document.body.appendChild(card);
  return card;
}

function makeMarker(attr: 'data-ui-toast' | 'data-dropdown-menu') {
  const el = document.createElement('div');
  el.setAttribute(attr, '');
  document.body.appendChild(el);
  return el;
}

describe('useNewFolderCancel', () => {
  it('outside pointerdown with empty name calls onCancel', () => {
    const renameInputValue = ref('');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    makeRow('temp-1');

    c.install('temp-1');
    document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('outside pointerdown with non-empty name does NOT cancel', () => {
    const renameInputValue = ref('My Folder');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    makeRow('temp-1');

    c.install('temp-1');
    document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).not.toHaveBeenCalled();
  });

  it('pointerdown inside the temp row does NOT cancel', () => {
    const renameInputValue = ref('');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    const row = makeRow('temp-2');

    c.install('temp-2');
    const input = row.querySelector('input') as HTMLInputElement;
    input.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).not.toHaveBeenCalled();
  });

  it('pointerdown inside a temp grid card input does NOT cancel', () => {
    const renameInputValue = ref('');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    const card = makeGridCard('temp-2-grid');

    c.install('temp-2-grid');
    const input = card.querySelector('input') as HTMLInputElement;
    input.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).not.toHaveBeenCalled();
  });

  it('pointerdown on a toast does NOT cancel', () => {
    const renameInputValue = ref('');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    makeRow('temp-3');
    const toast = makeMarker('data-ui-toast');

    c.install('temp-3');
    toast.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).not.toHaveBeenCalled();
  });

  it('pointerdown on a dropdown does NOT cancel', () => {
    const renameInputValue = ref('');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    makeRow('temp-4');
    const dd = makeMarker('data-dropdown-menu');

    c.install('temp-4');
    dd.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).not.toHaveBeenCalled();
  });

  it('uninstall removes the listener', () => {
    const renameInputValue = ref('');
    const onCancel = vi.fn();
    const c = useNewFolderCancel({ renameInputValue, onCancel });
    makeRow('temp-5');

    c.install('temp-5');
    c.uninstall();
    document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));

    expect(onCancel).not.toHaveBeenCalled();
  });
});
