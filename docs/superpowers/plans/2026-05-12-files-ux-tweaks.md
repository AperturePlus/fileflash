# Files UX Tweaks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land four UX changes on the My Files page — accumulative single-click selection + double-click activates, iconified view switcher, centered-modal preview, resizable columns, and ESC/outside-click cancel on new-folder creation.

**Architecture:** Each UX concern gets a focused composable; UI behavior changes ride on small extensions to the existing organisms (`FileRow`, `FileTable`, `FileToolbar`). Preview moves out of `RightSidebar` into a new `FilePreviewDialog` organism that owns ESC / overlay / body-scroll lock. `selectedFile` and `previewFile` get separated in the file store so the right sidebar is freed for future use.

**Tech Stack:** Vue 3 + TypeScript (strict `vue-tsc`), Pinia, Vitest + happy-dom (project uses `web/src/test/mount.ts` helper), CSS variables for column widths, Industrial Dashboard tokens (`--ac`, `--surface-*`, etc.).

**Spec:** `docs/superpowers/specs/2026-05-11-files-ux-tweaks-design.md`

---

## File Structure

### New files

- `web/src/composables/useFilePreview.ts` — `previewFile` ref + `openPreview` / `closePreview`, captures `document.activeElement` for focus restoration, locks body scroll.
- `web/src/composables/useColumnResize.ts` — `colWidths` reactive object + `onResizeStart(col, ev)` pointer handler; min/max clamping; cleanup on visibilitychange / window blur.
- `web/src/composables/useNewFolderCancel.ts` — `install(tempId)` / `uninstall()` capture-phase outside-click listener; emits toast on empty-name cancel.
- `web/src/composables/useFilePreview.spec.ts`
- `web/src/composables/useColumnResize.spec.ts`
- `web/src/composables/useNewFolderCancel.spec.ts`
- `web/src/composables/useFileSelection.spec.ts`
- `web/src/components/organisms/files/FilePreviewDialog.vue` — modal organism that hosts `FileDetailPanel`. Teleports to body.
- `web/src/components/organisms/files/FilePreviewDialog.spec.ts`
- `web/src/components/organisms/files/FileRow.spec.ts`
- `web/src/components/organisms/files/FileTable.spec.ts`
- `web/src/components/molecules/SegmentedControl.spec.ts`

### Modified files

- `web/src/components/atoms/icons.ts` — add `list` and `grid` paths.
- `web/src/components/atoms/Icon.spec.ts` — assert new icons render.
- `web/src/components/molecules/SegmentedControl.vue` — `SegmentedOption` accepts optional `icon` + `ariaLabel`; template renders `<Icon>` when set.
- `web/src/components/common/ToastStack.vue` — add `data-ui-toast` on the stack container.
- `web/src/components/common/DropdownMenu.vue` — add `data-dropdown-menu` on the menu div.
- `web/src/composables/useFileSelection.ts` — add `toggleAdd`, `selectRange`, `clear`, `lastSelectedId`.
- `web/src/composables/useFileActions.ts` — wire `useNewFolderCancel` install / uninstall.
- `web/src/store/file.ts` — add `previewFile` ref + clear in `fetchFolderContents`.
- `web/src/components/organisms/files/FileRow.vue` — single-click emits `select { item, modifiers }` + dblclick emits `activate` + `data-temp-folder-row` attribute.
- `web/src/components/organisms/files/FileTable.vue` — resize handles in header, CSS variable column widths, blank-click `clear-selection`, grid dblclick.
- `web/src/components/organisms/files/FileToolbar.vue` — icon-only segmented options.
- `web/src/components/organisms/files/FileToolbar.spec.ts` — query by aria-label.
- `web/src/components/organisms/shell/RightSidebar.vue` — drop FileDetailPanel, render placeholder.
- `web/src/components/organisms/shell/RightSidebar.spec.ts` — rewrite for placeholder behavior (the existing PDF / video tests move to `FilePreviewDialog.spec.ts`).
- `web/src/components/templates/MainLayout.vue` — `rightVisible` defaults to `false`; render `<FilePreviewDialog />` at root.
- `web/src/pages/files/MyFiles.vue` — use new composables; split `onItemClick` into select/activate.
- `web/src/i18n/messages.ts` — add `files.toolbar.aria.list`, `files.toolbar.aria.grid`, `files.toast.newFolderCanceled`, `files.preview.close`, `files.preview.title`.
- `web/src/pages/__dev/Library.vue` — extend Organisms · Files section with dblclick + modal + resize demos.

### Removed files

- None.

---

## Task 1: Add `list` and `grid` icons

**Files:**
- Modify: `web/src/components/atoms/icons.ts`
- Modify: `web/src/components/atoms/Icon.spec.ts`

- [ ] **Step 1: Write the failing tests**

Append to `web/src/components/atoms/Icon.spec.ts`:

```ts
it('renders the list icon (three rows with leading dots)', () => {
  const w = mount(Icon, { props: { name: 'list' } });
  const d = w.find('svg path').attributes('d') ?? '';
  expect(d).toContain('M3 6h.01');
  expect(d).toContain('M8 6h13');
});

it('renders the grid icon (four 7x7 squares)', () => {
  const w = mount(Icon, { props: { name: 'grid' } });
  const d = w.find('svg path').attributes('d') ?? '';
  expect(d).toContain('M4 4h7v7H4z');
  expect(d).toContain('M13 13h7v7h-7z');
});
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd web && bun run test -- atoms/Icon.spec
```

Expected: 2 new failures — TypeScript will narrow `name` to existing union; the assertions also fail.

- [ ] **Step 3: Implement**

Edit `web/src/components/atoms/icons.ts`, add inside the `ICONS` object (after `folderPlus`):

```ts
  list: 'M3 6h.01M3 12h.01M3 18h.01M8 6h13M8 12h13M8 18h13',
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd web && bun run test -- atoms/Icon.spec
```

Expected: all Icon tests pass (existing + 2 new).

- [ ] **Step 5: Commit**

```
git add web/src/components/atoms/icons.ts web/src/components/atoms/Icon.spec.ts
git commit -m "feat(atoms): add list and grid icons"
```

---

## Task 2: Tag toast stack and dropdown menu with data attrs

**Files:**
- Modify: `web/src/components/common/ToastStack.vue`
- Modify: `web/src/components/common/DropdownMenu.vue`

These are markers used by `useNewFolderCancel` to skip the outside-click handler when the click lands inside a toast or a dropdown opened from the temp folder row.

- [ ] **Step 1: Edit `ToastStack.vue`**

Add `data-ui-toast` to the outer `.toast-stack` div:

```vue
<div class="toast-stack" data-ui-toast aria-live="polite" aria-atomic="true">
```

- [ ] **Step 2: Edit `DropdownMenu.vue`**

Add `data-dropdown-menu` to the menu element:

```vue
<div v-if="isVisible" ref="menu" data-dropdown-menu class="dropdown-menu" :style="menuStyle">
```

- [ ] **Step 3: Sanity check**

```
cd web && bun run test
```

Expected: nothing regresses.

- [ ] **Step 4: Commit**

```
git add web/src/components/common/ToastStack.vue web/src/components/common/DropdownMenu.vue
git commit -m "chore(common): tag toast and dropdown with data attrs for click-guard"
```

---

## Task 3: Add i18n keys

**Files:**
- Modify: `web/src/i18n/messages.ts`

- [ ] **Step 1: Extend the `LocaleKey` union**

Find the `files.toolbar.upload` line in the union and add right after it:

```ts
  | 'files.toolbar.aria.list'
  | 'files.toolbar.aria.grid'
  | 'files.toast.newFolderCanceled'
  | 'files.preview.close'
  | 'files.preview.title'
```

- [ ] **Step 2: Add zh-CN strings**

Find the `'files.toolbar.upload': '上传',` line in the zh-CN block and add after it:

```ts
    'files.toolbar.aria.list': '列表视图',
    'files.toolbar.aria.grid': '网格视图',
    'files.toast.newFolderCanceled': '已取消新建文件夹',
    'files.preview.close': '关闭预览',
    'files.preview.title': '文件预览',
```

- [ ] **Step 3: Add en-US strings**

Find the `'files.toolbar.upload': 'Upload',` line in the en-US block and add after it:

```ts
    'files.toolbar.aria.list': 'List view',
    'files.toolbar.aria.grid': 'Grid view',
    'files.toast.newFolderCanceled': 'New folder canceled.',
    'files.preview.close': 'Close preview',
    'files.preview.title': 'File preview',
```

- [ ] **Step 4: Run type check**

```
cd web && bun run check
```

Expected: zero errors. (No callers yet; we add them in later tasks.)

- [ ] **Step 5: Commit**

```
git add web/src/i18n/messages.ts
git commit -m "feat(i18n): add files preview, toast, and view-aria keys"
```

---

## Task 4: Extend `useFileSelection` with anchored multi-select

**Files:**
- Modify: `web/src/composables/useFileSelection.ts`
- Create: `web/src/composables/useFileSelection.spec.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/composables/useFileSelection.spec.ts`:

```ts
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
    expect(s.lastSelectedId.value).toBe('a'); // anchor still moves on the click
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
    s.toggleAdd('a'); // anchor = 'a'
    s.toggleSelection('b');
    expect(s.selectedItems.value.has('b')).toBe(true);
    expect(s.lastSelectedId.value).toBe('a');
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

```
cd web && bun run test -- composables/useFileSelection.spec
```

Expected: failure — methods don't exist yet.

- [ ] **Step 3: Implement the extension**

Replace the contents of `web/src/composables/useFileSelection.ts`:

```ts
import { ref, computed } from 'vue';

export function useFileSelection() {
  const selectedItems = ref<Set<string>>(new Set());
  const lastSelectedId = ref<string | null>(null);

  const selectedCount = computed(() => selectedItems.value.size);

  const isSelected = (itemId: string | number) =>
    selectedItems.value.has(String(itemId));

  // Legacy checkbox path — does NOT update lastSelectedId so the Shift anchor stays stable.
  const toggleSelection = (itemId: string | number) => {
    if (!itemId && itemId !== 0) return;
    const id = String(itemId);
    const next = new Set(selectedItems.value);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedItems.value = next;
  };

  // Accumulative click toggle — moves the anchor on every click.
  const toggleAdd = (itemId: string | number) => {
    const id = String(itemId);
    const next = new Set(selectedItems.value);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedItems.value = next;
    lastSelectedId.value = id;
  };

  // Shift-click range selection (inclusive). Degrades to toggleAdd when no anchor.
  const selectRange = (toId: string, items: ReadonlyArray<{ id: string }>) => {
    if (!lastSelectedId.value) {
      toggleAdd(toId);
      return;
    }
    const fromIdx = items.findIndex((it) => it.id === lastSelectedId.value);
    const toIdx = items.findIndex((it) => it.id === toId);
    if (fromIdx === -1 || toIdx === -1) {
      toggleAdd(toId);
      return;
    }
    const [lo, hi] = fromIdx < toIdx ? [fromIdx, toIdx] : [toIdx, fromIdx];
    const next = new Set(selectedItems.value);
    for (let i = lo; i <= hi; i += 1) next.add(items[i].id);
    selectedItems.value = next;
    lastSelectedId.value = toId;
  };

  const clear = () => {
    selectedItems.value = new Set();
    lastSelectedId.value = null;
  };

  // Kept for compatibility with any caller using the old name.
  const clearSelection = clear;

  return {
    selectedItems,
    lastSelectedId,
    isSelected,
    toggleSelection,
    toggleAdd,
    selectRange,
    selectedCount,
    clear,
    clearSelection,
  };
}
```

- [ ] **Step 4: Run tests to verify pass**

```
cd web && bun run test -- composables/useFileSelection.spec
```

Expected: all 6 pass.

- [ ] **Step 5: Run wider test sweep**

```
cd web && bun run test
```

Expected: nothing else regresses (no caller used the rewritten methods yet).

- [ ] **Step 6: Commit**

```
git add web/src/composables/useFileSelection.ts web/src/composables/useFileSelection.spec.ts
git commit -m "feat(composables): add anchored multi-select + range to useFileSelection"
```

---

## Task 5: Create `useFilePreview`

**Files:**
- Create: `web/src/composables/useFilePreview.ts`
- Create: `web/src/composables/useFilePreview.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `web/src/composables/useFilePreview.spec.ts`:

```ts
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
    (document.body as HTMLElement).focus(); // simulate dialog stealing focus
    p.closePreview();
    expect(document.activeElement?.id).toBe('trigger');
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

```
cd web && bun run test -- composables/useFilePreview.spec
```

Expected: import error (file missing).

- [ ] **Step 3: Implement**

Create `web/src/composables/useFilePreview.ts`:

```ts
import { nextTick, onUnmounted, ref } from 'vue';
import type { FileItem } from '../types/file';

export function useFilePreview() {
  const previewFile = ref<FileItem | null>(null);
  let lastTrigger: HTMLElement | null = null;

  const lockBodyScroll = () => {
    document.body.style.overflow = 'hidden';
  };
  const unlockBodyScroll = () => {
    document.body.style.overflow = '';
  };

  const openPreview = async (file: FileItem) => {
    const active = document.activeElement;
    lastTrigger = active instanceof HTMLElement ? active : null;
    previewFile.value = null;
    await nextTick();
    previewFile.value = file;
    lockBodyScroll();
  };

  const closePreview = () => {
    previewFile.value = null;
    unlockBodyScroll();
    const trigger = lastTrigger;
    lastTrigger = null;
    if (trigger && typeof trigger.focus === 'function') {
      trigger.focus();
    }
  };

  onUnmounted(() => {
    unlockBodyScroll();
    lastTrigger = null;
  });

  return { previewFile, openPreview, closePreview };
}
```

- [ ] **Step 4: Run tests to verify pass**

```
cd web && bun run test -- composables/useFilePreview.spec
```

Expected: 4 pass.

- [ ] **Step 5: Commit**

```
git add web/src/composables/useFilePreview.ts web/src/composables/useFilePreview.spec.ts
git commit -m "feat(composables): add useFilePreview for modal-driven file preview"
```

---

## Task 6: Create `useColumnResize`

**Files:**
- Create: `web/src/composables/useColumnResize.ts`
- Create: `web/src/composables/useColumnResize.spec.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/composables/useColumnResize.spec.ts`:

```ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useColumnResize } from './useColumnResize';

function makePointerEvent(type: string, clientX: number): PointerEvent {
  return new PointerEvent(type, { clientX, bubbles: true });
}

describe('useColumnResize', () => {
  beforeEach(() => {
    document.body.style.cursor = '';
  });

  afterEach(() => {
    document.body.style.cursor = '';
  });

  it('starts from default px widths', () => {
    const c = useColumnResize();
    expect(c.colWidths.name).toBeGreaterThan(0);
    expect(c.colWidths.size).toBeGreaterThan(0);
    expect(c.colWidths.time).toBeGreaterThan(0);
  });

  it('drag updates the target column within clamp', () => {
    const c = useColumnResize();
    const startW = c.colWidths.name;
    c.onResizeStart('name', makePointerEvent('pointerdown', 100));
    document.dispatchEvent(makePointerEvent('pointermove', 200));
    expect(c.colWidths.name).toBe(Math.min(800, Math.max(120, startW + 100)));
    document.dispatchEvent(makePointerEvent('pointerup', 200));
  });

  it('clamps below MIN', () => {
    const c = useColumnResize();
    c.colWidths.size = 100; // start near min
    c.onResizeStart('size', makePointerEvent('pointerdown', 0));
    document.dispatchEvent(makePointerEvent('pointermove', -500));
    expect(c.colWidths.size).toBe(60);
    document.dispatchEvent(makePointerEvent('pointerup', -500));
  });

  it('clamps above MAX', () => {
    const c = useColumnResize();
    c.colWidths.size = 100;
    c.onResizeStart('size', makePointerEvent('pointerdown', 0));
    document.dispatchEvent(makePointerEvent('pointermove', 2000));
    expect(c.colWidths.size).toBe(200);
    document.dispatchEvent(makePointerEvent('pointerup', 2000));
  });

  it('cleanup on pointerup restores cursor', () => {
    const c = useColumnResize();
    c.onResizeStart('name', makePointerEvent('pointerdown', 0));
    expect(document.body.style.cursor).toBe('col-resize');
    document.dispatchEvent(makePointerEvent('pointerup', 0));
    expect(document.body.style.cursor).toBe('');
  });

  it('cleanup on visibilitychange stops dragging', () => {
    const c = useColumnResize();
    c.onResizeStart('name', makePointerEvent('pointerdown', 0));
    document.dispatchEvent(new Event('visibilitychange'));
    expect(document.body.style.cursor).toBe('');
    // After cleanup, further pointermoves should not change the value.
    const w = c.colWidths.name;
    document.dispatchEvent(makePointerEvent('pointermove', 500));
    expect(c.colWidths.name).toBe(w);
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

```
cd web && bun run test -- composables/useColumnResize.spec
```

Expected: import error.

- [ ] **Step 3: Implement**

Create `web/src/composables/useColumnResize.ts`:

```ts
import { reactive, onUnmounted } from 'vue';

type ColKey = 'name' | 'size' | 'time';

const DEFAULT_WIDTHS: Record<ColKey, number> = {
  name: 360,
  size: 120,
  time: 200,
};
const MIN: Record<ColKey, number> = { name: 120, size: 60, time: 120 };
const MAX: Record<ColKey, number> = { name: 800, size: 200, time: 280 };

const clamp = (v: number, lo: number, hi: number) =>
  Math.min(hi, Math.max(lo, v));

export function useColumnResize() {
  const colWidths = reactive({ ...DEFAULT_WIDTHS });

  let activeCol: ColKey | null = null;
  let startX = 0;
  let startW = 0;

  const onMove = (ev: PointerEvent) => {
    if (!activeCol) return;
    const delta = ev.clientX - startX;
    colWidths[activeCol] = clamp(startW + delta, MIN[activeCol], MAX[activeCol]);
  };

  const cleanup = () => {
    activeCol = null;
    document.removeEventListener('pointermove', onMove);
    document.removeEventListener('pointerup', onUp);
    document.removeEventListener('visibilitychange', cleanup);
    window.removeEventListener('blur', cleanup);
    document.body.style.cursor = '';
  };

  const onUp = () => cleanup();

  const onResizeStart = (col: ColKey, ev: PointerEvent) => {
    ev.preventDefault();
    activeCol = col;
    startX = ev.clientX;
    startW = colWidths[col];
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp, { once: true });
    document.addEventListener('visibilitychange', cleanup);
    window.addEventListener('blur', cleanup);
    document.body.style.cursor = 'col-resize';
  };

  onUnmounted(() => cleanup());

  return { colWidths, onResizeStart };
}
```

- [ ] **Step 4: Run tests to verify pass**

```
cd web && bun run test -- composables/useColumnResize.spec
```

Expected: 6 pass.

- [ ] **Step 5: Commit**

```
git add web/src/composables/useColumnResize.ts web/src/composables/useColumnResize.spec.ts
git commit -m "feat(composables): add useColumnResize for FileTable column drag"
```

---

## Task 7: Create `useNewFolderCancel`

**Files:**
- Create: `web/src/composables/useNewFolderCancel.ts`
- Create: `web/src/composables/useNewFolderCancel.spec.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/composables/useNewFolderCancel.spec.ts`:

```ts
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
```

- [ ] **Step 2: Run tests to verify failure**

```
cd web && bun run test -- composables/useNewFolderCancel.spec
```

Expected: import error.

- [ ] **Step 3: Implement**

Create `web/src/composables/useNewFolderCancel.ts`:

```ts
import type { Ref } from 'vue';

export interface UseNewFolderCancelOptions {
  renameInputValue: Ref<string>;
  onCancel: () => void;
}

export function useNewFolderCancel(options: UseNewFolderCancelOptions) {
  let listener: ((ev: PointerEvent) => void) | null = null;

  const install = (tempId: string) => {
    uninstall();
    const onPointerDown = (ev: PointerEvent) => {
      const target = ev.target as Element | null;
      if (!target) return;
      const guard = `[data-temp-folder-row="${tempId}"], [data-ui-toast], [data-dropdown-menu]`;
      if (target.closest(guard)) return;
      if (options.renameInputValue.value.trim() !== '') return;
      uninstall();
      options.onCancel();
    };
    listener = onPointerDown;
    document.addEventListener('pointerdown', onPointerDown, { capture: true });
  };

  const uninstall = () => {
    if (!listener) return;
    document.removeEventListener('pointerdown', listener, { capture: true });
    listener = null;
  };

  return { install, uninstall };
}
```

- [ ] **Step 4: Run tests to verify pass**

```
cd web && bun run test -- composables/useNewFolderCancel.spec
```

Expected: 6 pass.

- [ ] **Step 5: Commit**

```
git add web/src/composables/useNewFolderCancel.ts web/src/composables/useNewFolderCancel.spec.ts
git commit -m "feat(composables): add useNewFolderCancel outside-click guard"
```

---

## Task 8: Extend `SegmentedControl` with icon support

**Files:**
- Modify: `web/src/components/molecules/SegmentedControl.vue`
- Create: `web/src/components/molecules/SegmentedControl.spec.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/components/molecules/SegmentedControl.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import SegmentedControl from './SegmentedControl.vue';

const optsText = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' },
];

const optsIcon = [
  { value: 'list', label: '', icon: 'list' as const, ariaLabel: 'List view' },
  { value: 'grid', label: '', icon: 'grid' as const, ariaLabel: 'Grid view' },
];

describe('SegmentedControl', () => {
  it('renders label text when no icon set', () => {
    const w = mount(SegmentedControl, {
      props: { modelValue: 'a', options: optsText },
    });
    expect(w.findAll('.ff-segmented-option')[0].text()).toBe('A');
  });

  it('renders Icon when option has icon', () => {
    const w = mount(SegmentedControl, {
      props: { modelValue: 'list', options: optsIcon },
    });
    const btns = w.findAll('.ff-segmented-option');
    expect(btns[0].find('svg').exists()).toBe(true);
    expect(btns[1].find('svg').exists()).toBe(true);
  });

  it('exposes ariaLabel as aria-label attribute', () => {
    const w = mount(SegmentedControl, {
      props: { modelValue: 'list', options: optsIcon },
    });
    const btns = w.findAll('.ff-segmented-option');
    expect(btns[0].attributes('aria-label')).toBe('List view');
    expect(btns[1].attributes('aria-label')).toBe('Grid view');
  });

  it('emits update:modelValue on click', async () => {
    const w = mount(SegmentedControl, {
      props: { modelValue: 'list', options: optsIcon },
    });
    await w.findAll('.ff-segmented-option')[1].trigger('click');
    expect(w.emitted('update:modelValue')?.[0]?.[0]).toBe('grid');
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

```
cd web && bun run test -- molecules/SegmentedControl.spec
```

Expected: failure — `icon` prop not in `SegmentedOption`, no aria-label rendered.

- [ ] **Step 3: Implement**

Replace `web/src/components/molecules/SegmentedControl.vue`:

```vue
<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import type { IconName } from '../atoms/icons';

export interface SegmentedOption {
  value: string | number;
  label: string;
  icon?: IconName;
  ariaLabel?: string;
}

defineProps<{
  modelValue: string | number;
  options: SegmentedOption[];
  disabled?: boolean;
}>();

defineEmits<{ 'update:modelValue': [value: string | number] }>();
</script>

<template>
  <div class="ff-segmented" role="group">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="ff-segmented-option"
      :class="{ 'ff-segmented-option--active': opt.value === modelValue, 'ff-segmented-option--icon': !!opt.icon }"
      :aria-pressed="opt.value === modelValue ? 'true' : 'false'"
      :aria-label="opt.ariaLabel"
      :disabled="disabled"
      @click="$emit('update:modelValue', opt.value)"
    >
      <Icon v-if="opt.icon" :name="opt.icon" :size="16" />
      <span v-if="opt.label">{{ opt.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.ff-segmented {
  display: inline-flex;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}
.ff-segmented-option {
  padding: 4px 12px;
  background: transparent; border: 0;
  color: var(--text-secondary);
  font-family: var(--font-mono); font-size: var(--text-label); letter-spacing: var(--tracking-wide);
  text-transform: uppercase; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px;
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-segmented-option--icon { padding: 4px 8px; }
.ff-segmented-option:hover:not(:disabled) { color: var(--text-primary); }
.ff-segmented-option--active { background: var(--ac); color: var(--ac-fg); }
.ff-segmented-option:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
```

- [ ] **Step 4: Run tests to verify pass**

```
cd web && bun run test -- molecules/SegmentedControl
```

Expected: 4 pass; existing usages (settings, library page) still render label text and behave correctly — no regressions.

- [ ] **Step 5: Run all tests**

```
cd web && bun run test
```

Expected: green.

- [ ] **Step 6: Commit**

```
git add web/src/components/molecules/SegmentedControl.vue web/src/components/molecules/SegmentedControl.spec.ts
git commit -m "feat(molecules): SegmentedControl supports icon + ariaLabel"
```

---

## Task 9: `FileToolbar` switches to icon-only view options

**Files:**
- Modify: `web/src/components/organisms/files/FileToolbar.vue`
- Modify: `web/src/components/organisms/files/FileToolbar.spec.ts`

- [ ] **Step 1: Update the spec first (failing direction)**

Replace `web/src/components/organisms/files/FileToolbar.spec.ts` first test (`emits update:viewMode when switcher toggled`) with:

```ts
  it('emits update:viewMode when icon segmented toggled', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    const buttons = wrapper.findAll('.ff-segmented-option');
    expect(buttons).toHaveLength(2);
    expect(buttons[0].attributes('aria-label')).toBeTruthy();
    expect(buttons[0].find('svg').exists()).toBe(true);
    await buttons[1].trigger('click');
    expect(wrapper.emitted('update:viewMode')?.[0]?.[0]).toBe('grid');
  });
```

- [ ] **Step 2: Run tests to confirm failure**

```
cd web && bun run test -- organisms/files/FileToolbar.spec
```

Expected: failing — the toolbar still emits text labels with no svg.

- [ ] **Step 3: Edit `FileToolbar.vue`**

Replace the `viewOptions` computed block:

```ts
const viewOptions = computed<SegmentedOption[]>(() => [
  { value: 'list', label: '', icon: 'list', ariaLabel: t('files.toolbar.aria.list') },
  { value: 'grid', label: '', icon: 'grid', ariaLabel: t('files.toolbar.aria.grid') },
]);
```

(No template change needed — the SegmentedControl now renders icons.)

- [ ] **Step 4: Run the spec**

```
cd web && bun run test -- organisms/files/FileToolbar.spec
```

Expected: 4 pass.

- [ ] **Step 5: Commit**

```
git add web/src/components/organisms/files/FileToolbar.vue web/src/components/organisms/files/FileToolbar.spec.ts
git commit -m "feat(organisms): FileToolbar uses icon-only view switcher"
```

---

## Task 10: Add `previewFile` to file store

**Files:**
- Modify: `web/src/store/file.ts`

- [ ] **Step 1: Edit `store/file.ts`**

Add ref + clear logic. Inside `defineStore('file', () => {...})`:

```ts
  const previewFile = ref<ContentItem | null>(null);
```

(Place it next to `const selectedFile = ref<ContentItem | null>(null);`.)

In `fetchFolderContents` near the existing `selectedFile.value = null;`, add right after it:

```ts
    previewFile.value = null;
```

In the `return { ... }` block, add `previewFile` to the exposed members.

- [ ] **Step 2: Run type check**

```
cd web && bun run check
```

Expected: 0 errors.

- [ ] **Step 3: Run tests**

```
cd web && bun run test
```

Expected: green.

- [ ] **Step 4: Commit**

```
git add web/src/store/file.ts
git commit -m "feat(store): track previewFile separately from selectedFile"
```

---

## Task 11: Create `FilePreviewDialog`

**Files:**
- Create: `web/src/components/organisms/files/FilePreviewDialog.vue`
- Create: `web/src/components/organisms/files/FilePreviewDialog.spec.ts`
- Modify: `web/src/components/organisms/files/index.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/components/organisms/files/FilePreviewDialog.spec.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '../../../test/mount';
import { nextTick } from 'vue';
import FilePreviewDialog from './FilePreviewDialog.vue';

vi.mock('../../../api/file', () => ({
  previewFile: vi.fn(() => Promise.resolve(new Blob(['ok'], { type: 'text/plain' }))),
  downloadFile: vi.fn(),
}));

vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({ default: '/mock.js' }));
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: vi.fn(),
}));

const sampleFile = {
  itemType: 'file',
  id: 'f1',
  name: 'a.txt',
  size: 4,
  mimeType: 'text/plain',
  ownerName: 'me',
  updatedAt: '2026-01-01T00:00:00Z',
  createdAt: '2026-01-01T00:00:00Z',
  folderId: 'root',
};

describe('FilePreviewDialog', () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it('renders nothing when file is null', () => {
    const w = mount(FilePreviewDialog, { props: { file: null }, attachTo: document.body });
    expect(document.body.querySelector('.file-preview-dialog')).toBeNull();
    w.unmount();
  });

  it('renders overlay and FileDetailPanel when file is present', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile }, attachTo: document.body });
    await nextTick();
    const overlay = document.body.querySelector('.file-preview-dialog__overlay');
    expect(overlay).toBeTruthy();
    expect(document.body.querySelector('.detail')).toBeTruthy();
    w.unmount();
  });

  it('emits close on overlay self-click', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile }, attachTo: document.body });
    await nextTick();
    const overlay = document.body.querySelector('.file-preview-dialog__overlay') as HTMLElement;
    overlay.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(w.emitted('close')).toBeTruthy();
    w.unmount();
  });

  it('emits close on ESC keydown', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile }, attachTo: document.body });
    await nextTick();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(w.emitted('close')).toBeTruthy();
    w.unmount();
  });

  it('emits close on × button click', async () => {
    const w = mount(FilePreviewDialog, { props: { file: sampleFile }, attachTo: document.body });
    await nextTick();
    const x = document.body.querySelector('.file-preview-dialog__close') as HTMLButtonElement;
    x.click();
    expect(w.emitted('close')).toBeTruthy();
    w.unmount();
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

```
cd web && bun run test -- organisms/files/FilePreviewDialog
```

Expected: import error.

- [ ] **Step 3: Implement the dialog**

Create `web/src/components/organisms/files/FilePreviewDialog.vue`:

```vue
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue';
import FileDetailPanel from './FileDetailPanel.vue';
import { useLocaleStore } from '../../../store/locale';
import type { FileItem } from '../../../types/file';

const props = defineProps<{ file: FileItem | null }>();
const emit = defineEmits<{ (e: 'close'): void }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const isOpen = computed(() => props.file !== null);

const onKey = (ev: KeyboardEvent) => {
  if (ev.key === 'Escape' && isOpen.value) {
    ev.stopPropagation();
    emit('close');
  }
};

onMounted(() => {
  document.addEventListener('keydown', onKey);
});
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey);
});

const onOverlayClick = (ev: MouseEvent) => {
  if (ev.target === ev.currentTarget) emit('close');
};
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="file-preview-dialog__overlay"
      role="presentation"
      @click="onOverlayClick"
    >
      <div
        class="file-preview-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="t('files.preview.title')"
        tabindex="-1"
      >
        <button
          class="file-preview-dialog__close"
          :aria-label="t('files.preview.close')"
          @click="emit('close')"
        >
          ×
        </button>
        <div class="file-preview-dialog__body">
          <FileDetailPanel :file="file" @close="emit('close')" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.file-preview-dialog__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.file-preview-dialog {
  position: relative;
  width: min(1200px, 92vw);
  height: min(800px, 90vh);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  outline: none;
}
.file-preview-dialog__close {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  z-index: 1;
}
.file-preview-dialog__close:hover {
  background: var(--surface-inset);
  color: var(--text-primary);
}
.file-preview-dialog__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}
.file-preview-dialog__body :deep(.detail) {
  flex: 1;
  min-height: 0;
}
</style>
```

- [ ] **Step 4: Add to organism index**

Edit `web/src/components/organisms/files/index.ts`, append:

```ts
export { default as FilePreviewDialog } from './FilePreviewDialog.vue';
```

- [ ] **Step 5: Run tests to confirm pass**

```
cd web && bun run test -- organisms/files/FilePreviewDialog
```

Expected: 5 pass.

- [ ] **Step 6: Commit**

```
git add web/src/components/organisms/files/FilePreviewDialog.vue \
        web/src/components/organisms/files/FilePreviewDialog.spec.ts \
        web/src/components/organisms/files/index.ts
git commit -m "feat(organisms): add FilePreviewDialog modal preview"
```

---

## Task 12: Update `FileRow` with click modifiers, dblclick, data attr

**Files:**
- Modify: `web/src/components/organisms/files/FileRow.vue`
- Create: `web/src/components/organisms/files/FileRow.spec.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/components/organisms/files/FileRow.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileRow from './FileRow.vue';

const baseFile = {
  itemType: 'file' as const,
  id: 'f1',
  name: 'a.txt',
  size: 100,
  mimeType: 'text/plain',
  ownerName: 'me',
  updatedAt: '2026-01-01T00:00:00Z',
  createdAt: '2026-01-01T00:00:00Z',
  folderId: 'root',
  isStarred: false,
};

describe('FileRow', () => {
  it('single click emits select with item + modifiers', async () => {
    const w = mount(FileRow, {
      props: { item: baseFile, selected: false, renaming: false, renameValue: '' },
    });
    await w.find('.row').trigger('click', { shiftKey: false });
    const payloads = w.emitted('select');
    expect(payloads).toHaveLength(1);
    const p = payloads![0][0] as { item: { id: string }; modifiers: { shift: boolean } };
    expect(p.item.id).toBe('f1');
    expect(p.modifiers.shift).toBe(false);
  });

  it('shift+click sets modifiers.shift = true', async () => {
    const w = mount(FileRow, {
      props: { item: baseFile, selected: false, renaming: false, renameValue: '' },
    });
    await w.find('.row').trigger('click', { shiftKey: true });
    const p = w.emitted('select')![0][0] as { modifiers: { shift: boolean } };
    expect(p.modifiers.shift).toBe(true);
  });

  it('dblclick emits activate', async () => {
    const w = mount(FileRow, {
      props: { item: baseFile, selected: false, renaming: false, renameValue: '' },
    });
    await w.find('.row').trigger('dblclick');
    expect(w.emitted('activate')?.[0]?.[0]).toEqual(baseFile);
  });

  it('renaming suppresses dblclick activate', async () => {
    const w = mount(FileRow, {
      props: { item: baseFile, selected: false, renaming: true, renameValue: 'a.txt' },
    });
    await w.find('.row').trigger('dblclick');
    expect(w.emitted('activate')).toBeUndefined();
  });

  it('checkbox change still emits toggleSelect', async () => {
    const w = mount(FileRow, {
      props: { item: baseFile, selected: false, renaming: false, renameValue: '' },
    });
    await w.find('input[type="checkbox"]').trigger('change');
    expect(w.emitted('toggleSelect')?.[0]?.[0]).toBe('f1');
  });

  it('temp folder while renaming carries data-temp-folder-row', () => {
    const tempFolder = { ...baseFile, id: 'temp-new-folder-1', itemType: 'folder' as const, name: '' };
    const w = mount(FileRow, {
      props: { item: tempFolder, selected: false, renaming: true, renameValue: '' },
    });
    expect(w.find('.row').attributes('data-temp-folder-row')).toBe('temp-new-folder-1');
  });

  it('non-temp folder while renaming does NOT carry data-temp-folder-row', () => {
    const regular = { ...baseFile, id: 'regular-1', itemType: 'folder' as const };
    const w = mount(FileRow, {
      props: { item: regular, selected: false, renaming: true, renameValue: 'old' },
    });
    expect(w.find('.row').attributes('data-temp-folder-row')).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

```
cd web && bun run test -- organisms/files/FileRow.spec
```

Expected: most tests fail — current FileRow emits `click(item)` only, no `select` / `activate` / data-temp-folder-row.

- [ ] **Step 3: Update `FileRow.vue`**

Find the `defineEmits` block and replace with:

```ts
const emit = defineEmits<{
  (e: 'update:renameValue', v: string): void;
  (e: 'toggleSelect', id: string): void;
  (e: 'select', payload: { item: ContentItem; modifiers: { shift: boolean } }): void;
  (e: 'activate', item: ContentItem): void;
  (e: 'toggleStar', item: ContentItem): void;
  (e: 'download', item: FileItem): void;
  (e: 'extract-archive', item: FileItem): void;
  (e: 'start-rename', item: ContentItem): void;
  (e: 'cancel-rename'): void;
  (e: 'finish-rename'): void;
  (e: 'start-move', item: ContentItem): void;
  (e: 'start-share', item: ContentItem): void;
  (e: 'delete', item: ContentItem): void;
  (e: 'dragstart', payload: { event: DragEvent; item: ContentItem }): void;
  (e: 'drop-on-folder', payload: { event: DragEvent; folder: FolderItem }): void;
}>();
```

Add script helpers (above `</script>`):

```ts
const onRowClick = (ev: MouseEvent) => {
  if (props.renaming) return;
  ev.stopPropagation();
  emit('select', { item: props.item, modifiers: { shift: ev.shiftKey } });
};

const onRowDblClick = () => {
  if (props.renaming) return;
  emit('activate', props.item);
};

const isTempRow = (item: ContentItem): item is FolderItem =>
  item.itemType === 'folder' && item.id.startsWith('temp-new-folder');
```

Update the row element:

```vue
  <div
    class="row"
    :class="{ 'row--selected': selected }"
    :data-temp-folder-row="renaming && isTempRow(item) ? item.id : null"
    draggable="true"
    @click="onRowClick"
    @dblclick="onRowDblClick"
    @dragstart="emit('dragstart', { event: $event, item })"
    @dragover.prevent
    @drop.prevent="item.itemType === 'folder' && emit('drop-on-folder', { event: $event, folder: item as FolderItem })"
  >
```

(Drop the old `@click="emit('click', item)"`.)

- [ ] **Step 4: Run tests to confirm pass**

```
cd web && bun run test -- organisms/files/FileRow.spec
```

Expected: 7 pass.

- [ ] **Step 5: Sanity check whole suite**

```
cd web && bun run test
```

Expected: green except for callers that pass the old `click` prop — FileTable forwards `@click` from FileRow, so its `emit('click', $event)` listener will silently miss. We update FileTable next.

- [ ] **Step 6: Commit**

```
git add web/src/components/organisms/files/FileRow.vue web/src/components/organisms/files/FileRow.spec.ts
git commit -m "feat(organisms): FileRow emits select+activate with modifiers"
```

---

## Task 13: Update `FileTable` — forward new events + resize handles + CSS vars + grid dblclick + blank click

**Files:**
- Modify: `web/src/components/organisms/files/FileTable.vue`
- Modify: `web/src/components/organisms/files/FileRow.vue` (CSS only)
- Create: `web/src/components/organisms/files/FileTable.spec.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/src/components/organisms/files/FileTable.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileTable from './FileTable.vue';

const items = [
  { itemType: 'file', id: 'f1', name: 'a.txt', size: 1, mimeType: 't', ownerName: 'me', createdAt: '', updatedAt: '', folderId: 'root', isStarred: false },
  { itemType: 'folder', id: 'd1', name: 'docs', size: 0, ownerName: 'me', createdAt: '', updatedAt: '', parentFolderId: null, isStarred: false },
];

const baseProps = {
  mode: 'list' as const,
  items: items as any,
  selection: new Set<string>(),
  renamingId: null,
  renameValue: '',
  sortKey: 'name' as const,
  sortDirection: 'asc' as const,
};

describe('FileTable', () => {
  it('forwards FileRow select events', async () => {
    const w = mount(FileTable, { props: baseProps });
    const row = w.findAll('.row')[0];
    await row.trigger('click', { shiftKey: false });
    const ev = w.emitted('select');
    expect(ev).toBeTruthy();
    expect((ev![0][0] as any).item.id).toBe('f1');
  });

  it('forwards FileRow activate (dblclick)', async () => {
    const w = mount(FileTable, { props: baseProps });
    await w.findAll('.row')[0].trigger('dblclick');
    expect(w.emitted('activate')?.[0]?.[0]).toEqual(items[0]);
  });

  it('container click on blank area emits clear-selection', async () => {
    const w = mount(FileTable, { props: baseProps });
    await w.find('.table').trigger('click');
    expect(w.emitted('clear-selection')).toBeTruthy();
  });

  it('FileRow click does NOT bubble to clear-selection', async () => {
    const w = mount(FileTable, { props: baseProps });
    await w.findAll('.row')[0].trigger('click');
    expect(w.emitted('clear-selection')).toBeUndefined();
  });

  it('resize handles render in header for name/size/time', () => {
    const w = mount(FileTable, { props: baseProps });
    const handles = w.findAll('.resize-handle');
    expect(handles.length).toBe(3);
  });

  it('grid mode: dblclick on card emits activate', async () => {
    const w = mount(FileTable, { props: { ...baseProps, mode: 'grid' as const } });
    await w.findAll('.card')[0].trigger('dblclick');
    expect(w.emitted('activate')?.[0]?.[0]).toEqual(items[0]);
  });

  it('grid mode: single click on card emits select with modifiers', async () => {
    const w = mount(FileTable, { props: { ...baseProps, mode: 'grid' as const } });
    await w.findAll('.card')[0].trigger('click', { shiftKey: true });
    const p = w.emitted('select')![0][0] as { modifiers: { shift: boolean } };
    expect(p.modifiers.shift).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

```
cd web && bun run test -- organisms/files/FileTable.spec
```

Expected: failures across the board.

- [ ] **Step 3: Update `FileTable.vue` script**

Replace the `defineEmits` with:

```ts
const emit = defineEmits<{
  (e: 'update:renameValue', v: string): void;
  (e: 'toggleSelect', id: string): void;
  (e: 'select', payload: { item: ContentItem; modifiers: { shift: boolean } }): void;
  (e: 'activate', item: ContentItem): void;
  (e: 'clear-selection'): void;
  (e: 'toggleStar', item: ContentItem): void;
  (e: 'download', item: FileItem): void;
  (e: 'extract-archive', item: FileItem): void;
  (e: 'start-rename', item: ContentItem): void;
  (e: 'cancel-rename'): void;
  (e: 'finish-rename'): void;
  (e: 'start-move', item: ContentItem): void;
  (e: 'start-share', item: ContentItem): void;
  (e: 'delete', item: ContentItem): void;
  (e: 'dragstart', payload: { event: DragEvent; item: ContentItem }): void;
  (e: 'drop-on-folder', payload: { event: DragEvent; folder: FolderItem }): void;
  (e: 'sort', key: SortKey): void;
}>();
```

Add (after the existing imports / refs):

```ts
import { useColumnResize } from '../../../composables/useColumnResize';

const { colWidths, onResizeStart } = useColumnResize();
const tableStyle = computed(() => ({
  '--col-check': '44px',
  '--col-name': `${colWidths.name}px`,
  '--col-size': `${colWidths.size}px`,
  '--col-time': `${colWidths.time}px`,
  '--col-act': '56px',
}) as Record<string, string>);

const colKeyFor = (sortKey: SortKey): 'name' | 'size' | 'time' =>
  sortKey === 'updatedAt' ? 'time' : sortKey;
```

- [ ] **Step 4: Update `FileTable.vue` template — list mode**

Replace the list-mode block:

```vue
  <div
    v-if="mode === 'list'"
    class="table"
    :style="tableStyle"
    @click.self="emit('clear-selection')"
  >
    <div class="table__head">
      <div class="table__check" />
      <button
        v-for="col in sortable"
        :key="col.key"
        :data-sort-key="col.key"
        class="table__sort"
        :class="{ 'table__sort--active': sortKey === col.key }"
        @click="emit('sort', col.key)"
      >
        {{ col.label }}
        <Icon v-if="sortKey === col.key" :name="sortIcon" :size="12" />
        <span
          class="resize-handle"
          :data-resize-col="colKeyFor(col.key)"
          @pointerdown.stop.prevent="onResizeStart(colKeyFor(col.key), $event as PointerEvent)"
          @click.stop
        />
      </button>
      <div />
    </div>

    <FileRow
      v-for="item in items"
      :key="item.id"
      :item="item"
      :selected="isSelected(item.id)"
      :renaming="renamingId === item.id"
      :rename-value="renameValue"
      @update:rename-value="emit('update:renameValue', $event)"
      @toggle-select="emit('toggleSelect', $event)"
      @select="emit('select', $event)"
      @activate="emit('activate', $event)"
      @toggle-star="emit('toggleStar', $event)"
      @download="emit('download', $event)"
      @extract-archive="emit('extract-archive', $event)"
      @start-rename="emit('start-rename', $event)"
      @cancel-rename="emit('cancel-rename')"
      @finish-rename="emit('finish-rename')"
      @start-move="emit('start-move', $event)"
      @start-share="emit('start-share', $event)"
      @delete="emit('delete', $event)"
      @dragstart="emit('dragstart', $event)"
      @drop-on-folder="emit('drop-on-folder', $event)"
    />
  </div>
```

- [ ] **Step 5: Update `FileTable.vue` template — grid mode**

Replace the `<div v-else-if="mode === 'grid'" class="grid">` block. Change only:
- Root: add `@click.self="emit('clear-selection')"`.
- Card root: replace `@click="emit('click', item)"` with `@click.stop="emit('select', { item, modifiers: { shift: $event.shiftKey } })"` and add `@dblclick="renamingId === item.id ? null : emit('activate', item)"`.

```vue
  <div
    v-else-if="mode === 'grid'"
    class="grid"
    @click.self="emit('clear-selection')"
  >
    <div
      v-for="item in items"
      :key="item.id"
      class="card"
      :class="{ 'card--selected': isSelected(item.id) }"
      draggable="true"
      @click.stop="emit('select', { item, modifiers: { shift: $event.shiftKey } })"
      @dblclick="renamingId === item.id ? null : emit('activate', item)"
      @dragstart="emit('dragstart', { event: $event, item })"
      @dragover.prevent
      @drop.prevent="item.itemType === 'folder' && emit('drop-on-folder', { event: $event, folder: item as FolderItem })"
    >
      <!-- existing card__check, star, icon, name, actions blocks unchanged -->
      <div class="card__check" @click.stop>
        <input type="checkbox" :checked="isSelected(item.id)" @change.stop="emit('toggleSelect', item.id)" />
      </div>
      <button
        class="card__star"
        :class="{ 'card__star--on': item.isStarred }"
        @click.stop="emit('toggleStar', item)"
        :aria-label="item.isStarred ? t('files.table.aria.unstar') : t('files.table.aria.star')"
      >
        <Icon name="star" :size="14" />
      </button>
      <img
        v-if="item.itemType === 'folder'"
        src="../../../assets/generic/folder.svg"
        alt=""
        class="card__icon"
      />
      <img v-else :src="getIconForFile(item.name)" alt="" class="card__icon" />
      <div class="card__name">
        <input
          v-if="renamingId === item.id"
          :value="renameValue"
          class="card__rename"
          @input="emit('update:renameValue', ($event.target as HTMLInputElement).value)"
          @blur="emit('finish-rename')"
          @keydown.enter.prevent="emit('finish-rename')"
          @keydown.esc.prevent="emit('cancel-rename')"
        />
        <span v-else>{{ item.name }}</span>
      </div>
      <div class="card__actions" @click.stop>
        <DropdownMenu>
          <template #trigger>
            <button class="card__menu" :aria-label="t('files.table.aria.cardActions')">…</button>
          </template>
          <template #content>
            <div class="card__menu-list">
              <button v-if="item.itemType === 'file'" @click="emit('download', item as FileItem)">{{ t('files.action.download') }}</button>
              <button
                v-if="item.itemType === 'file' && isArchiveFile(item as FileItem)"
                @click="emit('extract-archive', item as FileItem)"
              >{{ t('files.action.extract') }}…</button>
              <button @click="emit('start-rename', item)">{{ t('files.action.rename') }}</button>
              <button @click="emit('start-move', item)">{{ t('files.action.move') }}</button>
              <button @click="emit('start-share', item)">{{ t('files.action.share') }}</button>
              <button @click="emit('toggleStar', item)">
                {{ item.isStarred ? t('files.action.unstar') : t('files.action.star') }}
              </button>
              <button class="card__menu-danger" @click="emit('delete', item)">{{ t('files.action.delete') }}</button>
            </div>
          </template>
        </DropdownMenu>
      </div>
    </div>
  </div>
```

- [ ] **Step 6: Update `FileTable.vue` CSS — replace `.table__head` and add resize-handle**

```css
.table__head {
  display: grid;
  grid-template-columns: var(--col-check) var(--col-name) var(--col-size) var(--col-time) var(--col-act);
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  height: 32px;
  background: var(--surface-inset);
  border-bottom: 1px solid var(--border-default);
  color: var(--text-dim);
  font-size: 11px;
  letter-spacing: 0.18em;
}
.table__sort { position: relative; }
.resize-handle {
  position: absolute;
  top: 0;
  right: -8px;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
}
.resize-handle:hover {
  background: linear-gradient(to right, transparent, rgb(var(--ac-rgb) / 0.4), transparent);
}
```

- [ ] **Step 7: Update `FileRow.vue` CSS — replace `grid-template-columns` in `.row`**

In `web/src/components/organisms/files/FileRow.vue`, replace:

```css
  grid-template-columns: 44px 1.6fr 0.8fr 1.1fr 56px;
```

with:

```css
  grid-template-columns: var(--col-check, 44px) var(--col-name, 360px) var(--col-size, 120px) var(--col-time, 200px) var(--col-act, 56px);
```

- [ ] **Step 8: Run all related tests**

```
cd web && bun run test -- organisms/files/FileTable.spec
cd web && bun run test -- organisms/files/FileRow.spec
```

Expected: each suite green.

- [ ] **Step 9: Run type check**

```
cd web && bun run check
```

Expected: 0 errors.

- [ ] **Step 10: Commit**

```
git add web/src/components/organisms/files/FileTable.vue \
        web/src/components/organisms/files/FileTable.spec.ts \
        web/src/components/organisms/files/FileRow.vue
git commit -m "feat(organisms): FileTable resize handles + var-driven columns + activate/clear events"
```

---

## Task 14: Wire `useNewFolderCancel` into `useFileActions`

**Files:**
- Modify: `web/src/composables/useFileActions.ts`

- [ ] **Step 1: Edit `useFileActions.ts`**

Add imports at the top:

```ts
import { useNewFolderCancel } from './useNewFolderCancel';
import { useLocaleStore } from '../store/locale';
```

Inside `useFileActions(currentFolderId)`, add near the other refs:

```ts
  const localeStore = useLocaleStore();
  const newFolderCancel = useNewFolderCancel({
    renameInputValue,
    onCancel: () => {
      const tempId = renamingItemId.value;
      if (tempId && tempId.startsWith('temp-new-folder')) {
        fileStore.items = fileStore.items.filter((i) => i.id !== tempId);
      }
      cancelRename();
      ui.toast({ type: 'info', message: localeStore.t('files.toast.newFolderCanceled') });
    },
  });
```

Update `cancelRename` to uninstall the guard:

```ts
  const cancelRename = () => {
    if (renamingItemId.value && renamingItemId.value.startsWith('temp-new-folder')) {
      fileStore.items = fileStore.items.filter((i) => i.id !== renamingItemId.value);
    }
    newFolderCancel.uninstall();
    renamingItemId.value = null;
    renameInputValue.value = '';
    isRenaming.value = false;
  };
```

Update `finishRename` — in each `finally` block, ensure `newFolderCancel.uninstall();` runs (cancelRename already calls it, so the redundant call is just documentation):

```ts
      } finally {
        newFolderCancel.uninstall();
        cancelRename();
        eventBus.emit('refresh-file-tree');
      }
```

Update `handleCreateFolder`:

```ts
  const handleCreateFolder = () => {
    const tempId = `temp-new-folder-${Date.now()}`;
    const tempFolder: FolderItem = {
      itemType: 'folder',
      id: tempId,
      name: '',
      size: 0,
      ownerName: 'You',
      updatedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      parentFolderId: currentFolderId.value,
      permission: 'owner',
    };
    fileStore.items.unshift(tempFolder);
    startRename(tempFolder);
    newFolderCancel.install(tempId);
  };
```

- [ ] **Step 2: Run type check**

```
cd web && bun run check
```

Expected: 0 errors.

- [ ] **Step 3: Run tests**

```
cd web && bun run test
```

Expected: green.

- [ ] **Step 4: Commit**

```
git add web/src/composables/useFileActions.ts
git commit -m "feat(composables): wire useNewFolderCancel for outside-click cancel toast"
```

---

## Task 15: Simplify `RightSidebar` and update `MainLayout`

**Files:**
- Modify: `web/src/components/organisms/shell/RightSidebar.vue`
- Modify: `web/src/components/organisms/shell/RightSidebar.spec.ts`
- Modify: `web/src/components/templates/MainLayout.vue`

- [ ] **Step 1: Rewrite the spec**

Replace `web/src/components/organisms/shell/RightSidebar.spec.ts` entirely with:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import RightSidebar from './RightSidebar.vue';

describe('components/organisms/shell/RightSidebar', () => {
  it('renders a placeholder when visible', () => {
    const w = mount(RightSidebar, { props: { visible: true } });
    expect(w.find('.right-sidebar').exists()).toBe(true);
    expect(w.text()).toContain('Reserved');
  });

  it('hides via class when not visible', () => {
    const w = mount(RightSidebar, { props: { visible: false } });
    expect(w.find('.right-sidebar.visible').exists()).toBe(false);
  });
});
```

- [ ] **Step 2: Rewrite the component**

Replace `web/src/components/organisms/shell/RightSidebar.vue`:

```vue
<script setup lang="ts">
defineProps<{ visible: boolean }>();
</script>

<template>
  <aside :class="['right-sidebar', { visible }]">
    <p class="right-sidebar__placeholder">Reserved for future use.</p>
  </aside>
</template>

<style scoped>
.right-sidebar {
  width: var(--sidebar-right-width);
  margin-right: calc(-1 * var(--sidebar-right-width));
  border-left: 1px solid var(--border-default);
  background: var(--surface-raised);
  display: flex;
  flex-direction: column;
  transition: margin-right var(--mo-duration-mid) var(--mo-easing);
}
.right-sidebar.visible {
  margin-right: 0;
}
.right-sidebar__placeholder {
  padding: var(--sp-md);
  color: var(--text-dim);
  font-size: var(--text-small);
}
</style>
```

- [ ] **Step 3: Update `MainLayout.vue` script setup**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useFileStore } from '../../store/file';
import { storeToRefs } from 'pinia';
import AppHeader from '../organisms/shell/AppHeader.vue';
import LeftSidebar from '../organisms/shell/LeftSidebar.vue';
import RightSidebar from '../organisms/shell/RightSidebar.vue';
import Footer from '../organisms/shell/Footer.vue';
import Spinner from '../atoms/Spinner.vue';
import FilePreviewDialog from '../organisms/files/FilePreviewDialog.vue';

const fileStore = useFileStore();
const { previewFile } = storeToRefs(fileStore);

const leftCollapsed = ref(false);
const rightVisible = ref(false);

const previewForDialog = computed(() =>
  previewFile.value && previewFile.value.itemType === 'file' ? previewFile.value : null,
);

function toggleLeft() { leftCollapsed.value = !leftCollapsed.value; }
function toggleRight() { rightVisible.value = !rightVisible.value; }
function onClosePreview() {
  fileStore.previewFile = null;
  document.body.style.overflow = '';
}
</script>
```

- [ ] **Step 4: Update `MainLayout.vue` template**

Append the dialog at the layout root level (right after the closing `</div>` of `.layout-body`):

```vue
    </div>
    <FilePreviewDialog :file="previewForDialog" @close="onClosePreview" />
  </div>
</template>
```

(Keep AppHeader / LeftSidebar / main / RightSidebar exactly as before. Just remove the old `selectedFile` reactivity since rightVisible is no longer derived from it.)

- [ ] **Step 5: Run tests**

```
cd web && bun run test -- organisms/shell/RightSidebar
```

Expected: 2 pass.

```
cd web && bun run test
```

Expected: all green.

- [ ] **Step 6: Commit**

```
git add web/src/components/organisms/shell/RightSidebar.vue \
        web/src/components/organisms/shell/RightSidebar.spec.ts \
        web/src/components/templates/MainLayout.vue
git commit -m "refactor(shell): RightSidebar becomes placeholder; layout mounts FilePreviewDialog"
```

---

## Task 16: Wire `MyFiles` with new composables and click semantics

**Files:**
- Modify: `web/src/pages/files/MyFiles.vue`

- [ ] **Step 1: Edit `MyFiles.vue` script setup**

Replace the body:

```vue
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useFileStore } from '../../store/file';
import { useSettingsStore } from '../../store/settings';
import { useFileSelection } from '../../composables/useFileSelection';
import { useFileActions } from '../../composables/useFileActions';
import { useBatchActions } from '../../composables/useBatchActions';
import { useUpload } from '../../composables/useUpload';
import { useFileSorting } from '../../composables/useFileSorting';
import { useFileDragMove } from '../../composables/useFileDragMove';
import { useFilePreview } from '../../composables/useFilePreview';
import { toggleFileStar } from '../../api/file';
import { toggleFolderStar } from '../../api/folder';
import { useLocaleStore } from '../../store/locale';
import { EmptyState, FileTable, FileToolbar, BulkActionBar, UploadProgressTray } from '../../components/organisms/files';
import Breadcrumb from '../../components/common/Breadcrumb.vue';
import MoveItemDialog from '../../components/common/MoveItemDialog.vue';
import ShareDialog from '../../components/common/ShareDialog.vue';
import ExtractArchiveDialog from './components/ExtractArchiveDialog.vue';
import { eventBus } from '../../utils/eventBus';
import type { ContentItem, FileItem } from '../../types/file';

const fileStore = useFileStore();
const localeStore = useLocaleStore();
const t = localeStore.t;
const { items, path, isLoading, currentFolderId } = storeToRefs(fileStore);
const { settings } = storeToRefs(useSettingsStore());
const fileInput = ref<HTMLInputElement | null>(null);

const searchQuery = ref(''); const isSearching = ref(false); const searchResults = ref<ContentItem[]>([]);
const selection = useFileSelection();
const { selectedItems, selectedCount, clear: clearSelection } = selection;
const a = useFileActions(currentFolderId);
const { handleBatchDownload, handleBatchDelete } = useBatchActions(selectedItems, clearSelection);
const { uploadTasks, isDragging, handleDragEnter, handleDragLeave, handleDragOver, handleDrop, handleFileSelect } = useUpload(currentFolderId);
const { sortedItems, setSort, sortKey, sortDirection } = useFileSorting(items);
const drag = useFileDragMove({ isSelected: selection.isSelected, selectedItems, handleBatchMove: a.handleBatchMove });
const { openPreview } = useFilePreview();

const viewMode = ref<'list' | 'grid'>((localStorage.getItem('fileflash-view-mode') as 'list' | 'grid') || 'list');
watch(viewMode, (v) => localStorage.setItem('fileflash-view-mode', v));

const displayItems = computed(() => isSearching.value
  ? [...searchResults.value].sort((x, y) => x.name.localeCompare(y.name))
  : sortedItems.value);

const isExtractDialogVisible = ref(false); const fileToExtract = ref<FileItem | null>(null);

const onSearch = async (query: string) => {
  searchQuery.value = query;
  if (!query) { isSearching.value = false; searchResults.value = []; return; }
  isSearching.value = true;
  try { searchResults.value = await fileStore.searchInFolder(currentFolderId.value || 'root', query); } catch { searchResults.value = []; }
};
const onSearchEvt = ({ query }: { query: string }) => onSearch(query);

const onItemSelect = ({ item, modifiers }: { item: ContentItem; modifiers: { shift: boolean } }) => {
  if (a.renamingItemId.value === item.id) return;
  if (modifiers.shift && selection.lastSelectedId.value) {
    selection.selectRange(item.id, displayItems.value);
  } else {
    selection.toggleAdd(item.id);
  }
};

const onItemActivate = (item: ContentItem) => {
  if (a.renamingItemId.value === item.id) return;
  if (item.itemType === 'folder') {
    isSearching.value = false; searchQuery.value = ''; searchResults.value = [];
    fileStore.navigateToFolder(item.id);
    return;
  }
  fileStore.previewFile = item;
  openPreview(item as FileItem);
};

const onClearSelection = () => selection.clear();

const onToggleStar = async (item: ContentItem) => {
  const next = !item.isStarred;
  try {
    if (item.itemType === 'file') await toggleFileStar(item.id, next); else await toggleFolderStar(item.id, next);
    const f = fileStore.items.find((e) => e.id === item.id); if (f) f.isStarred = next;
  } catch (e) { console.error('Failed to update star status', e); }
};
const navigateBC = (id: string) => { isSearching.value = false; searchQuery.value = ''; searchResults.value = []; fileStore.navigateToFolder(id); };

let timer: number | null = null;
watch(() => [settings.value.autoRefreshInterval, currentFolderId.value], () => {
  if (timer !== null) { window.clearInterval(timer); timer = null; }
  const s = Number(settings.value.autoRefreshInterval || 0); if (s <= 0) return;
  timer = window.setInterval(() => fileStore.fetchFolderContents(currentFolderId.value || 'root'), s * 1000);
}, { immediate: true });

onMounted(() => { fileStore.fetchFolderContents('root'); eventBus.on('move-items', drag.onSidebarMove); eventBus.on('search-files', onSearchEvt); });
onUnmounted(() => { eventBus.off('move-items', drag.onSidebarMove); eventBus.off('search-files', onSearchEvt); if (timer !== null) window.clearInterval(timer); });
</script>
```

- [ ] **Step 2: Update the FileTable bindings in the template**

Replace the existing `@toggle-select` / `@click` / `@toggle-star` triplet on the `<FileTable />` with:

```vue
        @toggle-select="selection.toggleSelection" @select="onItemSelect" @activate="onItemActivate"
        @clear-selection="onClearSelection" @toggle-star="onToggleStar"
```

(Delete any prior `@click="onItemClick"` line, and drop the `onItemClick` function definition.)

- [ ] **Step 3: Run type check**

```
cd web && bun run check
```

Expected: 0 errors.

- [ ] **Step 4: Run tests**

```
cd web && bun run test
```

Expected: green.

- [ ] **Step 5: Manual smoke**

```
cd web && bun run dev
```

Open `http://localhost:5173/files`, sign in (use the mock auth), and verify:

1. Single-click a file → row gains accent border (selection toggles).
2. Shift-click another row → range selection adds all between.
3. Click empty area inside the table → selection clears.
4. Double-click a file → preview modal opens centered.
5. ESC / overlay / × → modal closes; body scroll OK.
6. Double-click a folder → navigates in.
7. Click view-mode icon (right side of toolbar) → grid view switches; icons render.

- [ ] **Step 6: Commit**

```
git add web/src/pages/files/MyFiles.vue
git commit -m "feat(pages/files): wire MyFiles to new select/activate + modal preview"
```

---

## Task 17: Update dev library Files section

**Files:**
- Modify: `web/src/pages/__dev/Library.vue`

The `/__dev/library` page already has an "Organisms · Files" section. Add demo handlers so the new behaviors can be exercised in isolation.

- [ ] **Step 1: Add imports + state in the script**

Near the existing `import * as F from '../../components/organisms/files';`, add:

```ts
import { useFilePreview } from '../../composables/useFilePreview';
const filesPreview = useFilePreview();
const filesLastShift = ref('');

function demoOnSelect(payload: { item: { id: string }; modifiers: { shift: boolean } }) {
  filesLastShift.value = `${payload.item.id}${payload.modifiers.shift ? ' (shift)' : ''}`;
  if (payload.modifiers.shift) return;
  const next = new Set(filesSelection.value);
  if (next.has(payload.item.id)) next.delete(payload.item.id);
  else next.add(payload.item.id);
  filesSelection.value = next;
}
function demoOnActivate(item: { id: string; itemType: 'file' | 'folder'; name: string }) {
  if (item.itemType === 'file') {
    filesPreview.openPreview({
      itemType: 'file', id: item.id, name: item.name, size: 0,
      mimeType: 'text/plain', ownerName: 'demo',
      createdAt: '', updatedAt: '', folderId: 'root',
    } as any);
  } else {
    filesLastShift.value = `activate folder ${item.name}`;
  }
}
```

- [ ] **Step 2: Replace the FileTable demo usage**

Find the existing FileTable instance in the "Organisms · Files" section template and replace its event bindings with:

```vue
<F.FileTable
  :mode="filesViewMode"
  :items="demoItems as any"
  :selection="filesSelection"
  :renaming-id="filesRenamingId"
  :rename-value="filesRenameValue"
  :sort-key="filesSortKey"
  :sort-direction="filesSortDirection"
  @select="demoOnSelect"
  @activate="demoOnActivate"
  @clear-selection="filesSelection = new Set()"
  @sort="(k) => (filesSortKey = k)"
/>
<p class="library__note">Last interaction: {{ filesLastShift || '—' }}</p>
<F.FilePreviewDialog
  :file="filesPreview.previewFile.value as any"
  @close="filesPreview.closePreview"
/>
```

- [ ] **Step 3: Run type check**

```
cd web && bun run check
```

Expected: 0 errors (use `as any` casts on demo payloads where strict types push back).

- [ ] **Step 4: Manual smoke**

Open `http://localhost:5173/__dev/library` and click "Organisms · Files":

1. Single click toggles row selection in demo.
2. Double click on `README.md` opens the preview dialog.
3. ESC closes the preview.
4. Click on `projects` folder activates → text appears in the note.

- [ ] **Step 5: Commit**

```
git add web/src/pages/__dev/Library.vue
git commit -m "feat(dev/library): exercise new select/activate/preview on files demo"
```

---

## Task 18: Final verification

- [ ] **Step 1: Run full type check**

```
cd web && bun run check
```

Expected: 0 errors.

- [ ] **Step 2: Run full test suite**

```
cd web && bun run test
```

Expected: every spec green.

- [ ] **Step 3: Manual acceptance on `/files`**

Sign in with the mock account and verify each row:

| Action | Expected |
|---|---|
| Single click a row | Row gains accent border; checkbox state mirrors selection. |
| Shift+click another row | Range fills inclusively. |
| Ctrl+click | Behaves the same as plain click (additive). |
| Click on blank area of `.table` | Selection clears. |
| Double-click a file | Modal opens centered, content fills body. |
| Double-click a folder | Page navigates in; modal does not open. |
| ESC on modal | Modal closes, body scroll restored. |
| Click overlay | Same as ESC. |
| Click × | Same as ESC. |
| Click list / grid icon | View switches. View has correct aria-label. |
| Drag the right edge of "Name" header | Column resizes within clamp. |
| Refresh page | Column widths reset to defaults. |
| Click "New Folder" | Inline rename input opens. |
| Press ESC | Row disappears silently. |
| Click "New Folder", click elsewhere with empty name | Row disappears + toast "New folder canceled." |
| Click "New Folder", type, click elsewhere | Folder is created. |
| Click "New Folder", click on the toast | Does NOT cancel; toast dismisses. |
| Click "New Folder", click on a row dropdown menu | Does NOT cancel. |

- [ ] **Step 4: Build**

```
cd web && bun run build
```

Expected: success.

- [ ] **Step 5: Status**

```
git status
```

Expected: clean tree.

---

## Self-Review Notes

Spec coverage (each spec requirement maps to at least one task):

- Click semantics — Task 4 (composable) + Task 12 (FileRow) + Task 13 (FileTable) + Task 16 (MyFiles)
- View icons — Task 1 (icons.ts) + Task 8 (SegmentedControl) + Task 9 (FileToolbar)
- Modal preview — Task 5 (useFilePreview) + Task 10 (store) + Task 11 (FilePreviewDialog) + Task 15 (MainLayout)
- Column resize — Task 6 (useColumnResize) + Task 13 (FileTable + FileRow CSS)
- New-folder cancel — Task 2 (data attrs) + Task 7 (composable) + Task 14 (wire into useFileActions)
- i18n keys — Task 3
- Dev library — Task 17
- Verification — Task 18

Placeholders / red flags: none — every step shows the actual code or the exact text to change.

Type consistency: the `select` payload `{ item, modifiers: { shift } }` is identical in Tasks 12 (FileRow), 13 (FileTable), 16 (MyFiles), and 17 (Library demo). `useFilePreview` exposes `previewFile`, `openPreview`, `closePreview` consistently in Tasks 5, 11, 15, 16, 17.
