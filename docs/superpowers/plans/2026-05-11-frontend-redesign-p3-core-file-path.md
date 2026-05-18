# P3 Core File Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the `/files` (MyFiles) surface against the new Industrial Dashboard system. Extract 9 file organisms; the new `MyFiles.vue` must be ≤ 100 lines and contain only orchestration (state wiring, dialog hosts), no inline styling or markup of cells/rows/cards. The old `pages/files/components/` and `components/common/FileTreeNode.vue` / `FolderTreeNode.vue` move into `components/organisms/files/` with new visual treatment. Functional parity with current MyFiles is required — no feature is dropped in P3.

**Architecture:**
- `components/organisms/files/` — 9 organisms:
  - `EmptyState.vue` — empty / loading / "no search matches" panel
  - `UploadProgressTray.vue` — fixed-position upload queue (uses molecule `ProgressBar`)
  - `FileRow.vue` — single list/tree row with name, star, size, time, overflow menu
  - `FileTable.vue` — `mode: list | grid | tree`; renders header + rows (list), cards (grid), or tree nodes; owns selection rectangle, hover, DnD drop targets
  - `FolderTreeNode.vue` — migrated from `common/`; recursive folder children
  - `FileTreeNode.vue` — migrated from `common/`; leaf file under tree mode
  - `FileToolbar.vue` — page top bar: breadcrumb slot, search field, view switcher (SegmentedControl), sort button, "New Folder", "Upload"
  - `BulkActionBar.vue` — appears when `selectedCount > 0`: count + Move / Download / Delete actions
  - `FileDetailPanel.vue` — preview body extracted from existing `RightSidebar.vue`; RightSidebar becomes a thin shell that mounts FileDetailPanel
- `components/organisms/files/index.ts` — public barrel, mirrors atoms/molecules pattern
- `pages/files/MyFiles.vue` — rewritten ≤ 100 lines, imports only from `components/organisms/files`, `components/organisms/dialogs` (still in legacy paths at this phase), and composables/stores
- `pages/__dev/Library.vue` — adds an "Organisms · Files" section for live preview
- **Not deleted in P3** (deferred to P8): `pages/files/components/FileItemsView.vue`, `pages/files/components/ExtractArchiveDialog.vue` (used as-is via legacy import path), `components/common/FileTreeNode.vue`, `components/common/FolderTreeNode.vue`. Migration is **copy-then-replace** — leave the originals so we have a working app between commits.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript strict, Pinia store (`useFileStore`), Vitest + happy-dom + `web/src/test/mount.ts` helper, design tokens from `web/src/styles/tokens/*`. Run commands: `bun run test` / `bun run check` / `bun run build`. CWD for npm scripts: `web/`.

**Spec reference:** `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` §3.1 (component inventory), §3.2 (constraints — pages ≤ 100 lines, only import from `components/*`), §3.3 (dev library), §6 (P3 row).

**Predecessor:** P2 Shell + Templates (commit `4c28f73` + `cc4e5aa`). All shell organisms, templates, and the layout-level transition fix are live.

---

## Pre-flight

- [ ] **Step 0a: Confirm P2 commits are on develop**

```bash
git log --oneline | head -10
```

Expected: `cc4e5aa docs(progress): mark P2 Shell + Templates complete` and `4c28f73 feat(templates): add MainLayout...` reachable.

- [ ] **Step 0b: Verify test + check + build still clean**

```bash
cd web && bun run test && bun run check
```

Expected: all green. If `bun run test` reports failures unrelated to this plan, stop and surface them.

- [ ] **Step 0c: Skim current MyFiles + FileItemsView so you know what behavior must be preserved**

Read `web/src/pages/files/MyFiles.vue` (564 lines) and `web/src/pages/files/components/FileItemsView.vue` (441 lines). Note these behaviors that MUST survive the rewrite:

1. Click folder → `fileStore.navigateToFolder(item.id)`
2. Click file → `fileStore.selectedFile = item` (drives RightSidebar preview)
3. Rename inline (`renamingItemId === item.id`); Enter commits, Esc cancels
4. Star toggle (`toggleFileStar` / `toggleFolderStar`)
5. Drag item → DataTransfer `application/fileflash-item-ids`; drop on folder shows confirm dialog
6. Drag external files into `.file-display-area` → `useUpload.handleDrop`
7. Upload queue panel appears when `uploadTasks.length > 0`
8. Selection rectangle (checkbox per row); BulkActionBar shows count + Move/Download/Delete
9. Search via `eventBus.on('search-files', ...)` from the shell search field
10. Sidebar drop (move via tree) via `eventBus.on('move-items', ...)`
11. Breadcrumb click → `navigateByBreadcrumb`; drop on breadcrumb folder → confirm + move
12. `autoRefreshTimer` re-fetches on `settings.autoRefreshInterval` change
13. Sort key/direction via `useFileSorting`
14. View mode toggle (`grid` / `list`) persisted to `localStorage` key `fileflash-view-mode`
15. Archive files: "Extract..." menu entry when `name.endsWith('.zip'|'.7z'|'.tar'|'.tar.gz'|'.tgz'|'.gz')`

Confirm understanding by writing a one-line summary in your scratch notes — do NOT proceed until each of those 15 behaviors has a known target component in this plan.

---

## File Structure (locked before any task starts)

```
web/src/components/organisms/files/
├── index.ts                      # public barrel
├── EmptyState.vue                # ~80 lines
├── UploadProgressTray.vue        # ~120 lines
├── FileRow.vue                   # ~180 lines
├── FileTable.vue                 # ~280 lines (orchestrates list/grid/tree)
├── FolderTreeNode.vue            # ~120 lines (migrated)
├── FileTreeNode.vue              # ~110 lines (migrated)
├── FileToolbar.vue               # ~180 lines
├── BulkActionBar.vue             # ~100 lines
├── FileDetailPanel.vue           # extracted from RightSidebar.vue
├── EmptyState.spec.ts
├── UploadProgressTray.spec.ts
├── FileRow.spec.ts
├── FileTable.spec.ts
├── FileToolbar.spec.ts
└── BulkActionBar.spec.ts
# Tree nodes + FileDetailPanel get smoke tests only — they own little logic.

web/src/pages/files/MyFiles.vue   # rewritten ≤ 100 lines
web/src/pages/__dev/Library.vue   # +1 section
```

**Import policy:** organisms import only from `../../atoms`, `../../molecules`, sibling files in `./`. Pages import only from `components/organisms/files`, `components/organisms/dialogs` (still legacy in P3 — use existing `components/common/*Dialog.vue` paths until P8 dialog migration). No direct `components/common/*` import from new organism code except where this plan explicitly says so (DropdownMenu).

---

## Phase A — Leaf visual organisms

These have minimal logic; build first because everything else mounts them.

### Task 1: EmptyState organism

**Files:**
- Create: `web/src/components/organisms/files/EmptyState.vue`
- Create: `web/src/components/organisms/files/EmptyState.spec.ts`

**Design notes:**
- 3 visual variants via `variant` prop: `loading` | `empty` | `no-results`
- Loading variant renders `<Spinner />` atom + label "LOADING…" (uppercase tracking-wide per spec §2)
- Empty variant: icon `folder-open` + line "This folder is empty." + secondary "Upload files or create a folder."
- No-results variant: icon `search` + line `"No matches for \"{query}\""`; takes `query` prop
- Token-driven colors only: `--text-dim` / `--text-secondary`. No hex literals.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/components/organisms/files/EmptyState.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import EmptyState from './EmptyState.vue';

describe('EmptyState', () => {
  it('renders loading variant with spinner role', () => {
    const wrapper = mount(EmptyState, { props: { variant: 'loading' } });
    expect(wrapper.find('[data-variant="loading"]').exists()).toBe(true);
    expect(wrapper.text().toLowerCase()).toContain('loading');
  });

  it('renders empty variant copy', () => {
    const wrapper = mount(EmptyState, { props: { variant: 'empty' } });
    expect(wrapper.text()).toContain('This folder is empty');
  });

  it('renders no-results variant with quoted query', () => {
    const wrapper = mount(EmptyState, {
      props: { variant: 'no-results', query: 'foo.txt' },
    });
    expect(wrapper.text()).toContain('"foo.txt"');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && bunx vitest run src/components/organisms/files/EmptyState.spec.ts
```

Expected: FAIL with "Cannot find module './EmptyState.vue'".

- [ ] **Step 3: Implement EmptyState.vue**

```vue
<script setup lang="ts">
import { Icon, Spinner, Text } from '../../atoms';

defineProps<{
  variant: 'loading' | 'empty' | 'no-results';
  query?: string;
}>();
</script>

<template>
  <div class="empty-state" :data-variant="variant">
    <template v-if="variant === 'loading'">
      <Spinner />
      <Text variant="label">LOADING</Text>
    </template>
    <template v-else-if="variant === 'empty'">
      <Icon name="folder-open" :size="32" />
      <Text variant="body">This folder is empty</Text>
      <Text variant="small">Upload files or create a folder.</Text>
    </template>
    <template v-else>
      <Icon name="search" :size="32" />
      <Text variant="body">No matches for "{{ query }}"</Text>
    </template>
  </div>
</template>

<style scoped>
.empty-state {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-dim);
}
</style>
```

If `folder-open` or `search` is not in `atoms/icons.ts`, add them (single-line `<path>` from any free open-source icon set; match stroke style of existing icons). Run `bun run check` to confirm.

- [ ] **Step 4: Run tests to verify pass**

```bash
cd web && bunx vitest run src/components/organisms/files/EmptyState.spec.ts && bun run check
```

Expected: 3 passing, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/EmptyState.vue \
        web/src/components/organisms/files/EmptyState.spec.ts \
        web/src/components/atoms/icons.ts
git commit -m "feat(organisms/files): add EmptyState (loading/empty/no-results)"
```

---

### Task 2: UploadProgressTray organism

**Files:**
- Create: `web/src/components/organisms/files/UploadProgressTray.vue`
- Create: `web/src/components/organisms/files/UploadProgressTray.spec.ts`

**Design notes:**
- Takes `tasks: UploadTask[]` prop. `UploadTask` is the type returned by `useUpload`: `{ id, name, progress: { percentage } }` — re-derive locally rather than importing from composable (keeps organism portable).
- Renders nothing when `tasks.length === 0`.
- Header: `Text variant="label">UPLOAD QUEUE — {n}</Text>`
- Each row: filename (mono), `<ProgressBar :value="percentage" :max="100" />` (molecule), `MonoNumber` showing `{percentage}%`.
- Position: not fixed; placed in normal flow by parent. (Spec §3.1 puts this organism inline above the file display area, matching current MyFiles behavior.)

- [ ] **Step 1: Write the failing test**

```ts
// web/src/components/organisms/files/UploadProgressTray.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import UploadProgressTray from './UploadProgressTray.vue';

const tasks = [
  { id: 't1', name: 'video.mp4', progress: { percentage: 42 } },
  { id: 't2', name: 'doc.pdf', progress: { percentage: 100 } },
];

describe('UploadProgressTray', () => {
  it('renders nothing when tasks list is empty', () => {
    const wrapper = mount(UploadProgressTray, { props: { tasks: [] } });
    expect(wrapper.find('.tray').exists()).toBe(false);
  });

  it('renders one row per task with name + percentage', () => {
    const wrapper = mount(UploadProgressTray, { props: { tasks } });
    expect(wrapper.findAll('.tray__row')).toHaveLength(2);
    expect(wrapper.text()).toContain('video.mp4');
    expect(wrapper.text()).toContain('42');
    expect(wrapper.text()).toContain('100');
  });

  it('shows the queue length in the header', () => {
    const wrapper = mount(UploadProgressTray, { props: { tasks } });
    expect(wrapper.find('.tray__head').text()).toMatch(/2/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && bunx vitest run src/components/organisms/files/UploadProgressTray.spec.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement UploadProgressTray.vue**

```vue
<script setup lang="ts">
import { MonoNumber, Text } from '../../atoms';
import { ProgressBar } from '../../molecules';

export interface UploadTaskView {
  id: string;
  name: string;
  progress: { percentage: number };
}

defineProps<{ tasks: UploadTaskView[] }>();
</script>

<template>
  <section v-if="tasks.length > 0" class="tray">
    <header class="tray__head">
      <Text variant="label">UPLOAD QUEUE — {{ tasks.length }}</Text>
    </header>
    <div class="tray__rows">
      <div v-for="task in tasks" :key="task.id" class="tray__row">
        <span class="tray__name">{{ task.name }}</span>
        <ProgressBar :value="task.progress.percentage" :max="100" />
        <MonoNumber :value="task.progress.percentage" suffix="%" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.tray {
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  padding: 12px 16px;
}
.tray__head {
  margin-bottom: 8px;
}
.tray__rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tray__row {
  display: grid;
  grid-template-columns: minmax(160px, 240px) 1fr 56px;
  align-items: center;
  gap: 12px;
}
.tray__name {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
```

If `MonoNumber` doesn't accept a `suffix` prop, add it as a string prop appended after the formatted value (check existing `MonoNumber.vue`; if not present, use `<MonoNumber :value="task.progress.percentage" /> %` in the template instead — match whatever the atom currently supports).

- [ ] **Step 4: Run tests to verify pass**

```bash
cd web && bunx vitest run src/components/organisms/files/UploadProgressTray.spec.ts && bun run check
```

Expected: 3 passing, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/UploadProgressTray.vue \
        web/src/components/organisms/files/UploadProgressTray.spec.ts
git commit -m "feat(organisms/files): add UploadProgressTray"
```

---

## Phase B — Tree node migration

Migrate verbatim functional behavior; only re-skin to tokens. These exist today in `components/common/`.

### Task 3: Migrate FolderTreeNode + FileTreeNode

**Files:**
- Create: `web/src/components/organisms/files/FolderTreeNode.vue`
- Create: `web/src/components/organisms/files/FileTreeNode.vue`
- Read for reference: `web/src/components/common/FolderTreeNode.vue`, `web/src/components/common/FileTreeNode.vue`

**Design notes:**
- Copy `<script setup>` blocks verbatim from the existing files. Preserve all props, emits, recursive imports.
- Update relative imports: `FolderTreeNode.vue` references `FileTreeNode.vue` and itself — re-point to siblings in the new location.
- Replace hex / `--color-*` tokens with new tokens:
  - `--color-bg-tertiary` → `--surface-inset`
  - `--color-bg-primary` → `--surface-base`
  - `--color-border` → `--border-default`
  - `--color-text-secondary` → `--text-secondary`
  - `--color-text-quaternary` → `--text-dim`
  - `--color-primary` / `--color-primary-light` → `--ac` / accent-tinted background `rgb(var(--ac-rgb) / 0.12)`
- Remove `border-radius` values (B identity uses sharp edges per spec §2); replace with `border-radius: 0`.

- [ ] **Step 1: Copy + retarget FileTreeNode.vue**

Read the source: `web/src/components/common/FileTreeNode.vue`. Copy to new location. Adjust styles per the token map above. **Logic, props, emits unchanged.**

- [ ] **Step 2: Copy + retarget FolderTreeNode.vue**

Read source: `web/src/components/common/FolderTreeNode.vue`. Copy. Adjust:
- Update `import FolderTreeNode from './FolderTreeNode.vue'` (self-recursive) — path stays `./FolderTreeNode.vue` since sibling.
- Update `import FileTreeNode from './FileTreeNode.vue'` — path stays `./FileTreeNode.vue`.
- Apply token map.

- [ ] **Step 3: Smoke test — mount FolderTreeNode with a tiny tree**

Create `web/src/components/organisms/files/FolderTreeNode.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FolderTreeNode from './FolderTreeNode.vue';

describe('FolderTreeNode', () => {
  it('renders folder name', () => {
    const folder = { id: 'f1', name: 'Documents', itemType: 'folder', children: [] };
    const wrapper = mount(FolderTreeNode, {
      props: { folder, depth: 0, expanded: {}, selectedId: null },
    });
    expect(wrapper.text()).toContain('Documents');
  });
});
```

If the props in the source file differ from `{ folder, depth, expanded, selectedId }`, adjust the test to match the actual props. The point of this step is to confirm the component mounts after the migration.

- [ ] **Step 4: Run tests + check**

```bash
cd web && bunx vitest run src/components/organisms/files/ && bun run check
```

Expected: passing, no type errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/FolderTreeNode.vue \
        web/src/components/organisms/files/FileTreeNode.vue \
        web/src/components/organisms/files/FolderTreeNode.spec.ts
git commit -m "feat(organisms/files): migrate FolderTreeNode + FileTreeNode to new tokens"
```

---

## Phase C — Row + Table

### Task 4: FileRow organism

**Files:**
- Create: `web/src/components/organisms/files/FileRow.vue`
- Create: `web/src/components/organisms/files/FileRow.spec.ts`

**Design notes:**
- Renders one row in list mode (grid mode is a separate card layout owned by `FileTable`).
- Props: `item: ContentItem`, `selected: boolean`, `renaming: boolean`, `renameValue: string`.
- Emits: `toggleSelect`, `click`, `toggleStar`, `download`, `extract-archive`, `start-rename`, `cancel-rename`, `finish-rename`, `start-move`, `start-share`, `delete`, `dragstart`, `drop-on-folder`, `update:renameValue`.
- Layout: 5 columns `44px 1.6fr 0.8fr 1.1fr 56px` (checkbox / name / size / time / actions) — same proportions as current FileItemsView list mode.
- Size/time use `MonoNumber` for size and mono `font-feature-settings: "tnum"` for timestamps (per spec §2 — all numeric columns mono).
- Star button: filled when `item.isStarred`; outline otherwise. Fill color = `--ac` (accent), NOT amber `#f59e0b`. (Star color now follows accent theme.)
- Overflow `…` button → uses existing `components/common/DropdownMenu.vue` until P8 migrates it. Import via `import DropdownMenu from '../../common/DropdownMenu.vue';` — record this as the only allowed exception to "no common/* imports from organisms" until P8.
- `isArchiveFile(file)` helper — copy from current FileItemsView verbatim (matches `.zip / .7z / .tar / .tar.gz / .tgz / .gz`).

- [ ] **Step 1: Write the failing test**

```ts
// web/src/components/organisms/files/FileRow.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileRow from './FileRow.vue';

const folder = {
  id: 'fo1', name: 'Pics', itemType: 'folder' as const,
  isStarred: false, updatedAt: '2026-05-01T12:00:00Z',
};
const file = {
  id: 'fi1', name: 'report.pdf', itemType: 'file' as const,
  size: 2048, isStarred: true, updatedAt: '2026-05-02T08:30:00Z',
};

describe('FileRow', () => {
  it('renders name and emits click', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    expect(wrapper.text()).toContain('report.pdf');
    await wrapper.find('.row').trigger('click');
    expect(wrapper.emitted('click')?.[0]?.[0]).toBe(file);
  });

  it('emits toggleSelect when checkbox toggled', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('input[type="checkbox"]').setValue(true);
    expect(wrapper.emitted('toggleSelect')?.[0]?.[0]).toBe(file.id);
  });

  it('shows "--" for folder size', () => {
    const wrapper = mount(FileRow, {
      props: { item: folder, selected: false, renaming: false, renameValue: '' },
    });
    expect(wrapper.text()).toContain('--');
  });

  it('emits toggleStar', async () => {
    const wrapper = mount(FileRow, {
      props: { item: file, selected: false, renaming: false, renameValue: '' },
    });
    await wrapper.find('.row__star').trigger('click');
    expect(wrapper.emitted('toggleStar')?.[0]?.[0]).toBe(file);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && bunx vitest run src/components/organisms/files/FileRow.spec.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement FileRow.vue**

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { Icon, MonoNumber } from '../../atoms';
import DropdownMenu from '../../common/DropdownMenu.vue';
import { getIconForFile } from '../../../utils/fileIcons';
import type { ContentItem, FileItem, FolderItem } from '../../../types/file';

const props = defineProps<{
  item: ContentItem;
  selected: boolean;
  renaming: boolean;
  renameValue: string;
}>();

const emit = defineEmits<{
  (e: 'update:renameValue', v: string): void;
  (e: 'toggleSelect', id: string): void;
  (e: 'click', item: ContentItem): void;
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

const renameProxy = computed({
  get: () => props.renameValue,
  set: (v: string) => emit('update:renameValue', v),
});

const isArchiveFile = (f: FileItem) => {
  const n = (f.name || '').toLowerCase();
  return n.endsWith('.zip') || n.endsWith('.7z') || n.endsWith('.tar')
      || n.endsWith('.tar.gz') || n.endsWith('.tgz') || n.endsWith('.gz');
};

const formatTime = (s: string) => new Date(s).toLocaleString();
</script>

<template>
  <div
    class="row"
    :class="{ 'row--selected': selected }"
    draggable="true"
    @click="emit('click', item)"
    @dragstart="emit('dragstart', { event: $event, item })"
    @dragover.prevent
    @drop.prevent="item.itemType === 'folder' && emit('drop-on-folder', { event: $event, folder: item as FolderItem })"
  >
    <div class="row__check" @click.stop>
      <input
        type="checkbox"
        :checked="selected"
        @change.stop="emit('toggleSelect', item.id)"
      />
    </div>

    <div class="row__name">
      <img
        v-if="item.itemType === 'folder'"
        src="../../../assets/generic/folder.svg"
        alt=""
        class="row__icon"
      />
      <img v-else :src="getIconForFile(item.name)" alt="" class="row__icon" />

      <input
        v-if="renaming"
        v-model="renameProxy"
        class="row__rename"
        @blur="emit('finish-rename')"
        @keydown.enter.prevent="emit('finish-rename')"
        @keydown.esc.prevent="emit('cancel-rename')"
      />
      <span v-else class="row__label">{{ item.name }}</span>

      <button
        class="row__star"
        :class="{ 'row__star--on': item.isStarred }"
        :aria-label="item.isStarred ? 'Unstar' : 'Star'"
        @click.stop="emit('toggleStar', item)"
      >
        <Icon name="star" :size="14" />
      </button>
    </div>

    <div class="row__size">
      <MonoNumber
        v-if="item.itemType === 'file'"
        :value="Number(((item as FileItem).size / 1024).toFixed(1))"
        suffix=" KB"
      />
      <span v-else>--</span>
    </div>

    <div class="row__time">{{ formatTime(item.updatedAt) }}</div>

    <div class="row__actions" @click.stop>
      <DropdownMenu>
        <template #trigger>
          <button class="row__menu" aria-label="Row actions">…</button>
        </template>
        <template #content>
          <div class="row__menu-list">
            <button v-if="item.itemType === 'file'" @click="emit('download', item as FileItem)">Download</button>
            <button
              v-if="item.itemType === 'file' && isArchiveFile(item as FileItem)"
              @click="emit('extract-archive', item as FileItem)"
            >Extract…</button>
            <button @click="emit('start-rename', item)">Rename</button>
            <button @click="emit('start-move', item)">Move</button>
            <button @click="emit('start-share', item)">Share</button>
            <button @click="emit('toggleStar', item)">
              {{ item.isStarred ? 'Unstar' : 'Star' }}
            </button>
            <button class="row__menu-danger" @click="emit('delete', item)">Delete</button>
          </div>
        </template>
      </DropdownMenu>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 44px 1.6fr 0.8fr 1.1fr 56px;
  align-items: center;
  gap: 12px;
  min-height: 40px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-base);
  font-size: 13.5px;
}
.row:hover { background: var(--surface-inset); }
.row--selected {
  background: rgb(var(--ac-rgb) / 0.12);
  box-shadow: inset 2px 0 0 var(--ac);
}
.row__name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.row__icon { width: 18px; height: 18px; flex: none; }
.row__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
}
.row__rename {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--ac);
  color: var(--text-primary);
  padding: 2px 6px;
  font: inherit;
}
.row__star {
  width: 22px; height: 22px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
}
.row__star--on { color: var(--ac); }
.row__size, .row__time {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  color: var(--text-secondary);
  font-size: 12.5px;
}
.row__menu {
  width: 26px; height: 26px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
}
.row__menu-list {
  display: flex; flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  min-width: 160px;
}
.row__menu-list button {
  height: 32px;
  border: none;
  background: transparent;
  padding: 0 12px;
  text-align: left;
  color: var(--text-secondary);
  cursor: pointer;
}
.row__menu-list button:hover { background: var(--surface-inset); color: var(--text-primary); }
.row__menu-danger { color: var(--status-error) !important; }
</style>
```

Add `star` to `atoms/icons.ts` registry if not present.

- [ ] **Step 4: Run tests + check**

```bash
cd web && bunx vitest run src/components/organisms/files/FileRow.spec.ts && bun run check
```

Expected: 4 passing, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/FileRow.vue \
        web/src/components/organisms/files/FileRow.spec.ts \
        web/src/components/atoms/icons.ts
git commit -m "feat(organisms/files): add FileRow (list mode)"
```

---

### Task 5: FileTable organism (list / grid modes)

**Files:**
- Create: `web/src/components/organisms/files/FileTable.vue`
- Create: `web/src/components/organisms/files/FileTable.spec.ts`

**Design notes:**
- Props: `mode: 'list' | 'grid' | 'tree'`, `items: ContentItem[]`, `selection: Set<string>`, `renamingId: string | null`, `renameValue: string`, `sortKey`, `sortDirection`. Tree mode renders nothing in this task (delivered in Task 6 wiring; the prop is accepted so the public API is stable).
- Emits forward every FileRow emit + `sort(key)`. Plus `update:renameValue`.
- List header row clickable to emit `sort` — three columns (name/size/time). The currently-sorted column shows a small `<Icon name="arrow-up" />` / `arrow-down`.
- Grid mode: `grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));` cards. Cards have icon, name (rename input when renaming), star (floating top-right), overflow menu.
- Selection helper: `(id) => props.selection.has(id)`. Don't keep internal state.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/components/organisms/files/FileTable.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileTable from './FileTable.vue';

const items = [
  { id: 'a', name: 'alpha.txt', itemType: 'file' as const, size: 1024, updatedAt: '2026-05-01T00:00:00Z', isStarred: false },
  { id: 'b', name: 'beta', itemType: 'folder' as const, updatedAt: '2026-05-02T00:00:00Z', isStarred: false },
];

describe('FileTable', () => {
  it('renders one row per item in list mode', () => {
    const wrapper = mount(FileTable, {
      props: {
        mode: 'list', items,
        selection: new Set<string>(), renamingId: null, renameValue: '',
        sortKey: 'name', sortDirection: 'asc',
      },
    });
    expect(wrapper.findAllComponents({ name: 'FileRow' })).toHaveLength(2);
  });

  it('renders cards in grid mode', () => {
    const wrapper = mount(FileTable, {
      props: {
        mode: 'grid', items,
        selection: new Set<string>(), renamingId: null, renameValue: '',
        sortKey: 'name', sortDirection: 'asc',
      },
    });
    expect(wrapper.findAll('.card')).toHaveLength(2);
  });

  it('emits sort when list header column clicked', async () => {
    const wrapper = mount(FileTable, {
      props: {
        mode: 'list', items,
        selection: new Set<string>(), renamingId: null, renameValue: '',
        sortKey: 'name', sortDirection: 'asc',
      },
    });
    await wrapper.find('[data-sort-key="size"]').trigger('click');
    expect(wrapper.emitted('sort')?.[0]?.[0]).toBe('size');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && bunx vitest run src/components/organisms/files/FileTable.spec.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement FileTable.vue**

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { Icon } from '../../atoms';
import FileRow from './FileRow.vue';
import DropdownMenu from '../../common/DropdownMenu.vue';
import { getIconForFile } from '../../../utils/fileIcons';
import type { ContentItem, FileItem, FolderItem } from '../../../types/file';

const props = defineProps<{
  mode: 'list' | 'grid' | 'tree';
  items: ContentItem[];
  selection: Set<string>;
  renamingId: string | null;
  renameValue: string;
  sortKey: 'name' | 'size' | 'updatedAt';
  sortDirection: 'asc' | 'desc';
}>();

const emit = defineEmits<{
  (e: 'update:renameValue', v: string): void;
  (e: 'toggleSelect', id: string): void;
  (e: 'click', item: ContentItem): void;
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
  (e: 'sort', key: 'name' | 'size' | 'updatedAt'): void;
}>();

const isSelected = (id: string) => props.selection.has(id);

const sortIcon = computed(() => (props.sortDirection === 'asc' ? 'arrow-up' : 'arrow-down'));
const sortable: Array<{ key: 'name' | 'size' | 'updatedAt'; label: string }> = [
  { key: 'name', label: 'NAME' },
  { key: 'size', label: 'SIZE' },
  { key: 'updatedAt', label: 'UPDATED' },
];

function fwd<T extends keyof typeof emit>(name: T) {
  return (...args: unknown[]) => (emit as any)(name, ...args);
}

const isArchiveFile = (f: FileItem) => {
  const n = (f.name || '').toLowerCase();
  return n.endsWith('.zip') || n.endsWith('.7z') || n.endsWith('.tar')
      || n.endsWith('.tar.gz') || n.endsWith('.tgz') || n.endsWith('.gz');
};
</script>

<template>
  <div v-if="mode === 'list'" class="table">
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
      @click="emit('click', $event)"
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

  <div v-else-if="mode === 'grid'" class="grid">
    <div
      v-for="item in items"
      :key="item.id"
      class="card"
      :class="{ 'card--selected': isSelected(item.id) }"
      draggable="true"
      @click="emit('click', item)"
      @dragstart="emit('dragstart', { event: $event, item })"
      @dragover.prevent
      @drop.prevent="item.itemType === 'folder' && emit('drop-on-folder', { event: $event, folder: item as FolderItem })"
    >
      <div class="card__check" @click.stop>
        <input type="checkbox" :checked="isSelected(item.id)" @change.stop="emit('toggleSelect', item.id)" />
      </div>
      <button
        class="card__star"
        :class="{ 'card__star--on': item.isStarred }"
        @click.stop="emit('toggleStar', item)"
        :aria-label="item.isStarred ? 'Unstar' : 'Star'"
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
            <button class="card__menu" aria-label="Card actions">…</button>
          </template>
          <template #content>
            <div class="card__menu-list">
              <button v-if="item.itemType === 'file'" @click="emit('download', item as FileItem)">Download</button>
              <button
                v-if="item.itemType === 'file' && isArchiveFile(item as FileItem)"
                @click="emit('extract-archive', item as FileItem)"
              >Extract…</button>
              <button @click="emit('start-rename', item)">Rename</button>
              <button @click="emit('start-move', item)">Move</button>
              <button @click="emit('start-share', item)">Share</button>
              <button @click="emit('toggleStar', item)">
                {{ item.isStarred ? 'Unstar' : 'Star' }}
              </button>
              <button class="card__menu-danger" @click="emit('delete', item)">Delete</button>
            </div>
          </template>
        </DropdownMenu>
      </div>
    </div>
  </div>

  <div v-else class="tree">
    <!-- Tree mode wired in Task 6 when FileToolbar provides it. -->
    <slot name="tree" />
  </div>
</template>

<style scoped>
.table {
  display: flex; flex-direction: column;
  border: 1px solid var(--border-default);
  background: var(--surface-base);
}
.table__head {
  display: grid;
  grid-template-columns: 44px 1.6fr 0.8fr 1.1fr 56px;
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
.table__sort {
  background: transparent;
  border: none;
  text-align: left;
  color: inherit;
  cursor: pointer;
  display: inline-flex; align-items: center; gap: 4px;
  font-family: inherit;
  letter-spacing: inherit;
}
.table__sort--active { color: var(--text-primary); }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 12px;
}
.card {
  position: relative;
  display: flex; flex-direction: column;
  align-items: center; gap: 8px;
  padding: 16px 12px;
  background: var(--surface-base);
  border: 1px solid var(--border-default);
}
.card:hover { background: var(--surface-inset); }
.card--selected {
  background: rgb(var(--ac-rgb) / 0.12);
  border-color: var(--ac);
}
.card__check { position: absolute; top: 8px; left: 8px; }
.card__star {
  position: absolute; top: 8px; right: 36px;
  width: 22px; height: 22px;
  background: transparent; border: none;
  color: var(--text-dim);
  cursor: pointer;
}
.card__star--on { color: var(--ac); }
.card__icon { width: 48px; height: 48px; }
.card__name {
  width: 100%;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-primary);
  word-break: break-all;
}
.card__rename {
  width: 100%;
  background: var(--surface-inset);
  border: 1px solid var(--ac);
  color: var(--text-primary);
  padding: 2px 4px;
  font: inherit;
}
.card__actions { position: absolute; top: 8px; right: 8px; }
.card__menu {
  width: 22px; height: 22px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 11px;
}
.card__menu-list {
  display: flex; flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  min-width: 160px;
}
.card__menu-list button {
  height: 32px;
  border: none;
  background: transparent;
  padding: 0 12px;
  text-align: left;
  color: var(--text-secondary);
  cursor: pointer;
}
.card__menu-list button:hover { background: var(--surface-inset); color: var(--text-primary); }
.card__menu-danger { color: var(--status-error) !important; }
</style>
```

If `arrow-up` / `arrow-down` are not in `atoms/icons.ts`, add them.

- [ ] **Step 4: Run tests + check**

```bash
cd web && bunx vitest run src/components/organisms/files/FileTable.spec.ts && bun run check
```

Expected: 3 passing, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/FileTable.vue \
        web/src/components/organisms/files/FileTable.spec.ts \
        web/src/components/atoms/icons.ts
git commit -m "feat(organisms/files): add FileTable (list + grid)"
```

---

## Phase D — Toolbar layer

### Task 6: FileToolbar organism

**Files:**
- Create: `web/src/components/organisms/files/FileToolbar.vue`
- Create: `web/src/components/organisms/files/FileToolbar.spec.ts`

**Design notes:**
- Slots: `breadcrumb` (caller mounts the existing `components/common/Breadcrumb.vue` here; P8 migrates it).
- Props: `viewMode: 'list' | 'grid'`, `sortKey`, `sortDirection`, `searchQuery: string`, `isSearching: boolean`.
- Emits: `update:viewMode`, `update:searchQuery`, `clear-search`, `sort` (cycles next sort key), `create-folder`, `upload`.
- Uses molecules: `SearchField`, `SegmentedControl` (for view toggle), `Button`, `IconButton`.
- View segmented options: `[{ value: 'list', label: 'LIST' }, { value: 'grid', label: 'GRID' }]`.
- Sort button: label `"SORT: {key} {direction}"` in uppercase; clicking cycles `name → size → updatedAt → name` with current direction kept (parent decides direction toggle).
- "New Folder" + "Upload" buttons sit right of sort.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/components/organisms/files/FileToolbar.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import FileToolbar from './FileToolbar.vue';

const baseProps = {
  viewMode: 'list' as const,
  sortKey: 'name' as const,
  sortDirection: 'asc' as const,
  searchQuery: '',
  isSearching: false,
};

describe('FileToolbar', () => {
  it('emits update:viewMode when switcher toggled', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    // Trigger segmented control by clicking the grid option button
    await wrapper.find('[data-test="view-grid"]').trigger('click');
    expect(wrapper.emitted('update:viewMode')?.[0]?.[0]).toBe('grid');
  });

  it('emits create-folder on new folder click', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    await wrapper.find('[data-test="new-folder"]').trigger('click');
    expect(wrapper.emitted('create-folder')).toHaveLength(1);
  });

  it('emits upload on upload click', async () => {
    const wrapper = mount(FileToolbar, { props: baseProps });
    await wrapper.find('[data-test="upload"]').trigger('click');
    expect(wrapper.emitted('upload')).toHaveLength(1);
  });

  it('emits sort to next key when clicked', async () => {
    const wrapper = mount(FileToolbar, { props: { ...baseProps, sortKey: 'name' } });
    await wrapper.find('[data-test="sort"]').trigger('click');
    expect(wrapper.emitted('sort')?.[0]?.[0]).toBe('size');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && bunx vitest run src/components/organisms/files/FileToolbar.spec.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement FileToolbar.vue**

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { Icon } from '../../atoms';
import { Button, SearchField, SegmentedControl } from '../../molecules';
import type { SegmentedOption } from '../../molecules';

type SortKey = 'name' | 'size' | 'updatedAt';
const SORT_ORDER: SortKey[] = ['name', 'size', 'updatedAt'];

const props = defineProps<{
  viewMode: 'list' | 'grid';
  sortKey: SortKey;
  sortDirection: 'asc' | 'desc';
  searchQuery: string;
  isSearching: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:viewMode', v: 'list' | 'grid'): void;
  (e: 'update:searchQuery', v: string): void;
  (e: 'clear-search'): void;
  (e: 'sort', key: SortKey): void;
  (e: 'create-folder'): void;
  (e: 'upload'): void;
}>();

const viewOptions: SegmentedOption[] = [
  { value: 'list', label: 'LIST' },
  { value: 'grid', label: 'GRID' },
];

const nextSortKey = computed<SortKey>(() => {
  const i = SORT_ORDER.indexOf(props.sortKey);
  return SORT_ORDER[(i + 1) % SORT_ORDER.length];
});

function onSortClick() { emit('sort', nextSortKey.value); }
</script>

<template>
  <div class="toolbar">
    <div class="toolbar__left">
      <slot name="breadcrumb" />
      <div v-if="isSearching" class="toolbar__search-tag">
        <span>Search: "{{ searchQuery }}"</span>
        <button class="toolbar__clear" @click="emit('clear-search')">CLEAR</button>
      </div>
    </div>

    <div class="toolbar__right">
      <SearchField
        :model-value="searchQuery"
        placeholder="Search this folder"
        @update:model-value="emit('update:searchQuery', $event)"
      />

      <SegmentedControl
        :model-value="viewMode"
        :options="viewOptions"
        @update:model-value="(v) => emit('update:viewMode', v as 'list' | 'grid')"
      >
        <template #option="{ option }">
          <span :data-test="`view-${option.value}`">{{ option.label }}</span>
        </template>
      </SegmentedControl>

      <button
        data-test="sort"
        class="toolbar__sort"
        @click="onSortClick"
      >
        SORT · {{ sortKey.toUpperCase() }} {{ sortDirection === 'asc' ? '↑' : '↓' }}
      </button>

      <Button data-test="new-folder" variant="ghost" @click="emit('create-folder')">
        <Icon name="folder-plus" :size="14" /> NEW FOLDER
      </Button>
      <Button data-test="upload" variant="primary" @click="emit('upload')">
        <Icon name="upload" :size="14" /> UPLOAD
      </Button>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-default);
}
.toolbar__left {
  display: flex; align-items: center; gap: 12px;
  min-width: 0;
}
.toolbar__right {
  display: flex; align-items: center; gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.toolbar__search-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 8px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
}
.toolbar__clear {
  background: transparent;
  border: none;
  color: var(--ac);
  font-family: var(--font-mono);
  letter-spacing: 0.18em;
  font-size: 10px;
  cursor: pointer;
}
.toolbar__sort {
  height: 28px;
  padding: 0 10px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  cursor: pointer;
}
.toolbar__sort:hover { color: var(--text-primary); border-color: var(--ac); }
</style>
```

**If the SegmentedControl molecule does not support a `#option` slot**, simplify: drop the slot in the template and rely on the test using `[role="tab"]` or button-text matching to find the grid option. Adjust the test to `wrapper.findAll('[role="radio"], button').find(b => b.text() === 'GRID')` if needed. If neither works, change the test to fire `update:modelValue` directly via the SegmentedControl component instance: `await wrapper.findComponent(SegmentedControl).vm.$emit('update:modelValue', 'grid');`. Adapt — keep the assertion that toolbar emits `update:viewMode` with `'grid'`.

Add `folder-plus`, `upload` icons to `atoms/icons.ts` if missing.

- [ ] **Step 4: Run tests + check**

```bash
cd web && bunx vitest run src/components/organisms/files/FileToolbar.spec.ts && bun run check
```

Expected: 4 passing, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/FileToolbar.vue \
        web/src/components/organisms/files/FileToolbar.spec.ts \
        web/src/components/atoms/icons.ts
git commit -m "feat(organisms/files): add FileToolbar"
```

---

### Task 7: BulkActionBar organism

**Files:**
- Create: `web/src/components/organisms/files/BulkActionBar.vue`
- Create: `web/src/components/organisms/files/BulkActionBar.spec.ts`

**Design notes:**
- Props: `count: number`.
- Emits: `move`, `download`, `delete`, `clear`.
- Renders nothing when `count === 0`.
- Sticky strip at top of file display area with mono count + 4 buttons.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/components/organisms/files/BulkActionBar.spec.ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../../test/mount';
import BulkActionBar from './BulkActionBar.vue';

describe('BulkActionBar', () => {
  it('renders nothing when count is 0', () => {
    const wrapper = mount(BulkActionBar, { props: { count: 0 } });
    expect(wrapper.find('.bulk').exists()).toBe(false);
  });

  it('renders count when > 0 and emits delete', async () => {
    const wrapper = mount(BulkActionBar, { props: { count: 3 } });
    expect(wrapper.text()).toContain('3');
    await wrapper.find('[data-test="bulk-delete"]').trigger('click');
    expect(wrapper.emitted('delete')).toHaveLength(1);
  });

  it('emits move, download, clear', async () => {
    const wrapper = mount(BulkActionBar, { props: { count: 2 } });
    await wrapper.find('[data-test="bulk-move"]').trigger('click');
    await wrapper.find('[data-test="bulk-download"]').trigger('click');
    await wrapper.find('[data-test="bulk-clear"]').trigger('click');
    expect(wrapper.emitted('move')).toHaveLength(1);
    expect(wrapper.emitted('download')).toHaveLength(1);
    expect(wrapper.emitted('clear')).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && bunx vitest run src/components/organisms/files/BulkActionBar.spec.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement BulkActionBar.vue**

```vue
<script setup lang="ts">
import { MonoNumber } from '../../atoms';
import { Button } from '../../molecules';

defineProps<{ count: number }>();
defineEmits<{
  (e: 'move'): void;
  (e: 'download'): void;
  (e: 'delete'): void;
  (e: 'clear'): void;
}>();
</script>

<template>
  <div v-if="count > 0" class="bulk">
    <div class="bulk__count">
      <MonoNumber :value="count" />
      <span class="bulk__label">SELECTED</span>
    </div>
    <div class="bulk__actions">
      <Button data-test="bulk-move" variant="ghost" @click="$emit('move')">MOVE</Button>
      <Button data-test="bulk-download" variant="ghost" @click="$emit('download')">DOWNLOAD</Button>
      <Button data-test="bulk-delete" variant="danger" @click="$emit('delete')">DELETE</Button>
      <Button data-test="bulk-clear" variant="ghost" @click="$emit('clear')">CLEAR</Button>
    </div>
  </div>
</template>

<style scoped>
.bulk {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px;
  padding: 8px 12px;
  background: rgb(var(--ac-rgb) / 0.10);
  border: 1px solid var(--ac);
  color: var(--text-primary);
}
.bulk__count {
  display: inline-flex; align-items: baseline; gap: 8px;
}
.bulk__label {
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
}
.bulk__actions {
  display: inline-flex; align-items: center; gap: 6px;
}
</style>
```

If `Button` does not have a `danger` variant, use `ghost` with `style="color: var(--status-error)"` and document the gap as a TODO addressed in a separate molecule task — but DO NOT add a new variant in this plan.

- [ ] **Step 4: Run tests + check**

```bash
cd web && bunx vitest run src/components/organisms/files/BulkActionBar.spec.ts && bun run check
```

Expected: 3 passing, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/organisms/files/BulkActionBar.vue \
        web/src/components/organisms/files/BulkActionBar.spec.ts
git commit -m "feat(organisms/files): add BulkActionBar"
```

---

## Phase E — FileDetailPanel extraction

### Task 8: Extract FileDetailPanel from RightSidebar

**Files:**
- Create: `web/src/components/organisms/files/FileDetailPanel.vue`
- Modify: `web/src/components/organisms/shell/RightSidebar.vue`
- Update test if needed: `web/src/components/organisms/shell/RightSidebar.spec.ts`

**Design notes:**
- Read `RightSidebar.vue` fully. Identify the preview body — the part driven by `useFileStore().selectedFile`. Anything below the sidebar header collapse/close controls.
- Move that body verbatim into `FileDetailPanel.vue`. `FileDetailPanel` takes `file: ContentItem | null` as a prop instead of reading the store directly.
- RightSidebar becomes ~80–120 lines: keeps the sidebar shell (close button, width, collapse), reads store, passes `selectedFile` to `<FileDetailPanel :file="selectedFile" />`.
- Keep all third-party usage in FileDetailPanel: `viewerjs` (images), `plyr` (video/audio), `hls.js` (HLS streams), `pdfjs-dist` (PDF). These were in RightSidebar before — move them, do not re-implement.
- The existing `RightSidebar.spec.ts` mocks `previewFile`, `downloadFile`, viewer/plyr/hls. After extraction, those mocks now apply to FileDetailPanel. If the spec breaks, update it to test FileDetailPanel directly (mount with a fake file prop) and add a minimal RightSidebar smoke test (just check that it renders the panel slot when selectedFile is present).

- [ ] **Step 1: Read RightSidebar.vue and locate the preview body**

```bash
wc -l web/src/components/organisms/shell/RightSidebar.vue
```

Read the whole file. Mark the line range that is "preview body" (from the start of the file preview area to before `</template>`'s sidebar shell close).

- [ ] **Step 2: Create FileDetailPanel.vue with the extracted body**

The component signature:

```vue
<script setup lang="ts">
import type { ContentItem } from '../../../types/file';

defineProps<{ file: ContentItem | null }>();
// (paste extracted preview logic here — refs, watch on file prop, viewer/plyr/hls setup)
</script>
<template>
  <div v-if="file" class="detail">
    <!-- extracted preview markup -->
  </div>
  <div v-else class="detail detail--empty">
    <slot name="empty">
      <span>Select a file to preview.</span>
    </slot>
  </div>
</template>
```

Where the original code read `fileStore.selectedFile.value` / `selectedFile.value`, replace with the `file` prop. The `watch(selectedFile, ...)` becomes `watch(() => props.file, ...)`.

- [ ] **Step 3: Update RightSidebar.vue to mount FileDetailPanel**

Inside RightSidebar's existing template, replace the preview body with:

```vue
<FileDetailPanel :file="selectedFile" />
```

Add the import: `import FileDetailPanel from '../files/FileDetailPanel.vue';`.

Remove from RightSidebar.vue: any imports / refs / watchers that have moved to FileDetailPanel (viewerjs, plyr, hls, pdfjs, previewFile, downloadFile, the preview-specific refs and lifecycle hooks).

- [ ] **Step 4: Run the existing RightSidebar spec**

```bash
cd web && bunx vitest run src/components/organisms/shell/RightSidebar.spec.ts
```

Expected: either still passing (if the spec asserted on outer shell behavior) or failing because the mocks no longer attach to RightSidebar's imports. If failing:

- Update the spec's `vi.mock` targets to mock from `../files/FileDetailPanel.vue` perspective: e.g. `vi.mock('../../../api/file', ...)` paths likely still hold, but viewer/plyr/hls mocks might need to mount FileDetailPanel directly.
- Easier route: split into two specs:
  - `RightSidebar.spec.ts` — smoke test only: mount with empty store, then store with selected file, assert `FileDetailPanel` renders with the right prop. Stub `FileDetailPanel` via `global.stubs`.
  - `FileDetailPanel.spec.ts` — owns the previewFile / viewer / plyr / hls mock setup, mounts with a fake `file` prop.

If you split: move the heavy mock setup wholesale into `FileDetailPanel.spec.ts` and keep RightSidebar.spec lean.

- [ ] **Step 5: Run full test + check + build**

```bash
cd web && bun run test && bun run check
```

Expected: full suite green, type-check clean.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/organisms/files/FileDetailPanel.vue \
        web/src/components/organisms/shell/RightSidebar.vue \
        web/src/components/organisms/shell/RightSidebar.spec.ts \
        web/src/components/organisms/files/FileDetailPanel.spec.ts 2>/dev/null || true
git commit -m "refactor(organisms): extract FileDetailPanel from RightSidebar"
```

---

## Phase F — Barrel + new MyFiles + cutover

### Task 9: Export barrel + add to dev library

**Files:**
- Create: `web/src/components/organisms/files/index.ts`
- Modify: `web/src/pages/__dev/Library.vue`

- [ ] **Step 1: Write the barrel**

```ts
// web/src/components/organisms/files/index.ts
export { default as EmptyState } from './EmptyState.vue';
export { default as UploadProgressTray } from './UploadProgressTray.vue';
export { default as FileRow } from './FileRow.vue';
export { default as FileTable } from './FileTable.vue';
export { default as FolderTreeNode } from './FolderTreeNode.vue';
export { default as FileTreeNode } from './FileTreeNode.vue';
export { default as FileToolbar } from './FileToolbar.vue';
export { default as BulkActionBar } from './BulkActionBar.vue';
export { default as FileDetailPanel } from './FileDetailPanel.vue';
```

- [ ] **Step 2: Add Library section**

Open `web/src/pages/__dev/Library.vue`. After the existing molecules section, add:

```ts
// In the <script setup>:
import * as F from '../../components/organisms/files';
```

Extend `sections` array to include `'Organisms · Files'`. Add a `v-else-if="activeSection === 'Organisms · Files'"` block in the template that demos:

- `<F.EmptyState variant="empty" />`
- `<F.EmptyState variant="loading" />`
- `<F.EmptyState variant="no-results" query="foo" />`
- `<F.UploadProgressTray :tasks="[{ id: 't1', name: 'demo.mp4', progress: { percentage: 64 } }]" />`
- `<F.BulkActionBar :count="4" />`
- A static `FileTable` mounted in list mode and grid mode with 3 fake items (`mode="list"`, `mode="grid"`).

These give a live regression target. Use inline mock objects — no store wiring.

- [ ] **Step 3: Run dev server briefly to sanity-check**

```bash
cd web && bun run dev
```

Open `http://localhost:5173/__dev/library` in a browser. Click "Organisms · Files". Confirm:
- EmptyState 3 variants render
- UploadProgressTray shows the progress row
- BulkActionBar shows count 4
- FileTable list + grid render the 3 mock items, hover/star/menu interact
- Switching `data-accent` between lime/amber/oxide retints star + selected row

Stop dev server when done.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/organisms/files/index.ts \
        web/src/pages/__dev/Library.vue
git commit -m "feat(dev): add Organisms · Files section to /__dev/library"
```

---

### Task 10: Rewrite MyFiles.vue (≤ 100 lines)

**Files:**
- Modify: `web/src/pages/files/MyFiles.vue` (was 564 lines → target ≤ 100)
- Reference: keep `web/src/pages/files/components/ExtractArchiveDialog.vue` (still used as `import ExtractArchiveDialog from './components/ExtractArchiveDialog.vue';`) — migration in P8.

**Design notes:**
- New file is pure orchestration:
  1. Pull composables (`useFileSelection`, `useFileActions`, `useBatchActions`, `useUpload`, `useFileSorting`).
  2. `viewMode` ref persisted to `localStorage`.
  3. `searchQuery` / `isSearching` / `searchResults` refs.
  4. `displayItems` computed.
  5. Event-bus subscriptions (`move-items`, `search-files`).
  6. Auto-refresh timer effect.
  7. Render: `<FileToolbar>` (with breadcrumb slot) + `<BulkActionBar>` + `<UploadProgressTray>` + `<FileTable>` + `<EmptyState>` + dialogs.
- All inline `<style scoped>` removed — minimal layout-only styles allowed (≤ 20 lines) for the page wrapper itself, but no per-row / per-card / per-button styles. Visual responsibility moved into organisms.

- [ ] **Step 1: Write the new MyFiles.vue**

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
import { toggleFileStar } from '../../api/file';
import { toggleFolderStar } from '../../api/folder';
import {
  EmptyState, FileTable, FileToolbar, BulkActionBar, UploadProgressTray,
} from '../../components/organisms/files';
import Breadcrumb from '../../components/common/Breadcrumb.vue';
import MoveItemDialog from '../../components/common/MoveItemDialog.vue';
import ShareDialog from '../../components/common/ShareDialog.vue';
import ExtractArchiveDialog from './components/ExtractArchiveDialog.vue';
import { eventBus } from '../../utils/eventBus';
import { ui } from '../../utils/ui';
import type { ContentItem, FileItem, FolderItem } from '../../types/file';

const fileStore = useFileStore();
const settingsStore = useSettingsStore();
const { items, path, isLoading, currentFolderId } = storeToRefs(fileStore);
const { settings } = storeToRefs(settingsStore);
const fileInput = ref<HTMLInputElement | null>(null);

const searchQuery = ref('');
const isSearching = ref(false);
const searchResults = ref<ContentItem[]>([]);

const { selectedItems, isSelected, toggleSelection, selectedCount, clearSelection } = useFileSelection();
const {
  renamingItemId, renameInputValue, itemToMove, moveItemCount, moveHasActiveShare,
  isMoveDialogVisible, itemToShare, isShareDialogVisible,
  startRename, cancelRename, finishRename,
  handleDelete, handleDownload, handleCreateFolder,
  startMove, startMoveForSelection, closeMoveDialog, handleMoveConfirm,
  startShare, handleBatchMove,
} = useFileActions(currentFolderId);
const { handleBatchDownload, handleBatchDelete } = useBatchActions(selectedItems, clearSelection);
const { uploadTasks, isDragging, handleDragEnter, handleDragLeave, handleDragOver, handleDrop, handleFileSelect } = useUpload(currentFolderId);
const { sortedItems, setSort, sortKey, sortDirection } = useFileSorting(items);

const viewMode = ref<'list' | 'grid'>((localStorage.getItem('fileflash-view-mode') as 'list' | 'grid') || 'list');
watch(viewMode, (v) => localStorage.setItem('fileflash-view-mode', v));

const displayItems = computed(() =>
  isSearching.value ? [...searchResults.value].sort((a, b) => a.name.localeCompare(b.name)) : sortedItems.value,
);

const selectionSet = computed(() => new Set(selectedItems.value));

const isExtractDialogVisible = ref(false);
const fileToExtract = ref<FileItem | null>(null);
const handleExtractArchive = (f: FileItem) => { fileToExtract.value = f; isExtractDialogVisible.value = true; };

const handleSearch = async ({ query }: { query: string }) => {
  searchQuery.value = query;
  if (!query) { isSearching.value = false; searchResults.value = []; return; }
  isSearching.value = true;
  try { searchResults.value = await fileStore.searchInFolder(currentFolderId.value || 'root', query); }
  catch { searchResults.value = []; }
};
const clearSearch = () => handleSearch({ query: '' });

const handleItemClick = (item: ContentItem) => {
  if (renamingItemId.value === item.id) return;
  if (item.itemType === 'folder') { isSearching.value = false; searchQuery.value = ''; searchResults.value = []; fileStore.navigateToFolder(item.id); return; }
  fileStore.selectedFile = item;
};

const handleDragItemStart = ({ event, item }: { event: DragEvent; item: ContentItem }) => {
  if (!event.dataTransfer) return;
  const ids = isSelected(item.id) ? Array.from(selectedItems.value) : [item.id];
  event.dataTransfer.setData('application/fileflash-item-ids', JSON.stringify(ids));
  event.dataTransfer.effectAllowed = 'move';
};
const handleFolderDrop = ({ event, folder }: { event: DragEvent; folder: FolderItem }) => {
  event.preventDefault();
  const raw = event.dataTransfer?.getData('application/fileflash-item-ids'); if (!raw) return;
  const sourceIds: string[] = JSON.parse(raw); if (sourceIds.includes(folder.id)) return;
  ui.confirm({ title: 'Move Items', message: `Move ${sourceIds.length} item(s) into "${folder.name}"?`, confirmText: 'Move' })
    .then((ok) => ok && handleBatchMove(sourceIds, folder.id, 'keep'));
};
const handleBreadcrumbDrop = ({ sourceItemIds, targetFolderId }: { sourceItemIds: string[]; targetFolderId: string }) => {
  ui.confirm({ title: 'Move Items', message: `Move ${sourceItemIds.length} item(s) to this folder?`, confirmText: 'Move' })
    .then((ok) => ok && handleBatchMove(sourceItemIds, targetFolderId, 'keep'));
};
const handleSidebarMove = ({ sourceItemIds, targetFolderId, targetFolderName }: { sourceItemIds: string[]; targetFolderId: string; targetFolderName: string }) => {
  ui.confirm({ title: 'Move Items', message: `Move ${sourceItemIds.length} item(s) to "${targetFolderName}"?`, confirmText: 'Move' })
    .then((ok) => ok && handleBatchMove(sourceItemIds, targetFolderId, 'keep'));
};

const handleToggleStar = async (item: ContentItem) => {
  const target = !item.isStarred;
  try {
    if (item.itemType === 'file') await toggleFileStar(item.id, target); else await toggleFolderStar(item.id, target);
    const found = fileStore.items.find((e) => e.id === item.id); if (found) found.isStarred = target;
  } catch (e) { console.error('Failed to update star status', e); }
};

let autoRefreshTimer: number | null = null;
const resetAutoRefreshTimer = () => {
  if (autoRefreshTimer !== null) { window.clearInterval(autoRefreshTimer); autoRefreshTimer = null; }
  const s = Number(settings.value.autoRefreshInterval || 0); if (s <= 0) return;
  autoRefreshTimer = window.setInterval(() => fileStore.fetchFolderContents(currentFolderId.value || 'root'), s * 1000);
};
watch(() => [settings.value.autoRefreshInterval, currentFolderId.value], resetAutoRefreshTimer, { immediate: true });

const navigateByBreadcrumb = (folderId: string) => { isSearching.value = false; searchQuery.value = ''; searchResults.value = []; fileStore.navigateToFolder(folderId); };

onMounted(() => { fileStore.fetchFolderContents('root'); eventBus.on('move-items', handleSidebarMove); eventBus.on('search-files', handleSearch); });
onUnmounted(() => { eventBus.off('move-items', handleSidebarMove); eventBus.off('search-files', handleSearch); if (autoRefreshTimer !== null) window.clearInterval(autoRefreshTimer); });
</script>

<template>
  <div class="page" @dragenter="handleDragEnter" @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop">
    <input ref="fileInput" type="file" multiple hidden @change="handleFileSelect" />

    <FileToolbar
      :view-mode="viewMode"
      :sort-key="sortKey"
      :sort-direction="sortDirection"
      :search-query="searchQuery"
      :is-searching="isSearching"
      @update:view-mode="viewMode = $event"
      @update:search-query="handleSearch({ query: $event })"
      @clear-search="clearSearch"
      @sort="setSort"
      @create-folder="handleCreateFolder"
      @upload="fileInput?.click()"
    >
      <template #breadcrumb>
        <Breadcrumb :path="path" @navigate="navigateByBreadcrumb" @drop-on-folder="handleBreadcrumbDrop" />
      </template>
    </FileToolbar>

    <BulkActionBar
      :count="selectedCount"
      @move="startMoveForSelection(Array.from(selectedItems))"
      @download="handleBatchDownload"
      @delete="handleBatchDelete"
      @clear="clearSelection"
    />

    <UploadProgressTray :tasks="uploadTasks" />

    <div class="page__body">
      <div v-if="isDragging" class="page__drag">Drop files to upload</div>

      <EmptyState v-if="isLoading" variant="loading" />
      <EmptyState v-else-if="displayItems.length === 0 && isSearching" variant="no-results" :query="searchQuery" />
      <EmptyState v-else-if="displayItems.length === 0" variant="empty" />
      <FileTable
        v-else
        :mode="viewMode"
        :items="displayItems"
        :selection="selectionSet"
        :renaming-id="renamingItemId"
        :rename-value="renameInputValue"
        :sort-key="sortKey"
        :sort-direction="sortDirection"
        @update:rename-value="renameInputValue = $event"
        @toggle-select="toggleSelection"
        @click="handleItemClick"
        @toggle-star="handleToggleStar"
        @download="handleDownload"
        @extract-archive="handleExtractArchive"
        @start-rename="startRename"
        @cancel-rename="cancelRename"
        @finish-rename="finishRename"
        @start-move="startMove"
        @start-share="startShare"
        @delete="handleDelete"
        @dragstart="handleDragItemStart"
        @drop-on-folder="handleFolderDrop"
        @sort="setSort"
      />
    </div>

    <MoveItemDialog
      :is-visible="isMoveDialogVisible" :item-to-move="itemToMove"
      :item-count="moveItemCount" :has-active-share="moveHasActiveShare" :default-share-handling="'keep'"
      @close="closeMoveDialog" @confirm="handleMoveConfirm"
    />
    <ShareDialog :is-visible="isShareDialogVisible" :item-to-share="itemToShare" @close="isShareDialogVisible = false" />
    <ExtractArchiveDialog
      :is-visible="isExtractDialogVisible" :file="fileToExtract" :current-folder-id="currentFolderId"
      @close="isExtractDialogVisible = false"
    />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; height: 100%; min-height: 0; }
.page__body { flex: 1; min-height: 0; overflow: auto; position: relative; }
.page__drag {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgb(var(--ac-rgb) / 0.08);
  border: 1px dashed var(--ac);
  color: var(--ac);
  font-family: var(--font-mono);
  letter-spacing: 0.18em;
  pointer-events: none;
  z-index: 5;
}
</style>
```

- [ ] **Step 2: Verify line count**

```bash
wc -l web/src/pages/files/MyFiles.vue
```

Expected: ≤ 100 lines (template + style do not count against the page logic, but the spec constraint is the whole file — recount if over 100. The skeleton above is intentionally compact; condense further if it exceeds 100).

If you can't get under 100 without removing functionality:
- First try: collapse trivial helpers into inline arrow handlers inside the template.
- Second try: extract drag-handler payload mapping into a single helper in `web/src/composables/useDragMove.ts` (new file ≤ 30 lines).
- Do NOT delete functionality to meet the budget.

- [ ] **Step 3: Run full test + type check**

```bash
cd web && bun run test && bun run check
```

Expected: all green. If existing MyFiles-related specs fail, read the error — most likely they imported `FileItemsView` which still exists, so nothing should break. If a test imported MyFiles directly and asserted on its internals, update it to assert on the new public behavior (events emitted, organism mounts) rather than internal helpers.

- [ ] **Step 4: Manual smoke test in browser**

```bash
cd web && bun run dev
```

Sign in, open `/files`, verify each of the 15 behaviors listed in Step 0c. Pay attention to:

1. Folder navigation — clicking folder card / row updates breadcrumb.
2. File click — RightSidebar preview opens.
3. Inline rename works on both list row and grid card; Enter saves, Esc cancels.
4. Star toggles on both modes, color matches accent (switch accent in `__dev/library` first or via console: `document.documentElement.dataset.accent = 'amber'`).
5. Drag a file onto a folder card — confirm dialog appears, move succeeds.
6. Drag external file into the page — upload triggers, tray shows progress, file appears after upload.
7. Select 3 items → BulkActionBar appears → Delete removes them.
8. Search via the shell header search field — results render, "no matches" empty state when none.
9. Drag a file onto a sidebar tree folder — confirm dialog, move.
10. Drag a file onto a breadcrumb segment — confirm dialog, move.
11. Toggle auto-refresh in Settings to 5s, return to /files, watch for re-fetch (network tab).
12. Click "SORT" header — cycles between name/size/updatedAt; arrow direction flips on second click of same column (this needs `useFileSorting` to flip — verify behavior matches old MyFiles).
13. Toggle LIST/GRID — view persists across reload (localStorage `fileflash-view-mode`).
14. Right-click a `.zip` file — overflow menu shows "Extract…" entry.
15. No layout reflow / no full-page fade on navigation between /files and /shared (P2 fix should still hold).

If any behavior is broken, fix in this task — do not commit broken parity.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/files/MyFiles.vue web/src/composables/useDragMove.ts 2>/dev/null || true
git commit -m "refactor(pages/files): rewrite MyFiles against new organisms (≤100 lines)"
```

---

## Phase G — Verification + memory update

### Task 11: Final verification

- [ ] **Step 1: Full pipeline**

```bash
cd web && bun run test && bun run check && bun run build
```

Expected: all green, build artifact produced.

- [ ] **Step 2: Confirm no orphan imports**

```bash
cd web && bunx vue-tsc --noEmit 2>&1 | tail -20
```

Expected: 0 errors. Any "X is declared but never used" warnings on removed code → clean up.

- [ ] **Step 3: Visual regression — Library**

Run `bun run dev`, open `/__dev/library` → `Organisms · Files`, cycle accent through lime/amber/oxide. Star color, selected row tint, bulk bar border all retint correctly.

- [ ] **Step 4: Visual regression — /files**

Cycle accent on `/files` (set `document.documentElement.dataset.accent` from devtools). All accent-tinted UI (selection, star-on, upload drop overlay, sort arrow, BulkActionBar) retints.

- [ ] **Step 5: No commit needed if all pass**

If anything in steps 1–4 fails, fix and add a follow-up commit. Otherwise this task has no artifact.

---

### Task 12: Update progress memory

**Files:**
- Modify: `C:\Users\xc150\.claude\projects\D--pyprj-fileflash\memory\frontend_redesign_progress.md`

- [ ] **Step 1: Move P3 from "进行中 / 待开始" into "已完成"**

Add entry like:

```
- **P3 Core File Path**（2026-05-11，commits Task 1–10）— 9 files organisms 全部建好（EmptyState/UploadProgressTray/FileRow/FileTable/FolderTreeNode/FileTreeNode/FileToolbar/BulkActionBar/FileDetailPanel），新 `pages/files/MyFiles.vue` X 行（旧 564 行）。`/__dev/library` 加 Organisms · Files 段。旧 `pages/files/components/FileItemsView.vue` 和 `components/common/FileTreeNode.vue|FolderTreeNode.vue` 保留至 P8 清理。
```

Replace `X` with the actual `wc -l` result.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/progress* 2>/dev/null || true   # if any progress doc exists
# Memory file is outside the repo; no git commit needed for it.
# But add a chore commit marking the phase done:
git commit --allow-empty -m "chore(progress): mark P3 Core File Path complete"
```

---

## Self-Review checklist

After all tasks land, run through this once.

1. **Spec coverage** — every component in spec §3.1 `organisms/files/` is created (9 of them). MyFiles ≤ 100 lines (spec §3.2). Dev library has new section (spec §3.3).
2. **Functional parity** — all 15 behaviors from Pre-flight Step 0c work.
3. **Token discipline** — grep new organism files for `#[0-9a-fA-F]{3,6}` or `--color-` references. Should be 0 hits (except the unavoidable `#f59e0b` if you forgot to replace it on star — switch to `var(--ac)`).

```bash
cd web && grep -nE '#[0-9a-fA-F]{3,8}|--color-' src/components/organisms/files/*.vue
```

Expected: empty.

4. **No new common/* imports beyond DropdownMenu** — grep:

```bash
cd web && grep -nE "from '\.\./\.\./common/" src/components/organisms/files/*.vue
```

Expected: only `DropdownMenu` imports. Anything else is a violation; refactor.

5. **Sharp edges** — grep for `border-radius` in new organism CSS:

```bash
cd web && grep -nE 'border-radius' src/components/organisms/files/*.vue
```

Expected: 0 hits (B identity is sharp; spec §2). If any sneak in, set to `0` or remove.

6. **Build + test** — `bun run test && bun run check && bun run build` is green on the final commit.

If any check fails, add a fix commit before declaring P3 done.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-11-frontend-redesign-p3-core-file-path.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
