# P7 Agent Track · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Top-level tasks use checkbox (`- [ ]`) syntax for tracking.

**Spec reference:** `docs/superpowers/specs/2026-05-20-frontend-redesign-p7-agent-design.md`
**Total spec:** `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` §3.1, §4 (P7 row), §9
**Predecessors:** P0 / P1 / P2 / P3 / P4 (all green as of `mem:frontend_redesign_progress`)

**Goal:** Rewrite the Agent track (Workspace + Skills + AgentLayout) onto the Industrial Dashboard system. Three-column "engineering dashboard" layout. Zero Naive UI in the Agent track. Each rewritten page file ≤ 100 lines (≤ 60 for AgentLayout). Pre-existing CI build failure (`AgentWorkspace.vue` TS errors) is fixed as a side effect of moving state into a typed composable.

**Tech stack:** Vue 3 SFC + `<script setup lang="ts">`, vue-router, Pinia, vitest + `@vue/test-utils` via `web/src/test/mount.ts`, design tokens from `web/src/styles/tokens/*` (already in P0).

---

## Scope Check

P7 spec covers a single subsystem (Agent track). Admin Dashboard, the rest of P7, is explicitly out of scope this plan. Backend persistence of conversations is out of scope (the spec keeps state in `localStorage`). This plan stays a single coherent unit.

---

## File Structure

### New files (`web/src/components/molecules/`)

| File | Responsibility |
|---|---|
| `Modal.vue` | Generic dialog primitive. Props: `open`, `size: 'sm'\|'md'\|'lg'`, `closeOnBackdrop?: boolean`. Slots: `header`, default (body), `footer`. Emits: `close`. Renders via Teleport-to-body + scrim. ESC + scrim click → emit close (unless `closeOnBackdrop=false`). |
| `Modal.spec.ts` | mount when open, slot rendering, ESC + scrim click emits, `open=false` does not mount body |
| `Pagination.vue` | Props: `page: number`, `pageSize: number`, `total: number`, `siblingCount?: number = 1`. Emits: `update:page`. Renders `[<] [1] ... [N-1] [N] [>]` with JetBrains Mono digits, current page lime. |
| `Pagination.spec.ts` | renders correct number of buttons, prev/next disabled at bounds, click emits new page, no-op when single page |
| `FileDrop.vue` | Props: `accept?: string`, `multiple?: boolean = false`, `disabled?: boolean`. Emits: `files: [File[]]`. Renders: a focusable bordered drop area with hidden `<input type="file">`; click opens picker, drag-drop fires files. |
| `FileDrop.spec.ts` | click opens picker (asserts hidden input is triggered), drop event emits parsed File[], rejects mismatched accept, respects `multiple=false` |
| `Select.vue` | Props: `modelValue`, `options: Array<{ value: string\|number; label: string }>`, `size?: 'sm'\|'md' = 'md'`, `placeholder?: string`. Emits: `update:modelValue`. Built on `components/common/DropdownMenu.vue`. |
| `Select.spec.ts` | renders selected label, opens menu on click, click option emits update, keyboard ↑/↓/Enter navigation |

All four exported via `components/molecules/index.ts`.

### New files (`web/src/composables/`)

| File | Responsibility |
|---|---|
| `useAgentSession.ts` | Conversation CRUD + active switching + `localStorage` persistence under key `fileflash.agent.sessions.v1`. Plan/execute/cancel orchestration with per-kind typed pollers (`pollPlanJob`, `pollExecuteJob`). Cleans up timers on unmount. |
| `useAgentSession.spec.ts` | sendMessage→plan polling succeeds; execute→polling succeeds; cancel stops timers; create/switch/delete sessions; localStorage roundtrip |
| `useAgentSkills.ts` | marketplace + my-skills lists with pagination + debounced search; create / update / delete / import |
| `useAgentSkills.spec.ts` | load + debounced search (fakeTimers), create reloads my-skills, update reloads my-skills, import upsert reloads marketplace |

### New files (`web/src/components/organisms/agent/`)

All exported via new `components/organisms/agent/index.ts`.

| File | Props | Emits | Notes |
|---|---|---|---|
| `SessionList.vue` | `sessions: Session[]`, `activeId: string \| null` | `select: [id]`, `create`, `delete: [id]` | Renders `[+ NEW]` button + scrollable list of `SessionItem`. |
| `SessionItem.vue` | `session: Session`, `active: boolean` | `select`, `delete` | One row. Title truncates, mono `relativeTime`. Active = 2px lime left bar. Delete button visible on hover, click ⇒ `delete` emit with stopPropagation. |
| `TaskTimeline.vue` | `turns: ChatMessage[]`, `focusedId?: string` | `focus-turn: [id]`, `execute: [turnId]`, `cancel: [turnId]` | Scroll container; auto-scrolls to bottom when new turn appears. Renders one `TurnEntry` per `(user, agent)` pair. |
| `TurnEntry.vue` | `turn: AgentTurn`, `policy: AgentExecutionPolicy`, `focused: boolean` | `execute`, `cancel`, `focus` | User row + agent row with plan summary, `PlanActionRow` list, execute/cancel button row, warnings, error state. |
| `PlanActionRow.vue` | `action: AgentProposedAction` | _none_ | Single step row: `step#` + tool name (mono) + `read`/`write` Bar atom + collapsible input JSON. |
| `TaskInputDock.vue` | `modelValue: string`, `policy: AgentExecutionPolicy`, `disabled?: boolean` | `update:modelValue`, `update:policy`, `submit` | Bottom dock with textarea + policy Select + Send Button. Enter submits, Shift+Enter newline. |
| `PlanInspector.vue` | `turn?: AgentTurn \| null` | _none_ | Right rail: when no turn focused, shows empty hint; otherwise shows skill / planHash / cost / actions count / warnings. |
| `SkillCard.vue` | `skill: AgentSkillItem`, `editable?: boolean` | `edit`, `delete` | One card. Editable variant shows Edit + Delete ghost buttons. |
| `SkillEditorPanel.vue` | `open: boolean`, `editingKey: string \| null`, `initial?: Partial<SkillForm>`, `loading?: boolean` | `close`, `submit: [SkillForm]` | Right slide-in panel (built on the new Modal molecule with `size="lg"` + custom right-anchored class). Form fields per Spec §4.2: name / description / triggersText / tools / planTemplate / inputsSchema / outputsSchema (last three under collapsible "Advanced JSON"). |
| `SkillImportPanel.vue` | `loading?: boolean`, `results?: ImportAgentSkillResult[]` | `submit: [{ mode, jsonText }]` | Admin-only widget. SegmentedControl for `upsert`/`insertOnly`, FileDrop for picking `.json`, textarea for raw JSON, Submit button, results list. |

Smoke tests (mount + one core interaction) for: `SessionList.spec.ts`, `TurnEntry.spec.ts`, `SkillCard.spec.ts`.

### Modified files

| File | Change |
|---|---|
| `web/src/pages/agent/workspace/AgentWorkspace.vue` | Full rewrite. Target ≤ 100 lines. Composes `SessionList` + `TaskTimeline` + `TaskInputDock` + `PlanInspector`, all wiring via `useAgentSession()`. |
| `web/src/pages/agent/skills/AgentSkills.vue` | Full rewrite. Target ≤ 100 lines. SegmentedControl tabs + `SkillCard` grid + `Pagination` + `SkillEditorPanel` + `SkillImportPanel`, all wiring via `useAgentSkills()`. |
| `web/src/pages/agent/AgentLayout.vue` | Replace NSpace/NButton + radial-gradient hero with mono brand line + SegmentedControl tabs. Target ≤ 60 lines. |
| `web/src/pages/__dev/Library.vue` | Add sections `'Molecules · Forms'` and `'Organisms · Agent'` to the `sections` tuple + matching `<section>` blocks. |
| `web/src/components/molecules/index.ts` | Export Modal, Pagination, FileDrop, Select. |
| `web/src/components/organisms/agent/index.ts` | New barrel. |

### Out of scope (P8 cleanup)

- Migrating `ConfirmDialog.vue`, `PromptDialog.vue`, `ShareDialog.vue`, `MoveItemDialog.vue`, `SelectFolderDialog.vue`, `FilePreviewDialog.vue` to the new `Modal` molecule.
- Deleting legacy `components/layout/*` and the duplicate `components/common/FolderTreeNode.vue` / `FileTreeNode.vue` / `Breadcrumb.vue`.
- `src/pages/__dev/Library.vue(408,25)` pre-existing `error TS7006` — predates this plan, file is dev-only. If a 5-second fix surfaces (adding `: string` to one param) take it; otherwise leave for P8.

---

## TS Build Fix (Side Effect of Composable Move)

The current build failure (`vue-tsc -b` errors in `AgentWorkspace.vue` lines 161/162/164/234) is resolved automatically by Task 5 (creating `useAgentSession.ts`) and Task 14 (rewriting `AgentWorkspace.vue`). The composable uses two typed pollers — pasted verbatim here so all later tasks reference the same API:

```ts
// inside useAgentSession.ts
async function pollPlanJob(msg: ChatMessage, jobId: string): Promise<void> {
  const timerKey = `${msg.id}:plan`;
  stopPolling(timerKey);

  const tick = async () => {
    try {
      const job = await getAgentJob<AgentPlanResult>(jobId);
      msg.status = (job.status as MsgStatus) || 'running';

      if (job.status === 'succeeded' && job.result) {
        msg.planResult = job.result;
        msg.planHash = job.result.planHash;
      }
      if (job.status === 'failed' || job.status === 'canceled') {
        msg.errorMessage = job.errorMessage || 'Plan failed.';
      }
      if (isTerminalStatus(job.status)) {
        stopPolling(timerKey);
        if (msg.planResult && policy.value === 'autopilot') {
          await runExecute(msg);
        }
      }
    } catch {
      // network blips: skip this tick
    }
  };

  await tick();
  if (!isTerminalStatus(msg.status)) {
    pollTimers.set(timerKey, setInterval(tick, 1200));
  }
}

async function pollExecuteJob(msg: ChatMessage, jobId: string): Promise<void> {
  const timerKey = `${msg.id}:execute`;
  stopPolling(timerKey);

  const tick = async () => {
    try {
      const job = await getAgentJob<AgentExecutionResult>(jobId);
      msg.status = (job.status as MsgStatus) || 'running';

      if (job.status === 'succeeded' && job.result) {
        msg.executeResult = job.result;
      }
      if (job.status === 'failed' || job.status === 'canceled') {
        msg.errorMessage = job.errorMessage || 'Execute failed.';
      }
      if (isTerminalStatus(job.status)) stopPolling(timerKey);
    } catch {
      // skip
    }
  };

  await tick();
  if (!isTerminalStatus(msg.status)) {
    pollTimers.set(timerKey, setInterval(tick, 1200));
  }
}
```

The previous `pollJob(_, _, kind)` and the unused `reactiveUserMsg` are deleted as part of Task 14's full rewrite of the page.

---

## Tasks

### Task 1 — `Modal` molecule

**Files:** create `web/src/components/molecules/Modal.vue` + `Modal.spec.ts`; modify `web/src/components/molecules/index.ts`.

- [ ] Write `Modal.spec.ts` with 4 cases: (a) `open=false` does not mount body content; (b) `open=true` renders `header` / default / `footer` slots; (c) ESC keypress on document emits `close`; (d) click on `.ff-modal__scrim` emits `close` and click on `.ff-modal__panel` does not.
- [ ] Run `cd web && bun x vitest run src/components/molecules/Modal.spec.ts` — expect FAIL ("Cannot find module './Modal.vue'").
- [ ] Implement `Modal.vue`:
  - `<script setup>`: props `open: boolean`, `size: 'sm' \| 'md' \| 'lg' = 'md'`, `closeOnBackdrop: boolean = true`. Emits `close`. `onMounted`+`onBeforeUnmount` register/deregister a `document.addEventListener('keydown', ...)` for ESC.
  - `<template>`: `<Teleport to="body"><Transition name="ff-modal-fade"><div v-if="open" class="ff-modal" @click.self="onBackdrop"><div class="ff-modal__scrim" /><div class="ff-modal__panel" :class="`ff-modal__panel--${size}`"><header class="ff-modal__head" v-if="$slots.header"><slot name="header" /></header><div class="ff-modal__body"><slot /></div><footer class="ff-modal__foot" v-if="$slots.footer"><slot name="footer" /></footer></div></div></Transition></Teleport>`
  - `<style scoped>`: fixed inset 0, flex centered, scrim `background: rgb(0 0 0 / 0.55)`, panel `background: var(--surface-raised)`, `border: 1px solid var(--border-default)`, no border-radius, padding `var(--sp-xl)`. Sizes: `sm` 360px, `md` 560px, `lg` 920px. Transition: opacity 200ms `var(--mo-easing)`.
- [ ] Export from `components/molecules/index.ts`: `export { default as Modal } from './Modal.vue';`
- [ ] Run tests again — expect 4 PASS.
- [ ] Commit: `git add web/src/components/molecules/Modal.vue web/src/components/molecules/Modal.spec.ts web/src/components/molecules/index.ts && git commit -m "feat(web): add Modal molecule"`

### Task 2 — `Pagination` molecule

**Files:** create `web/src/components/molecules/Pagination.vue` + `Pagination.spec.ts`; modify `index.ts`.

- [ ] Write `Pagination.spec.ts` with 4 cases: (a) renders correct page numbers when `total=50, pageSize=10` → pages 1..5; (b) prev disabled at page 1, next disabled at last page; (c) clicking a page number emits `update:page` with that number; (d) `total <= pageSize` → component renders nothing (returns null/comment).
- [ ] Run vitest — expect FAIL.
- [ ] Implement `Pagination.vue`:
  - Props: `page: number`, `pageSize: number`, `total: number`, `siblingCount: number = 1`.
  - Computed `pageCount = Math.max(1, Math.ceil(props.total / props.pageSize))`.
  - Computed `visiblePages`: returns `[1, '…', current-1, current, current+1, '…', last]` style array (collapses with `siblingCount`).
  - Template: `<nav class="ff-pg" v-if="pageCount > 1"><button class="ff-pg__btn" :disabled="page<=1" @click="$emit('update:page', page-1)">‹</button><button v-for="(p, i) in visiblePages" :key="i" class="ff-pg__btn" :class="{ 'is-active': p===page }" :disabled="typeof p !== 'number'" @click="typeof p === 'number' && $emit('update:page', p)">{{ p }}</button><button class="ff-pg__btn" :disabled="page>=pageCount" @click="$emit('update:page', page+1)">›</button></nav>`
  - Style: mono font, `tnum`, button 28×28, hairline border, active = lime bg + dark-on-lime text. No radius.
- [ ] Export from `molecules/index.ts`.
- [ ] Run tests — expect 4 PASS.
- [ ] Commit: `feat(web): add Pagination molecule`

### Task 3 — `FileDrop` molecule

**Files:** create `FileDrop.vue` + `FileDrop.spec.ts`; modify `index.ts`.

- [ ] Write `FileDrop.spec.ts` with 4 cases: (a) renders helper text + accepts slot; (b) `change` event on the hidden input with one File emits `files` with that file in an array; (c) drop event with `dataTransfer.files` emits `files`; (d) when `multiple=false` and 2 files dropped, emits only first.
- [ ] Run — expect FAIL.
- [ ] Implement:
  - Props: `accept?: string`, `multiple?: boolean = false`, `disabled?: boolean`.
  - Emits: `files: [File[]]`.
  - Refs: `inputEl = ref<HTMLInputElement | null>(null)`, `isDragging = ref(false)`.
  - Methods: `openPicker()` calls `inputEl.value?.click()`. `onChange(e)` reads `(e.target as HTMLInputElement).files`, slices to `multiple ? all : [first]`, emits. `onDrop(e)` preventDefault, sets `isDragging=false`, reads `e.dataTransfer.files`, filters by `accept` (mime/extension match using simple split-on-comma logic), slices, emits.
  - Template: `<div class="ff-drop" :class="{ 'is-dragging': isDragging, 'is-disabled': disabled }" tabindex="0" role="button" @click="openPicker" @keydown.enter="openPicker" @dragenter.prevent="isDragging=true" @dragover.prevent @dragleave.prevent="isDragging=false" @drop.prevent="onDrop"><input ref="inputEl" type="file" hidden :accept="accept" :multiple="multiple" @change="onChange" /><span class="ff-drop__label"><slot>Drop file or click to browse</slot></span></div>`
  - Style: hairline border, accent color when dragging, padding `var(--sp-lg)`, mono label.
- [ ] Export from `molecules/index.ts`.
- [ ] Run tests — expect 4 PASS.
- [ ] Commit: `feat(web): add FileDrop molecule`

### Task 4 — `Select` molecule

**Files:** create `Select.vue` + `Select.spec.ts`; modify `index.ts`.

- [ ] Write `Select.spec.ts` with 4 cases: (a) renders the label of the option whose `value === modelValue`; (b) renders placeholder when no match; (c) clicking the trigger shows the menu, clicking an option emits `update:modelValue` with that value and hides the menu; (d) Esc on open menu closes it.
- [ ] Run — expect FAIL.
- [ ] Implement:
  - Props: `modelValue: string \| number`, `options: Array<{ value: string \| number; label: string }>`, `size?: 'sm' \| 'md' = 'md'`, `placeholder?: string`.
  - Emits: `update:modelValue: [value]`.
  - Internal `open = ref(false)`, computed `selectedLabel` from `options.find(...)`.
  - Trigger button (`Button` molecule, `variant="ghost"`, `icon="chevronDown"`) toggles `open`. Menu uses absolutely positioned `<ul>` styled per `MenuItem` molecule.
  - Click-outside via `useEventListener('mousedown', ...)` on document closes menu when target is outside root ref.
  - Keyboard: ↑/↓ navigate, Enter selects, Esc closes.
- [ ] Export from `molecules/index.ts`.
- [ ] Run tests — expect 4 PASS.
- [ ] Commit: `feat(web): add Select molecule`

### Task 5 — `useAgentSession` composable

**Files:** create `web/src/composables/useAgentSession.ts` + `useAgentSession.spec.ts`.

- [ ] Write `useAgentSession.spec.ts` with 5 cases (each uses `vi.useFakeTimers()` + mock of `../api/agent`):
  1. `createSession()` adds to `sessions`, sets `activeSessionId`, persists to `localStorage['fileflash.agent.sessions.v1']`.
  2. `sendMessage('hello')` calls mocked `planAgentTask`, pushes a user + agent message, schedules polling. After fake-tick to terminal `succeeded`, agent message has `planResult` and `planHash` populated.
  3. `runExecute(turn)` calls mocked `executeAgentPlan`, pushes execute job id, polls to terminal `succeeded` → `executeResult` populated.
  4. `cancel(turn)` calls mocked `cancelAgentJob`, clears all timers for that turn.
  5. Reload — instantiate composable twice, assert sessions loaded from localStorage on the second instance.
- [ ] Run — expect FAIL ("Cannot find module").
- [ ] Implement `useAgentSession.ts`:
  - Export `interface ChatMessage { id; role: 'user'\|'agent'; content; status: MsgStatus; planJobId?; planHash?; planResult?: AgentPlanResult; executeJobId?; executeResult?: AgentExecutionResult; errorMessage?; timestamp; }`
  - Export `interface Session { id; title; messages: ChatMessage[]; createdAt; updatedAt; }`
  - Export `type AgentTurn = { user: ChatMessage; agent: ChatMessage; }` — derived from pairs.
  - Module-scope singleton state (so the composable can be called from multiple components): `const sessions = ref<Session[]>(load())`, `const activeSessionId = ref<string|null>(sessions.value[0]?.id ?? null)`, `const policy = ref<AgentExecutionPolicy>('confirm')`, `const isSending = ref(false)`, `const pollTimers = new Map<string, ReturnType<typeof setInterval>>()`.
  - `load()` reads `localStorage['fileflash.agent.sessions.v1']`, parses defensively.
  - `watch(sessions, persist, { deep: true })` writes back JSON.
  - Functions: `createSession`, `switchSession`, `deleteSession`, `resetActiveSession`, `sendMessage(input)`, `runExecute(msg)`, `cancel(msg)`, `pollPlanJob`, `pollExecuteJob`, `stopPolling`, `stopAllPolling` (paste verbatim TS-fix code from earlier section).
  - `onScopeDispose(stopAllPolling)` to cleanup if used in `<script setup>` of a Vue component.
  - Exports default function `useAgentSession()` returning the refs + functions.
- [ ] Run tests — expect 5 PASS.
- [ ] Commit: `feat(web): add useAgentSession composable with localStorage persistence`

### Task 6 — `useAgentSkills` composable

**Files:** create `useAgentSkills.ts` + `useAgentSkills.spec.ts`.

- [ ] Write spec with 4 cases (mock `../api/skill`):
  1. `loadMarketplace()` populates `marketplace.value` with returned items.
  2. Search debounce: setting `queryText` schedules a 250 ms call, advancing timer triggers both `loadMarketplace` and `loadMySkills` once.
  3. `createSkill(payload)` calls `createCustomSkill` then reloads mySkills.
  4. `submitImport({ mode: 'upsert', jsonText })` parses array form, calls `importGlobalSkills`, then reloads marketplace.
- [ ] Run — expect FAIL.
- [ ] Implement:
  - State: `marketplace`, `mySkills` (both `Ref<PaginatedData<AgentSkillItem> \| null>`), `marketplacePage`, `mySkillsPage`, `isMarketplaceLoading`, `isMySkillsLoading`, `queryText`.
  - `useDebounceFn` (`@vueuse/core` already in deps) for search.
  - Editor state: `editingKey: Ref<string \| null>`, `form: reactive(SkillForm)`, helpers `openNewSkill`, `openEditSkill`, `saveSkill`.
  - Import state: `importMode`, `importJsonText`, `importResults`, `importLoading`, `submitImport` (parses array or `{ items }` form).
- [ ] Run tests — expect 4 PASS.
- [ ] Commit: `feat(web): add useAgentSkills composable`

### Task 7 — `SessionItem` + `SessionList` organisms

**Files:** create `web/src/components/organisms/agent/SessionItem.vue` + `SessionList.vue` + `SessionList.spec.ts` + `web/src/components/organisms/agent/index.ts`.

- [ ] Implement `SessionItem.vue`:
  - Props: `session: Session`, `active: boolean`.
  - Emits: `select`, `delete`.
  - Template: `<div class="ff-si" :class="{ 'is-active': active }" @click="$emit('select')"><div class="ff-si__main"><span class="ff-si__title">{{ session.title }}</span><span class="ff-si__time">{{ relativeTime(session.updatedAt) }}</span></div><IconButton icon="trash" label="Delete" size="sm" class="ff-si__del" @click.stop="$emit('delete')" /></div>`
  - Style: padding `var(--sp-sm) var(--sp-md)`, border-bottom hairline, mono time. Active = `border-left: 2px solid var(--ac)` + brighter text. Trash button visible on hover only.
  - Local helper `relativeTime` (extract / inline — mirror the one in current `AgentWorkspace.vue` lines 346-354).
- [ ] Implement `SessionList.vue`:
  - Props: `sessions: Session[]`, `activeId: string | null`.
  - Emits: `select: [id]`, `create`, `delete: [id]`.
  - Template: top `<header class="ff-sl__head"><span class="ff-sl__label">SESSIONS</span><IconButton icon="plus" label="New session" @click="$emit('create')" /></header><div class="ff-sl__list" v-if="sessions.length"><SessionItem v-for="s in sessions" :key="s.id" :session="s" :active="s.id===activeId" @select="$emit('select', s.id)" @delete="$emit('delete', s.id)" /></div><div v-else class="ff-sl__empty">No sessions yet.</div>`
  - Width 240px, full-height column.
- [ ] Write `SessionList.spec.ts` (smoke test):
  - Renders 0 items → shows empty placeholder.
  - Renders N items → calls `select` emit with correct id on item click.
  - Header `+` button emits `create`.
- [ ] Write `components/organisms/agent/index.ts`: `export { default as SessionList } from './SessionList.vue';` + `SessionItem`.
- [ ] Run tests — expect PASS.
- [ ] Commit: `feat(web): add SessionList + SessionItem agent organisms`

### Task 8 — `PlanActionRow` + `TurnEntry`

**Files:** create `PlanActionRow.vue` + `TurnEntry.vue` + `TurnEntry.spec.ts`; update agent barrel.

- [ ] Implement `PlanActionRow.vue`:
  - Props: `action: AgentProposedAction`.
  - Local `expanded = ref(false)`.
  - Template: `<div class="ff-par"><div class="ff-par__head" @click="expanded = !expanded"><span class="ff-par__num">{{ action.step.toString().padStart(2, '0') }}</span><code class="ff-par__tool">{{ action.tool }}</code><Bar :tone="action.sideEffect === 'write' ? 'warn' : 'mute'" class="ff-par__se">{{ action.sideEffect }}</Bar><Icon :name="expanded ? 'chevronUp' : 'chevronDown'" :size="12" /></div><pre v-if="expanded" class="ff-par__input">{{ JSON.stringify(action.input, null, 2) }}</pre></div>`
  - Style: row 28px, mono everywhere, hairline border-bottom. Click toggles JSON.
- [ ] Implement `TurnEntry.vue`:
  - Props: `turn: AgentTurn`, `policy: AgentExecutionPolicy`, `focused: boolean`.
  - Emits: `execute`, `cancel`, `focus`.
  - Computed `canExecute = Boolean(turn.agent.planHash) && turn.agent.status === 'succeeded' && policy !== 'planOnly'`.
  - Computed `isActive = turn.agent.status === 'pending' || turn.agent.status === 'running'`.
  - Template: User row block (right-aligned bordered card), then Agent row block. Agent block conditionals mirror current `AgentWorkspace.vue` template lines 460-573 but using new molecules: `Bar` atom for the running 2px progress bar, `Button` molecule for Execute/Cancel, no Naive UI components. Plan summary uses `<p class="ff-te__sum">{{ turn.agent.planResult.summary }}</p>`. Plan actions are `<PlanActionRow v-for="a in turn.agent.planResult.proposedActions" :key="a.step" :action="a" />`. Cost row uses `MonoNumber` atom.
  - Style: 220ms enter Transition (`opacity 0→1` + `translateY(4px→0)`), focused → `outline: 1px solid var(--ac)` on agent card. Direct corners.
  - Click agent card emits `focus`.
- [ ] Write `TurnEntry.spec.ts` (smoke): renders the plan summary text; with `policy='planOnly'` Execute button is absent; with `status='running'`, Cancel button is present and clicking it emits `cancel`.
- [ ] Add both to agent barrel.
- [ ] Run tests — expect PASS.
- [ ] Commit: `feat(web): add PlanActionRow + TurnEntry agent organisms`

### Task 9 — `TaskTimeline` + `TaskInputDock`

**Files:** create both `.vue` files; update barrel.

- [ ] Implement `TaskTimeline.vue`:
  - Props: `turns: AgentTurn[]`, `policy: AgentExecutionPolicy`, `focusedId?: string`.
  - Emits: forward `execute`, `cancel`, `focus-turn`.
  - Template: `<div ref="scrollEl" class="ff-tt"><header class="ff-tt__label">TIMELINE</header><div v-if="!turns.length" class="ff-tt__welcome"><p class="ff-tt__hint">Type a task below to get started.</p><div class="ff-tt__chips"><button v-for="h in HINTS" :key="h" class="ff-tt__chip" @click="$emit('hint-pick', h)">{{ h }}</button></div></div><TurnEntry v-for="t in turns" :key="t.agent.id" :turn="t" :policy="policy" :focused="t.agent.id === focusedId" @execute="$emit('execute', t.agent.id)" @cancel="$emit('cancel', t.agent.id)" @focus="$emit('focus-turn', t.agent.id)" /></div>`
  - Add `HINTS` const: 3 example tasks (mirror current welcome chips line 437-441).
  - `watchEffect`: after `turns.length` change, `nextTick` then `scrollEl.value.scrollTop = scrollEl.value.scrollHeight`.
- [ ] Implement `TaskInputDock.vue`:
  - Props: `modelValue: string`, `policy: AgentExecutionPolicy`, `disabled?: boolean`.
  - Emits: `update:modelValue`, `update:policy`, `submit`.
  - Local consts: `POLICY_OPTIONS = [{ value: 'planOnly', label: 'PLAN ONLY' }, { value: 'confirm', label: 'CONFIRM' }, { value: 'autopilot', label: 'AUTOPILOT' }]`.
  - Template: `<footer class="ff-tid"><textarea class="ff-tid__ta" :value="modelValue" @input="onInput" @keydown="onKey" :placeholder="placeholder" rows="2" /><div class="ff-tid__row"><Select size="sm" :model-value="policy" :options="POLICY_OPTIONS" @update:model-value="$emit('update:policy', $event)" /><Button variant="primary" :disabled="!modelValue.trim() || disabled" @click="$emit('submit')">Send</Button></div></footer>`
  - `onKey`: Enter (no shift) → preventDefault + emit submit.
- [ ] Add both to agent barrel.
- [ ] Commit: `feat(web): add TaskTimeline + TaskInputDock agent organisms`

### Task 10 — `PlanInspector`

**Files:** create `PlanInspector.vue`; update barrel.

- [ ] Implement:
  - Props: `turn?: AgentTurn | null`.
  - Empty-state branch when no turn focused: `<aside class="ff-pi"><header class="ff-pi__label">INSPECTOR</header><p class="ff-pi__empty">Select a turn to inspect its plan.</p></aside>`
  - Loaded branch: shows skill name, planHash (mono, click-to-copy via `navigator.clipboard.writeText`), cost row (tokens / toolCalls / durationSecEstimate via `MonoNumber`), warnings count, action count. Use uppercase `StatBlock` molecule for the three cost numbers.
  - 320px width, full-height column with internal scroll.
- [ ] Add to barrel.
- [ ] Commit: `feat(web): add PlanInspector agent organism`

### Task 11 — `SkillCard` + `SkillEditorPanel` + `SkillImportPanel`

**Files:** create all three `.vue` files; `SkillCard.spec.ts`; update barrel.

- [ ] Implement `SkillCard.vue`:
  - Props: `skill: AgentSkillItem`, `editable?: boolean`.
  - Emits: `edit`, `delete`.
  - Template: hairline-bordered card with skill name (h3, IBM Plex), `Tag` molecule for `global`/`private`, mono `skillKey`, description paragraph, triggers (small text). When `editable`, footer row with two ghost Buttons (Edit / Delete).
- [ ] Write `SkillCard.spec.ts` (smoke):
  - Renders `skill.name` and `skill.skillKey`.
  - `editable=true` shows Edit + Delete buttons; clicking emits.
  - `editable=false` shows neither.
- [ ] Implement `SkillEditorPanel.vue`:
  - Props: `open: boolean`, `editingKey: string | null`, `initial?: Partial<SkillForm>`, `loading?: boolean`.
  - Emits: `close`, `submit: [SkillForm]`.
  - Uses Modal molecule (`size="lg"`) with custom class to right-anchor (override transform/position in scoped style).
  - Form: `TextField` for name; `TextField` (textarea via attr) for description; `TextField` for triggers; `TextField` for tools (comma-separated); collapsible Advanced JSON section with three textareas (`planTemplate`, `inputsSchema`, `outputsSchema`).
  - Footer: Cancel ghost button + Save primary button (loading state).
  - `submit` payload typed as `SkillForm` (defined locally + re-exported for `useAgentSkills`).
- [ ] Implement `SkillImportPanel.vue`:
  - Props: `loading?: boolean`, `results?: ImportAgentSkillResult[]`.
  - Emits: `submit: [{ mode: ImportAgentSkillMode; jsonText: string }]`.
  - SegmentedControl for `upsert` / `insertOnly`.
  - `FileDrop` accept=".json,application/json"; on `files` event, reads first file as text and populates the textarea.
  - Submit button passes `{ mode, jsonText }` upward.
  - Results section: list of `<div>{{ r.skillKey }} <Tag>{{ r.action }}</Tag></div>` when present.
- [ ] Add all to agent barrel.
- [ ] Run tests — expect PASS.
- [ ] Commit: `feat(web): add Skill organism trio (Card + EditorPanel + ImportPanel)`

### Task 12 — Rewrite `AgentLayout.vue`

**Files:** modify `web/src/pages/agent/AgentLayout.vue`.

- [ ] Replace contents with ≤ 60 line implementation:
  - `<script setup>`: `useRouter`, `useRoute`, computed `currentTab = route.path.startsWith('/agent/skills') ? 'skills' : 'workspace'`, `TABS = [{ value: 'workspace', label: 'WORKSPACE' }, { value: 'skills', label: 'SKILLS' }]`, `function onTab(v) { router.push(v === 'skills' ? '/agent/skills' : '/agent'); }`
  - `<template>`: `<div class="agent-layout"><header class="agent-layout__head"><span class="agent-layout__brand">[ FILEFLASH · AGENT ]</span><SegmentedControl :model-value="currentTab" :options="TABS" @update:model-value="onTab" /></header><router-view v-slot="{ Component }"><Transition name="page-fade" mode="out-in"><component :is="Component" /></Transition></router-view></div>`
  - `<style scoped>`: column flex full-height, head 48px with 1px bottom hairline, mono brand text. Remove radial-gradient hero and rounded card.
- [ ] Run `cd web && bun run build` — TS errors specific to AgentLayout should be gone (was using NSpace/NButton; now using SegmentedControl). AgentWorkspace TS errors will remain pending Task 13.
- [ ] Commit: `feat(web): rewrite AgentLayout with SegmentedControl tabs`

### Task 13 — Rewrite `AgentWorkspace.vue`

**Files:** modify `web/src/pages/agent/workspace/AgentWorkspace.vue`.

- [ ] Replace contents with ≤ 100 line page that:
  - `<script setup>`: imports `useAgentSession` and the four agent organisms. Destructures `{ sessions, activeSession, activeTurns, activeSessionId, policy, taskInput, isSending, createSession, switchSession, deleteSession, sendMessage, runExecute, cancel }` from the composable. Declares local `focusedTurnId = ref<string | null>(null)`.
  - `<template>`: `<div class="aw"><SessionList class="aw__left" :sessions :active-id="activeSessionId" @select="switchSession" @create="createSession" @delete="deleteSession" /><div class="aw__center"><TaskTimeline :turns="activeTurns" :policy :focused-id="focusedTurnId" @execute="(id) => runExecute(turnOf(id))" @cancel="(id) => cancel(turnOf(id))" @focus-turn="focusedTurnId = $event" @hint-pick="(h) => { taskInput = h; sendMessage(); }" /><TaskInputDock v-model="taskInput" v-model:policy="policy" :disabled="isSending" @submit="sendMessage" /></div><PlanInspector class="aw__right" :turn="focusedTurn" /></div>`
  - Local helper `turnOf(id)` and computed `focusedTurn`.
  - `<style scoped>`: grid `grid-template-columns: 240px 1fr 320px`, full height, hairline columns. `@media (max-width: 1280px)` collapses right column into a fixed-position drawer (opens when `focusedTurnId` is set).
- [ ] Run `cd web && bun run build` — expect SUCCESS (the 4 original TS errors are now gone because `pollJob` is replaced by typed pollers in the composable).
- [ ] Commit: `feat(web): rewrite AgentWorkspace as three-column dashboard`

### Task 14 — Rewrite `AgentSkills.vue`

**Files:** modify `web/src/pages/agent/skills/AgentSkills.vue`.

- [ ] Replace contents with ≤ 100 line page that:
  - `<script setup>`: imports `useAgentSkills` + `SkillCard` + `SkillEditorPanel` + `SkillImportPanel` + `SegmentedControl` + `Pagination` + `TextField`. Destructures all composable returns. Local `activeTab = ref<'marketplace' | 'my'>('marketplace')`. Computed `activeData = activeTab === 'marketplace' ? marketplace : mySkills`. `isAdmin` from `useUserStore()`.
  - `<template>`: `<div class="as"><header class="as__head"><TextField v-model="queryText" placeholder="Search skills..." /><SegmentedControl v-model="activeTab" :options="TAB_OPTIONS" /><Button v-if="activeTab === 'my'" variant="primary" @click="openNewSkill">New Skill</Button></header><section class="as__grid"><SkillCard v-for="s in activeData?.items || []" :key="s.skillKey" :skill="s" :editable="activeTab === 'my'" @edit="openEditSkill(s)" @delete="removeSkill(s.skillKey)" /></section><Pagination v-model:page="activePage" :page-size="perPage" :total="activeTotal" /><SkillImportPanel v-if="isAdmin && activeTab === 'marketplace'" :loading="importLoading" :results="importResults" @submit="submitImport" /><SkillEditorPanel :open="editorOpen" :editing-key="editingKey" :initial="form" :loading="editorLoading" @close="closeEditor" @submit="saveSkill" /></div>`
  - Style: column flex, padding `var(--sp-xl)`. Grid `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`, gap `var(--sp-md)`. No radius.
- [ ] Run `cd web && bun run build` — expect SUCCESS.
- [ ] Commit: `feat(web): rewrite AgentSkills with new molecules + organisms`

### Task 15 — `/__dev/library` updates

**Files:** modify `web/src/pages/__dev/Library.vue`.

- [ ] Add to `sections` tuple: `'Molecules · Forms'`, `'Organisms · Agent'` (insert before `'Organisms · Files'` and after `'Organisms · Auth'` respectively).
- [ ] Import the four new molecules and ten new organisms: `import { Modal, Pagination, FileDrop, Select } from '../../components/molecules';` and `import * as Ag from '../../components/organisms/agent';`
- [ ] Add demo state at script bottom: `const dlgOpen = ref(false); const pgPage = ref(2); const selectVal = ref('confirm'); ...` and fixtures for sessions, turns, plan, skill list.
- [ ] Add `<section v-if="activeSection === 'Molecules · Forms'">...</section>` showing each molecule in 1–2 states (Modal: open via button; Pagination: 50 items; FileDrop: idle + drag-hover via class force; Select: closed + open).
- [ ] Add `<section v-if="activeSection === 'Organisms · Agent'">...</section>` showing each organism in isolated states: SessionList (empty + 3 items), TurnEntry (planning / plan-shown / executing / done / failed / canceled — 6 variants), PlanInspector (empty + populated), TaskInputDock (idle + disabled), SkillCard (global + private), SkillEditorPanel (closed; toggle button to open), SkillImportPanel (empty + with results).
- [ ] Quick visual check: `cd web && bun run dev`, open `http://localhost:5173/__dev/library`, navigate to both new sections, verify they render.
- [ ] Commit: `chore(web): register p7 molecules and agent organisms in dev library`

### Task 16 — Acceptance + cleanup

**Files:** none modified; verification only.

- [ ] Run full test suite: `cd web && bun x vitest run` — all green.
- [ ] Run typecheck: `cd web && bun run build` — vue-tsc clean, vite build succeeds.
- [ ] Verify acceptance items from spec §8:
  - [ ] AC1 — `bun run build` passes ✅ (Task 13/14)
  - [ ] AC2 — `bun x vitest run` passes
  - [ ] AC3 — `wc -l web/src/pages/agent/workspace/AgentWorkspace.vue` ≤ 100
  - [ ] AC4 — `wc -l web/src/pages/agent/skills/AgentSkills.vue` ≤ 100
  - [ ] AC5 — `wc -l web/src/pages/agent/AgentLayout.vue` ≤ 60
  - [ ] AC6 — `grep -r "naive-ui" web/src/pages/agent web/src/components/organisms/agent` zero hits
  - [ ] AC7 — `grep -r "from 'naive-ui'" web/src/components/molecules/Modal.vue web/src/components/molecules/Pagination.vue web/src/components/molecules/FileDrop.vue web/src/components/molecules/Select.vue` zero hits
  - [ ] AC8 — `/__dev/library` renders new sections (manual check from Task 15)
  - [ ] AC9 — localStorage roundtrip: open Workspace, create session, send message, refresh, verify session restored, delete a session and verify removal persists
  - [ ] AC10 — Manual policy walkthroughs: planOnly (no execute button), confirm (button present, click executes), autopilot (auto-executes after plan succeeds)
  - [ ] AC11 — DevTools: set `prefers-reduced-motion: reduce`, observe no transitions on turn entry / inspector drawer
- [ ] If all ✅, commit acceptance verification log (if any): `chore(p7): verify acceptance criteria`
- [ ] Update `mem:frontend_redesign_progress` to mark P7 (Agent track) complete (workspace + skills), leaving Admin Dashboard for the rest of P7.

---

## Self-Review

**1. Spec coverage:**
- §3 (Three-column layout) → Tasks 7–10, 13
- §3.2 (AgentSkills single-column) → Tasks 11, 14
- §3.3 (AgentLayout) → Task 12
- §4.1 (4 backfill molecules) → Tasks 1–4
- §4.2 (10 agent organisms) → Tasks 7–11
- §4.3 (2 composables) → Tasks 5, 6
- §5 (TS fix) → Task 5 (pasted verbatim) + Task 13 (delete old code via rewrite)
- §6 (Visual & interaction language) → applied inline across organisms; explicit at Tasks 8, 9, 10 (Spring & Bloom transitions; uppercase tracked labels; mono numbers)
- §7 (`/__dev/library`) → Task 15
- §8 (Acceptance) → Task 16 enumerates all 11 items

**2. Placeholder scan:** No TBD/TODO. All component code blocks reference real props/emits/template skeletons. The TS fix code is pasted verbatim once and referenced by name elsewhere. No "TBD".

**3. Type consistency:** `ChatMessage`, `Session`, `AgentTurn`, `SkillForm` defined in Task 5/6 are the same names referenced by Tasks 7–11. `Bar` atom is referenced in Task 8 — verified exists at `web/src/components/atoms/Bar.vue`. `StatBlock` referenced in Task 10 — verified exists at `web/src/components/molecules/StatBlock.vue`. `IconButton`, `MonoNumber`, `MenuItem`, `SegmentedControl`, `Button`, `TextField` all referenced by name match existing files in `atoms/` or `molecules/`. `relativeTime` helper used in Task 7 — defined inline as a copy of the current `AgentWorkspace.vue` lines 346–354.

**4. Worktree note:** plan was written outside a dedicated worktree (the brainstorming session did not create one). Executor should choose whether to create one before Task 1 — recommended if pursuing subagent-driven execution.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-20-frontend-redesign-p7-agent.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

**Which approach?**
