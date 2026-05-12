# Files UX Tweaks — Design

Date: 2026-05-11
Scope: `/files` page (MyFiles) — click semantics, preview surface, column resizing, new-folder cancel UX.

## Goals

1. Make selection feel like a desktop file manager: single click selects (accumulative), double click "activates" (preview for files, navigate for folders).
2. Replace right-sidebar preview with a centered modal so the sidebar is freed for future use.
3. Allow users to resize the Name / Size / Updated columns (session-only, not persisted).
4. Make new-folder creation cancelable via ESC (silent) and via outside click on empty name (with toast).
5. Use icons instead of "List" / "Grid" text in the view switcher.

## Non-Goals

- Persisting column widths across sessions.
- Filling the right sidebar with new content (placeholder only; later phase decides).
- Touching the Shared / Trash / ShareAccess pages (they will inherit `FileTable` changes when P4 runs).
- Replacing the legacy `ConfirmDialog` (out of scope; only the new `FilePreviewDialog` uses Industrial Dashboard tokens).

## Decisions (settled in brainstorm)

| # | Question | Choice |
|---|---|---|
| 1 | Click semantics | Accumulative multi-select on single click + Shift range + double-click activates + blank-click clears. |
| 2 | View icons | Linear/Notion style: `list` = three rows with leading dots, `grid` = 2×2 squares. Add both to `atoms/icons.ts`. |
| 3 | Preview surface | Centered modal `min(1200px, 92vw) × min(800px, 90vh)`; ESC / overlay click / × all close it. |
| 4 | Column resize | Resizable, **not** persisted. Reset to fr-derived defaults on every mount. |
| 5 | New-folder cancel | ESC = silent cancel. Outside-click on empty name = cancel + toast. Outside-click on typed name = commit (existing blur path). |

## Architecture

### New files

- `web/src/composables/useFilePreview.ts` — `previewFile: Ref<FileItem | null>`, `openPreview(file)`, `closePreview()`. Owns body-scroll lock and focus return (captures `document.activeElement` at open time). `onUnmounted` cleanup.
- `web/src/composables/useColumnResize.ts` — `colWidths: Reactive<{ name: number; size: number; time: number }>`, `onResizeStart(col, event)`. Initial values derived once from container width × default fr ratios. No persistence.
- `web/src/composables/useNewFolderCancel.ts` — `install(tempId)` / `uninstall()`; attaches capture-phase `pointerdown` to `document`; emits `cancel + toast` when outside-click happens with empty `renameInputValue`.
- `web/src/components/organisms/files/FilePreviewDialog.vue` — modal organism. Hosts `FileDetailPanel`. Handles ESC, overlay self-click, × button. Teleports to `body`.

### Extended

- `web/src/composables/useFileSelection.ts` — adds `toggleAdd(id)`, `selectRange(toId, items)`, `clear()`, plus `lastSelectedId: Ref<string | null>`. Existing `toggleSelection(id)` is kept for the checkbox path (does not update `lastSelectedId`).
- `web/src/composables/useFileActions.ts` — `handleCreateFolder` now installs `useNewFolderCancel` after `startRename` and uninstalls in `cancelRename` / `finishRename` exit paths.
- `web/src/store/file.ts` — `fetchFolderContents` clears `previewFile` (alongside the existing `selectedFile = null`). `selectedFile` remains for future "details summary in right sidebar"; not load-bearing for this work.
- `web/src/components/atoms/icons.ts` — add `list` and `grid` entries.
- `web/src/components/molecules/SegmentedControl.vue` — `SegmentedOption` gains optional `icon: IconName` and `ariaLabel: string`; template renders `<Icon>` when `icon` is set, falling back to `label` text.
- `web/src/components/organisms/files/FileRow.vue` — single click emits `select { item, modifiers }` (with `stopPropagation`); new `@dblclick` emits `activate`. Renaming mode short-circuits dblclick. Container has `:data-temp-folder-row` set during temp-folder rename for the outside-click guard.
- `web/src/components/organisms/files/FileTable.vue` — header gains 4px `resize-handle` between columns; list and grid view both use `var(--col-*)` for grid-template-columns; container `@click.self` emits `clear-selection`. Grid cards mirror the dblclick behavior.
- `web/src/components/organisms/files/FileToolbar.vue` — view-mode SegmentedControl options switch to icon-only with `ariaLabel` for screen readers.
- `web/src/pages/files/MyFiles.vue` — adopts `useFilePreview` / `useColumnResize`; splits `onItemClick` into `onItemSelect(item, modifiers)` and `onItemActivate(item)`; handles `clear-selection`. Adds `<FilePreviewDialog />` slot at page root (renders nothing when `previewFile === null`).
- `web/src/components/templates/MainLayout.vue` — `rightVisible` becomes `ref(false)`. `toggleRight` still flips it; default state is hidden.
- `web/src/components/organisms/shell/RightSidebar.vue` — stops mounting `FileDetailPanel`; renders a static placeholder div (`<aside><p class="rs-placeholder">Reserved for future use.</p></aside>`). The preview surface is now `FilePreviewDialog`; this sidebar is intentionally empty until a later phase fills it.
- `web/src/i18n/messages.ts` — add `files.toolbar.aria.list`, `files.toolbar.aria.grid`, `files.toast.newFolderCanceled`, `files.preview.close`, `files.preview.title`.

### Removed / Deprecated

- Nothing on disk is deleted. `RightSidebar.vue` no longer references `FileDetailPanel` (the import goes away). `FileDetailPanel.vue` is still imported by `FilePreviewDialog`, so the file stays.

## Data Flow

### Selection / Activation

```
FileRow @click(e)
  ├─ stopPropagation                         // prevent container @click.self
  └─ emit('select', { item, modifiers: { shift: e.shiftKey } })

FileTable @click(e) (forwards FileRow events; container @click.self → 'clear-selection')

MyFiles onItemSelect(item, modifiers)
  ├─ modifiers.shift && lastSelectedId  → selection.selectRange(item.id, displayItems)
  └─ else                                → selection.toggleAdd(item.id)

Note: in accumulative mode every plain click is additive — Ctrl/Cmd would be redundant,
so we ignore them. Only Shift triggers different behavior (range). Removing modifier-not-used
branches keeps the contract obvious.

FileRow @dblclick → emit('activate', item)
MyFiles onItemActivate(item)
  ├─ renaming?         → ignore (FileRow already short-circuits)
  ├─ folder            → fileStore.navigateToFolder(item.id)
  └─ file              → useFilePreview.openPreview(item)
                         // useFilePreview captures document.activeElement internally
                         // for focus restoration on close — caller passes no trigger.
```

Checkbox path stays separate: `FileRow.row__check @change` → `emit('toggleSelect', id)` → `selection.toggleSelection(id)` (does not touch `lastSelectedId`).

### Preview

```
openPreview(file)
  ├─ lastTrigger = document.activeElement as HTMLElement | null   // capture before focus changes
  ├─ previewFile.value = null; await nextTick(); previewFile.value = file   // force re-watch
  └─ document.body.style.overflow = 'hidden'

FilePreviewDialog
  ├─ watches previewFile → renders overlay + FileDetailPanel when non-null
  ├─ on mount / on become-non-null: dialog.focus()
  ├─ ESC keydown / overlay @click.self / × @click → emit('close') → closePreview()
  └─ on close: document.body.style.overflow = ''; lastTrigger?.focus()

fetchFolderContents (file store): clears previewFile (alongside selectedFile)
```

### Column Resize

```
useColumnResize
  ├─ mount: ResizeObserver one-shot reads container width →
  │          colWidths = { name: w * 1.6 / 3.5, size: w * 0.8 / 3.5, time: w * 1.1 / 3.5 }
  ├─ onResizeStart(col, e):
  │    e.preventDefault()
  │    startX = e.clientX; startW = colWidths[col]
  │    document.addEventListener('pointermove', onMove)
  │    document.addEventListener('pointerup',   onUp,   { once: true })
  │    document.body.style.cursor = 'col-resize'
  ├─ onMove(e):
  │    colWidths[col] = clamp(startW + (e.clientX - startX), MIN[col], MAX[col])
  ├─ onUp / on visibilitychange / on window blur:
  │    remove listeners; restore cursor
  └─ unmount: same cleanup

MIN/MAX: name [120, 800], size [60, 200], time [120, 280]

CSS variables exposed on .table:
  --col-check: 44px
  --col-name:  <px>
  --col-size:  <px>
  --col-time:  <px>
  --col-act:   56px
.table__head, .row { grid-template-columns: var(--col-check) var(--col-name) var(--col-size) var(--col-time) var(--col-act); }
```

### New Folder Cancel

```
useFileActions.handleCreateFolder()
  ├─ insert temp folder; startRename(tempFolder)
  └─ useNewFolderCancel.install(tempId)

useNewFolderCancel.install(tempId)
  ├─ onPointerDown = (e) =>
  │     if e.target.closest(
  │       `[data-temp-folder-row="${tempId}"], [data-ui-toast], [data-dropdown-menu]`
  │     ) return
  │     uninstall()
  │     if renameInputValue.value.trim() === '':
  │       fileStore.items = fileStore.items.filter(i => i.id !== tempId)
  │       cancelRename()       // silent removal portion
  │       ui.toast({ type: 'info', message: t('files.toast.newFolderCanceled') })
  │     // else: let blur fire finishRename naturally (commit)
  └─ document.addEventListener('pointerdown', onPointerDown, { capture: true })

ESC: FileRow @keydown.esc on rename input → emit('cancel-rename') →
     useFileActions.cancelRename() → uninstall (silent, no toast)

finishRename success or failure → also uninstalls
```

### View Icons

`icons.ts` additions (24×24, stroke-2):

```
list: 'M3 6h.01M3 12h.01M3 18h.01M8 6h13M8 12h13M8 18h13'
grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z'
```

`SegmentedOption` shape:

```ts
interface SegmentedOption {
  value: string | number;
  label: string;
  icon?: IconName;
  ariaLabel?: string;  // required when icon is set (label may be empty for icon-only)
}
```

`FileToolbar` viewOptions:

```ts
[
  { value: 'list', label: '', icon: 'list', ariaLabel: t('files.toolbar.aria.list') },
  { value: 'grid', label: '', icon: 'grid', ariaLabel: t('files.toolbar.aria.grid') },
]
```

`SegmentedControl` template renders `<Icon :name="opt.icon" :label="opt.ariaLabel" />` when `opt.icon` exists, else text. CSS keeps the existing 4px padding.

## Edge Cases / Error Handling

- **Same file dblclick'd twice** — `openPreview` resets `previewFile` to null and re-assigns on next tick so `FileDetailPanel`'s `watch(props.file)` re-runs (handles "user changed the file in another tab" case).
- **Shift+click without anchor** — `selectRange` falls back to `toggleAdd` and writes `lastSelectedId = currentId`.
- **Column dragged to min** — `min-width: 0` on `.row__name`; existing ellipsis preserves the layout.
- **pointerup lost** (alt-tab, dialog steals focus) — `visibilitychange` and `window.blur` both invoke the same cleanup path.
- **ESC inside preview while a renaming row was focused beneath it** — preview keydown handler calls `stopPropagation` so the rename ESC does not double-fire.
- **Outside-click on the toast that says "canceled"** — the toast root carries `data-ui-toast`, so the guard ignores it.
- **Outside-click on a dropdown menu** opened from the temp row — dropdown carries `data-dropdown-menu`; ignored.
- **Component unmount while preview open** — `useFilePreview` `onUnmounted` runs `closePreview` (frees body overflow).
- **`navigateToFolder` mid-preview** — `fetchFolderContents` clears `previewFile` so the modal closes naturally.

## Testing

### Unit (vitest + happy-dom)

| File | What it covers |
|---|---|
| `useFileSelection.spec.ts` (new) | `toggleAdd` / `selectRange` / `clear`; `lastSelectedId` updates; range without anchor degrades to toggleAdd; checkbox-toggle path does not move anchor. |
| `useFilePreview.spec.ts` (new) | `openPreview` sets preview + records trigger; second open of same file forces re-watch via null-tick; `closePreview` restores body overflow and focus. |
| `useColumnResize.spec.ts` (new) | Initial widths derived from container; pointerdown→move→up updates value within clamp; visibilitychange triggers cleanup; min/max enforcement. |
| `FileRow.spec.ts` (new) | Single click emits `select` with modifiers; `Shift`/`Ctrl`/`Meta` flags propagated; dblclick emits `activate`; renaming suppresses dblclick; checkbox change still emits `toggleSelect`. |
| `FileTable.spec.ts` (new) | Header CSS vars react to `useColumnResize`; container `@click.self` emits `clear-selection`; grid cards emit dblclick the same way. |
| `FilePreviewDialog.spec.ts` (new) | ESC / overlay self-click / × all emit `close`; FileDetailPanel mounted with prop; body overflow toggled; focus returned to trigger. |
| `useNewFolderCancel.spec.ts` (new) | Outside pointerdown with empty input → cancel + toast; with non-empty → noop; ESC path → no toast; ignored selectors (temp-folder-row, dropdown, toast). |
| `FileToolbar.spec.ts` (update) | view-mode toggle now queried by `aria-label` (icon-only); other emits unchanged. |
| `SegmentedControl.spec.ts` (new) | Renders Icon when `icon` set; passes `ariaLabel`; falls back to text when no icon. |

### Manual

Verified in browser on `/files` (and `/__dev/library` Organisms · Files section where present):

- Single click / Shift+click / Ctrl+click / Cmd+click / blank-area click in list **and** grid view.
- Double-click file (opens modal) / folder (navigates) / temp folder (no-op while renaming).
- Preview modal close paths: ESC, overlay, ×. Body scroll lock restored after close. Focus returns to last triggering row.
- Preview content correctness for image, PDF, video, audio, text.
- Column drag to min/max; reset on refresh; multiple drags in a row.
- New folder: ESC (silent) / outside-click empty (toast) / outside-click typed (commit) / click on toast (does not re-cancel) / click on row dropdown menu (does not cancel).
- View-mode icons render with correct `aria-label`; screen reader announces them.

## Build Sequence (preview for writing-plans)

1. Atoms / molecules infra — `icons.ts` (list/grid), `SegmentedControl` icon support, `SegmentedControl.spec.ts`.
2. Composables — `useFileSelection` extension + spec, `useFilePreview` + spec, `useColumnResize` + spec, `useNewFolderCancel` + spec.
3. Organisms — `FilePreviewDialog` + spec, `FileRow` (dblclick + data attrs) + spec, `FileTable` (resize handles + var-driven columns + blank-click) + spec, `FileToolbar` (icon options) + spec update.
4. Page / store / layout — `MyFiles` rewire, `MainLayout` rightVisible default, `fileStore` previewFile clear, `useFileActions` cancel hook.
5. i18n keys + dev library page updates (Organisms · Files Section: dblclick demo, modal demo, resize demo).
6. Strict `vue-tsc`, `vitest run`, manual browser pass.
