# P4 Other File Surfaces · Implementation Plan

**Spec reference**: `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` §3.1, §4 (P4 row), §9 (acceptance criteria)
**Predecessor**: P3 Core File Path (verified green: 246 tests / typecheck clean as of 2026-05-12)
**Goal**: Migrate Shared / Trash / ShareAccess pages to the Industrial Dashboard system. Each rewritten page file ≤ 100 lines. All visual responsibility moves into organisms under `components/organisms/`. Legacy CSS tokens (`var(--color-border)`, `var(--color-bg-primary)`, `var(--border-radius-*)`) eliminated from these surfaces.

## Scope

3 page files in scope:

| Page | Current LOC | Target LOC |
|---|---|---|
| `pages/shared/SharedWithMe.vue` | 386 | ≤ 100 |
| `pages/trash/Trash.vue` | 258 | ≤ 100 |
| `pages/share/ShareAccess.vue` | 363 | ≤ 100 |

Note on spec wording "复用 FileTable": after reviewing the data shapes, the three surfaces have distinct column sets that do **not** map cleanly onto `FileTable`'s `ContentItem` contract. Building shared sibling table organisms keeps `FileTable` focused. We will still **reuse atoms, molecules, EmptyState, and the design tokens** — that's the real reuse target.

## New Organisms

### `components/organisms/sharing/` (new folder)
- `SharedReceivedTable.vue` — header + rows for `SharedItem[]`. Columns: checkbox, name + type tag, sharedBy, permission, sharedAt (mono), accept-action. Emits `toggle`, `toggle-all`, `accept`.
- `SharedLinksTable.vue` — header + rows for `Share[]`. Columns: resource name + type, share-link code, visits/downloads (mono), createdAt (mono), copy/delete actions. Emits `copy`, `delete`.
- `SharedBatchBar.vue` — selection summary + "Accept Selected" action. Mirrors `BulkActionBar` pattern (count + actions; floating overlay via Transition).
- `index.ts` — public barrel

### `components/organisms/trash/` (new folder)
- `TrashTable.vue` — header + rows for `RecycleBinItem[]`. Columns: icon + name, originalPath, deletedAt (mono), expires-in (mono, accent tint when ≤ 7 days), restore/delete actions. Emits `restore`, `permanent-delete`.
- `index.ts`

### `components/organisms/share/` (new folder; not to be confused with `sharing/` above)
- `ShareInfoCard.vue` — read-only metadata card for an accessed share. Rows: Type, Name, Size (mono), Expires, Password. Uses small uppercase labels per design system.
- `ShareAccessPanel.vue` — gate panel. Two modes: password-protected (TextField + Unlock) or open-access (single "Get Access" button). Emits `request-access`.
- `ShareActionsPanel.vue` — post-access actions: Preview / Download (file only) / Save to My Space. Emits `preview`, `download`, `save`.
- `index.ts`

### `components/organisms/files/`
- `EmptyState.vue` — extend with `variant: 'loading' | 'empty' | 'no-results' | 'error'`. The `'error'` variant is new (replaces the inline `.state.error` block in ShareAccess). Already has `loading`/`empty`/`no-results` from P3; just adds the error case.

## Page Rewrites

### `pages/shared/SharedWithMe.vue` (~80 lines target)
- `<script setup>`: tab state, selection, two data refs, fetch helpers, action handlers
- `<template>`:
  - `PageHeader` block: title + description (raw markup — minor inline)
  - `SegmentedControl` molecule for tab switch
  - `<SharedBatchBar>` (only in received-tab when count > 0; floating overlay pattern from MyFiles)
  - `<SharedReceivedTable>` or `<SharedLinksTable>` based on tab
  - `<EmptyState>` for loading / empty
- `<style scoped>`: page-level layout only (flex column, gap)

### `pages/trash/Trash.vue` (~60 lines target)
- `<script setup>`: items ref, isLoading, three handlers
- `<template>`:
  - PageHeader (title + description + "Clear Bin" `Button`)
  - `<TrashTable>` or `<EmptyState>`
- `<style scoped>`: layout

### `pages/share/ShareAccess.vue` (~90 lines target)
- `<script setup>`: same business logic, just delegate rendering
- `<template>`:
  - PageHeader (title + share code)
  - `<EmptyState variant="loading">` / `<EmptyState variant="error">`
  - `<ShareInfoCard :share>`
  - `<ShareAccessPanel :password-protected :is-accessing @request-access>`
  - `<ShareActionsPanel v-if="accessData" :is-file :can-preview :can-download :is-folder @preview @download @save>`
  - `<SelectFolderDialog ...>` (from existing `components/common/`)
- `<style scoped>`: layout

## Visual Treatment (per Industrial Dashboard tokens)

- Surfaces: `--surface-base` background; cards/tables on `--surface-raised` with `1px solid --border-default`; no border-radius
- Row hover: `--surface-inset` background
- Row selected: `rgb(var(--ac-rgb) / 0.10)` background + `--ac` left border (2px)
- Typography: header labels `--text-label` (uppercase, tracking 0.18em, `--text-dim`); names `--text-body`; mono columns (sizes, dates, counts) use `MonoNumber` or `font-family: --font-mono` + tnum
- Actions: `Button` molecule (`variant="ghost" | "primary" | "danger"`), height matches `--row-h`
- Danger action background tint: `rgb(255 79 44 / 0.10)` border `--status-error`
- Empty/loading states: EmptyState organism, same look as MyFiles

## Dev Library

`pages/__dev/Library.vue` — add three new sections:
- **Organisms · Sharing** — SharedReceivedTable (empty + 3 rows), SharedLinksTable (empty + 3 rows), SharedBatchBar (count = 2)
- **Organisms · Trash** — TrashTable (empty + 3 rows, including one near-expiry)
- **Organisms · Share** — ShareInfoCard, ShareAccessPanel (both modes), ShareActionsPanel (file + folder modes)

Each fixture uses inline mock data shaped to the real TS types.

## Tests

Co-located vitest specs for each new organism (mount + key props + emit assertions):
- `SharedReceivedTable.spec.ts` — renders rows, toggle emits, accept emits
- `SharedLinksTable.spec.ts` — renders rows, copy/delete emits
- `SharedBatchBar.spec.ts` — count display, hidden when count=0
- `TrashTable.spec.ts` — renders rows, restore/delete emits, near-expiry highlight
- `ShareInfoCard.spec.ts` — renders all rows
- `ShareAccessPanel.spec.ts` — password vs open modes; request-access emit
- `ShareActionsPanel.spec.ts` — file mode shows preview/download; folder mode hides them

No page-level tests (consistent with P3 — pages are orchestration only).

Full suite (`bun x vitest run`) must remain green. `bun x vue-tsc --noEmit` must pass.

## Out of Scope (handled in later phases)

- `components/common/SelectFolderDialog.vue` migration to `components/organisms/dialogs/` — P8 cleanup
- `components/common/MoveItemDialog.vue`, `ShareDialog.vue` migration — P8 cleanup
- Removing legacy `var(--color-*)` definitions from `style.css` — P8 cleanup (definitions still needed by Profile/Settings/Dashboard/Agent until P5–P7 finish)
- Search bar wiring on Shared page — not in current product behavior

## Acceptance

- [ ] 3 pages each ≤ 100 lines, only importing from `components/organisms/*`, composables, stores, API, types
- [ ] All new organisms registered in `components/organisms/<group>/index.ts`
- [ ] Dev library shows new organisms in all relevant states
- [ ] No legacy color/spacing tokens (`--color-border`, `--color-bg-primary`, `--border-radius-md`, `--spacing-md`, etc.) used inside the new files
- [ ] `bun x vitest run` — all green
- [ ] `bun x vue-tsc --noEmit` — no errors
- [ ] No `console.error` / `console.warn` from rendering these pages
- [ ] Behavioral parity: all existing actions (accept, batch-accept, copy link, delete link, restore, permanent delete, clear bin, get-access, password unlock, preview, download, save) still work end-to-end

## Commit Plan

Single `feat(p4)` commit at the end, after all acceptance checks pass.
