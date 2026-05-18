# P1 Foundation: Atoms + Molecules + Test Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the atom + molecule layers of the new component library (~26 components total), introduce Vitest + @vue/test-utils test infrastructure with a token-aware mount helper, and ship a dev-only `/__dev/library` route that renders every component in every documented state. P1 produces **no user-visible page changes** — it lays the components that P2+ will consume.

**Architecture:** Components live under `web/src/components/{atoms,molecules}/`. Each component is a single `.vue` file paired with a `.spec.ts` (Vitest + @vue/test-utils + happy-dom). Atoms are indivisible primitives that pull tokens directly from CSS variables. Molecules compose 2-4 atoms (sometimes with internal logic) and accept slots/props for variant behavior. The library viewer at `/__dev/library` is itself written using these components — eating our own dog food. No pages or routes outside `__dev` are modified.

**Tech Stack:** Vue 3, Vite, Bun (`bun@1.2.8`), Vitest, @vue/test-utils, happy-dom

**Spec reference:** `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` § 3 (Atomic Design 组件结构)

**Predecessor:** P0 Foundation. Tokens at `web/src/styles/tokens/*.css` are assumed in place; this plan references them by name.

---

## Pre-flight

- [ ] **Step 0a: Confirm P0 is on develop**

```bash
cd D:/pyprj/fileflash && git log --oneline | grep -E "feat\(styles\):|feat\(web\): preload" | head -5
```

Expected: at least the P0 commits `01fa7af` (color), `dba11c0` (style.css shim) are reachable.

- [ ] **Step 0b: Verify type-check + build still clean**

```bash
cd web && bun run check && bun run build 2>&1 | tail -5
```

Expected: both succeed, `built in <N>s` line.

- [ ] **Step 0c: Confirm token resolution still works in browser (optional but recommended)**

Start dev server, open localhost:5173, in DevTools console:
```js
getComputedStyle(document.documentElement).getPropertyValue('--ac').trim()
```
Expected: `#B6FF3D` or `#5C9E00` depending on resolved theme. Stop server.

---

## Phase A — Test Infrastructure (Tasks 1–4)

### Task 1: Install Vitest + @vue/test-utils + happy-dom

**Files:**
- Modify: `web/package.json`
- Modify: `web/bun.lock`

- [ ] **Step 1: Install devDependencies**

```bash
cd web && bun add -d vitest @vue/test-utils happy-dom @vitest/ui
```

Expected: package.json updated with vitest (≥1.6 or current), @vue/test-utils (≥2.4), happy-dom (≥14), @vitest/ui.

- [ ] **Step 2: Verify versions**

```bash
cd web && bun pm ls vitest @vue/test-utils happy-dom 2>&1 | head -10
```

Expected: all three appear with version numbers.

- [ ] **Step 3: Commit**

```bash
git add web/package.json web/bun.lock
git commit -m "chore(web): add vitest, @vue/test-utils, happy-dom for P1 component tests"
```

---

### Task 2: Configure Vitest

**Files:**
- Modify: `web/vite.config.ts`
- Modify: `web/tsconfig.app.json`
- Create: `web/src/test/setup.ts`
- Modify: `web/package.json` (scripts section)

- [ ] **Step 1: Update `web/vite.config.ts`**

Preserve the existing `loadEnv(...)` call; only append the `test` block. Replace the file with:

```ts
/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const isElectronRuntime = env.VITE_APP_RUNTIME === 'electron';

  return {
    plugins: [vue()],
    base: isElectronRuntime ? './' : '/',
    test: {
      environment: 'happy-dom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      css: true,
    },
  };
});
```

Notes:
- `loadEnv` is preserved so `.env.[mode]` files (used now by `cross-env VITE_APP_RUNTIME=electron`, and possibly later by additional flags) still resolve.
- `test.globals` is intentionally NOT set; every spec in this plan imports `{ describe, it, expect }` explicitly, so global ambient types are unnecessary. This also keeps `tsconfig.app.json`'s `types` resolution untouched (see Step 3).
- `/// <reference types="vitest" />` lets `defineConfig` accept the `test` field without changing the `vite` package import.

- [ ] **Step 2: Create `web/src/test/setup.ts`**

```ts
// web/src/test/setup.ts
// Global setup for Vitest. Imports the full theme.css so all component tests
// have CSS custom properties available via getComputedStyle.

import '../styles/theme.css';
import { beforeEach } from 'vitest';

// Reset HTML data attributes between tests so theme/accent/motion don't leak.
beforeEach(() => {
  const html = document.documentElement;
  html.dataset.theme = 'dark';
  html.dataset.accent = 'lime';
  html.dataset.motion = 'spring';
});
```

- [ ] **Step 3: Update `web/tsconfig.app.json` to include test spec files**

Read the current content first:

```bash
cat web/tsconfig.app.json
```

The only change needed is appending `"src/**/*.spec.ts"` to the existing `include` array. Do **not** add a `compilerOptions.types` entry — setting `types` would override @vue/tsconfig's defaults and stop @types packages (`@types/spark-md5`, `@types/js-cookie`, `@types/qs`, `@types/mockjs`) from being picked up automatically. Tests in this plan use explicit `import { describe, it, expect } from 'vitest'` rather than relying on globals, so no ambient types are required.

Resulting file:

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "src/**/*.spec.ts"]
}
```

- [ ] **Step 4: Add test scripts to `web/package.json`**

In the `scripts` object, add two entries (keep existing scripts intact):

```json
"test": "vitest run",
"test:watch": "vitest",
"test:ui": "vitest --ui"
```

- [ ] **Step 5: Verify scripts wired**

```bash
cd web && bun run test 2>&1 | tail -5
```

Expected: Vitest runs and reports "No test files found" (no atoms yet). That's the desired state for this task — infrastructure works, no failures.

- [ ] **Step 6: Verify type-check still passes**

```bash
cd web && bun run check
```

Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add web/vite.config.ts web/tsconfig.app.json web/src/test/setup.ts web/package.json
git commit -m "chore(web): configure Vitest with happy-dom + theme.css preload"
```

---

### Task 3: Write the mount helper

**Files:**
- Create: `web/src/test/mount.ts`

Tests need a consistent way to mount a component with the theme system active. This helper wraps `@vue/test-utils`'s `mount()` with token-context defaults.

- [ ] **Step 1: Write `web/src/test/mount.ts`**

```ts
// web/src/test/mount.ts
// Token-aware mount helper. Wraps @vue/test-utils so component tests can
// switch theme/accent/motion via options and assert against resolved CSS
// variable values.

import { mount as vtuMount, type MountingOptions } from '@vue/test-utils';
import type { Component } from 'vue';

export interface ThemeContext {
  theme?: 'dark' | 'light';
  accent?: 'lime' | 'amber' | 'oxide';
  motion?: 'spring' | 'tight' | 'reduced';
}

export function mount<TComponent extends Component>(
  component: TComponent,
  options: MountingOptions<unknown> & { context?: ThemeContext } = {},
) {
  const { context, ...rest } = options;
  if (context) {
    const html = document.documentElement;
    if (context.theme) html.dataset.theme = context.theme;
    if (context.accent) html.dataset.accent = context.accent;
    if (context.motion) html.dataset.motion = context.motion;
  }
  return vtuMount(component, rest);
}

/** Read a CSS variable from the document root after mount. */
export function readToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
```

- [ ] **Step 2: Smoke-test the helper itself**

Create `web/src/test/mount.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { defineComponent, h } from 'vue';
import { mount, readToken } from './mount';

describe('test/mount helper', () => {
  const Probe = defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'probe' }, 'probe');
    },
  });

  it('mounts a component', () => {
    const wrapper = mount(Probe);
    expect(wrapper.find('[data-testid="probe"]').text()).toBe('probe');
  });

  it('applies theme context', () => {
    mount(Probe, { context: { theme: 'light', accent: 'amber' } });
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.dataset.accent).toBe('amber');
  });

  it('readToken returns CSS variable values', () => {
    mount(Probe, { context: { theme: 'dark', accent: 'lime' } });
    expect(readToken('--ac')).toBe('#B6FF3D');
    expect(readToken('--surface-base')).toBe('#0E0E10');
  });

  it('resets between tests (verifies setup beforeEach)', () => {
    // The previous test set dark/lime — beforeEach should have reset to defaults.
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.documentElement.dataset.accent).toBe('lime');
  });
});
```

- [ ] **Step 3: Run the test**

```bash
cd web && bun run test
```

Expected: 4 passing tests, no failures.

- [ ] **Step 4: Commit**

```bash
git add web/src/test/mount.ts web/src/test/mount.spec.ts
git commit -m "feat(test): add token-aware mount helper + readToken util"
```

---

### Task 4: Set up component index barrel

**Files:**
- Create: `web/src/components/atoms/index.ts` (empty exports for now — will fill as atoms land)
- Create: `web/src/components/molecules/index.ts`

These barrels are public façades. Pages should only import from `components/atoms` and `components/molecules`, never reach into individual files. Tasks below append exports as components land.

- [ ] **Step 1: Create both files with placeholder content**

`web/src/components/atoms/index.ts`:

```ts
// Public façade for atom components. Entries are added as atoms land in P1.
export {};
```

`web/src/components/molecules/index.ts`:

```ts
// Public façade for molecule components. Entries are added as molecules land in P1.
export {};
```

- [ ] **Step 2: Verify type-check tolerates empty modules**

```bash
cd web && bun run check
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/atoms/index.ts web/src/components/molecules/index.ts
git commit -m "feat(components): scaffold atoms/ and molecules/ barrel exports"
```

---

## Phase B — Atoms (Tasks 5–12)

For each atom: write the spec first (TDD), watch it fail, write the component, watch it pass, commit. Component files are kept under 80 lines.

### Task 5: Text atom

**Files:**
- Create: `web/src/components/atoms/Text.vue`
- Create: `web/src/components/atoms/Text.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

The Text atom is the typographic primitive. Every other atom that contains text uses Text under the hood. It accepts a `variant` prop that maps 1:1 to the type tokens (display / h1 / h2 / body / small / label / data).

- [ ] **Step 1: Write the failing test `Text.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount, readToken } from '../../test/mount';
import Text from './Text.vue';

describe('atoms/Text', () => {
  it('renders default body variant in a <span>', () => {
    const w = mount(Text, { slots: { default: 'hello' } });
    const el = w.find('span');
    expect(el.exists()).toBe(true);
    expect(el.text()).toBe('hello');
  });

  it.each([
    ['display', '--text-display'],
    ['h1', '--text-h1'],
    ['h2', '--text-h2'],
    ['body', '--text-body'],
    ['small', '--text-small'],
    ['label', '--text-label'],
    ['data', '--text-data'],
  ] as const)('variant=%s applies token %s as font-size', (variant, token) => {
    const w = mount(Text, { props: { variant }, slots: { default: 'x' } });
    expect(getComputedStyle(w.element as Element).fontSize).toBe(readToken(token));
  });

  it('label variant uses mono font, uppercase, wide tracking', () => {
    const w = mount(Text, { props: { variant: 'label' }, slots: { default: 'x' } });
    const cs = getComputedStyle(w.element as Element);
    expect(cs.fontFamily).toMatch(/JetBrains Mono/);
    expect(cs.textTransform).toBe('uppercase');
    // `--tracking-wider` is `0.18em`; with `--text-label` = 10px, the
    // computed value resolves to roughly 1.8px. getComputedStyle returns
    // the resolved px value, not the em string, so compare numerically.
    expect(parseFloat(cs.letterSpacing)).toBeGreaterThan(0);
  });

  it('data variant uses mono font with tabular numbers', () => {
    const w = mount(Text, { props: { variant: 'data' }, slots: { default: '0.05' } });
    const cs = getComputedStyle(w.element as Element);
    expect(cs.fontFamily).toMatch(/JetBrains Mono/);
    expect(cs.fontFeatureSettings).toContain('"tnum"');
  });

  it('renders as <h1> when as="h1" is passed', () => {
    const w = mount(Text, { props: { as: 'h1', variant: 'display' }, slots: { default: 'Title' } });
    expect(w.find('h1').exists()).toBe(true);
  });
});
```

- [ ] **Step 2: Run the test, verify it fails**

```bash
cd web && bun run test src/components/atoms/Text.spec.ts
```

Expected: `Cannot find module './Text.vue'`. Test fails.

- [ ] **Step 3: Write `Text.vue`**

```vue
<script setup lang="ts">
export type TextVariant = 'display' | 'h1' | 'h2' | 'body' | 'small' | 'label' | 'data';

withDefaults(defineProps<{
  variant?: TextVariant;
  as?: string;
}>(), {
  variant: 'body',
  as: 'span',
});
</script>

<template>
  <component :is="as" class="ff-text" :class="`ff-text--${variant}`">
    <slot />
  </component>
</template>

<style scoped>
.ff-text {
  font-family: var(--font-sans);
  color: var(--text-primary);
  line-height: var(--leading-normal);
  margin: 0;
}

.ff-text--display { font-size: var(--text-display); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); line-height: var(--leading-tight); }
.ff-text--h1      { font-size: var(--text-h1); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-snug); line-height: var(--leading-snug); }
.ff-text--h2      { font-size: var(--text-h2); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-snug); line-height: var(--leading-snug); }
.ff-text--body    { font-size: var(--text-body); font-weight: var(--weight-regular); }
.ff-text--small   { font-size: var(--text-small); color: var(--text-secondary); }
.ff-text--label   { font-size: var(--text-label); font-family: var(--font-mono); color: var(--text-dim); text-transform: uppercase; letter-spacing: var(--tracking-wider); font-weight: var(--weight-medium); }
.ff-text--data    { font-size: var(--text-data); font-family: var(--font-mono); font-feature-settings: "tnum"; }
</style>
```

- [ ] **Step 4: Run the test, verify it passes**

```bash
cd web && bun run test src/components/atoms/Text.spec.ts
```

Expected: all tests pass.

- [ ] **Step 5: Add to atoms barrel**

Replace `web/src/components/atoms/index.ts` with:

```ts
export { default as Text } from './Text.vue';
export type { TextVariant } from './Text.vue';
```

- [ ] **Step 6: Run type-check**

```bash
cd web && bun run check
```

Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/atoms/Text.vue web/src/components/atoms/Text.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add Text atom with 7 typographic variants"
```

---

### Task 6: MonoNumber + Divider atoms

Two trivial atoms in one task — each is under 30 lines.

**Files:**
- Create: `web/src/components/atoms/MonoNumber.vue` + `.spec.ts`
- Create: `web/src/components/atoms/Divider.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

- [ ] **Step 1: Write `MonoNumber.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount, readToken } from '../../test/mount';
import MonoNumber from './MonoNumber.vue';

describe('atoms/MonoNumber', () => {
  it('renders the value in a span', () => {
    const w = mount(MonoNumber, { props: { value: '2.4 MB' } });
    expect(w.find('span').text()).toBe('2.4 MB');
  });

  it('uses mono font with tabular numbers', () => {
    const w = mount(MonoNumber, { props: { value: '100' } });
    const cs = getComputedStyle(w.element as Element);
    expect(cs.fontFamily).toMatch(/JetBrains Mono/);
    expect(cs.fontFeatureSettings).toContain('"tnum"');
  });

  it('accent variant uses accent color', () => {
    const w = mount(MonoNumber, { props: { value: '100', accent: true } });
    const cs = getComputedStyle(w.element as Element);
    expect(cs.color).toBe('rgb(182, 255, 61)'); // --ac = #B6FF3D
  });
});
```

- [ ] **Step 2: Write `Divider.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount, readToken } from '../../test/mount';
import Divider from './Divider.vue';

describe('atoms/Divider', () => {
  it('renders a horizontal hr by default', () => {
    const w = mount(Divider);
    expect(w.find('hr').exists()).toBe(true);
  });

  it('horizontal: 1px border on top, no margin', () => {
    const w = mount(Divider);
    const cs = getComputedStyle(w.element as Element);
    expect(cs.borderTopWidth).toBe('1px');
    expect(cs.borderTopColor).toBe('rgb(31, 31, 35)'); // --border-subtle dark
  });

  it('vertical variant renders a span with 1px left border', () => {
    const w = mount(Divider, { props: { orientation: 'vertical' } });
    const el = w.find('span');
    expect(el.exists()).toBe(true);
    expect(getComputedStyle(el.element).borderLeftWidth).toBe('1px');
  });
});
```

- [ ] **Step 3: Run both failing tests**

```bash
cd web && bun run test src/components/atoms/MonoNumber.spec.ts src/components/atoms/Divider.spec.ts
```

Expected: both fail (modules not found).

- [ ] **Step 4: Write `MonoNumber.vue`**

```vue
<script setup lang="ts">
defineProps<{
  value: string | number;
  accent?: boolean;
}>();
</script>

<template>
  <span class="ff-num" :class="{ 'ff-num--accent': accent }">{{ value }}</span>
</template>

<style scoped>
.ff-num {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: var(--text-data);
  color: var(--text-secondary);
}
.ff-num--accent { color: var(--ac); }
</style>
```

- [ ] **Step 5: Write `Divider.vue`**

```vue
<script setup lang="ts">
withDefaults(defineProps<{ orientation?: 'horizontal' | 'vertical' }>(), {
  orientation: 'horizontal',
});
</script>

<template>
  <hr v-if="orientation === 'horizontal'" class="ff-divider ff-divider--h" />
  <span v-else class="ff-divider ff-divider--v" aria-hidden="true" />
</template>

<style scoped>
.ff-divider { border: 0; margin: 0; padding: 0; }
.ff-divider--h { border-top: 1px solid var(--border-subtle); width: 100%; }
.ff-divider--v {
  display: inline-block;
  border-left: 1px solid var(--border-subtle);
  width: 0;
  height: 1em;
  vertical-align: middle;
}
</style>
```

- [ ] **Step 6: Run tests, verify pass**

```bash
cd web && bun run test src/components/atoms/MonoNumber.spec.ts src/components/atoms/Divider.spec.ts
```

Expected: all tests pass.

- [ ] **Step 7: Update barrel**

`web/src/components/atoms/index.ts`:

```ts
export { default as Text } from './Text.vue';
export type { TextVariant } from './Text.vue';
export { default as MonoNumber } from './MonoNumber.vue';
export { default as Divider } from './Divider.vue';
```

- [ ] **Step 8: Commit**

```bash
git add web/src/components/atoms/MonoNumber.vue web/src/components/atoms/MonoNumber.spec.ts web/src/components/atoms/Divider.vue web/src/components/atoms/Divider.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add MonoNumber + Divider"
```

---

### Task 7: Bar + Dot atoms

Two micro-atoms for status indicators and progress bars.

**Files:**
- Create: `web/src/components/atoms/Bar.vue` + `.spec.ts`
- Create: `web/src/components/atoms/Dot.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

- [ ] **Step 1: Write `Bar.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Bar from './Bar.vue';

describe('atoms/Bar', () => {
  it('renders a div with the requested width %', () => {
    const w = mount(Bar, { props: { value: 0.64 } });
    expect((w.element as HTMLElement).style.width).toBe('64%');
  });

  it('clamps value to [0, 1]', () => {
    const a = mount(Bar, { props: { value: -0.5 } });
    const b = mount(Bar, { props: { value: 1.5 } });
    expect((a.element as HTMLElement).style.width).toBe('0%');
    expect((b.element as HTMLElement).style.width).toBe('100%');
  });

  it('default tone fills with accent color', () => {
    const w = mount(Bar, { props: { value: 0.5 } });
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe('rgb(182, 255, 61)');
  });

  it('tone=error fills with status-error color', () => {
    const w = mount(Bar, { props: { value: 0.5, tone: 'error' } });
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe('rgb(255, 79, 44)');
  });
});
```

- [ ] **Step 2: Write `Dot.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Dot from './Dot.vue';

describe('atoms/Dot', () => {
  it('renders a 8px square span by default', () => {
    const w = mount(Dot);
    const cs = getComputedStyle(w.element as Element);
    expect(cs.width).toBe('8px');
    expect(cs.height).toBe('8px');
  });

  it('default tone is accent', () => {
    const w = mount(Dot);
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe('rgb(182, 255, 61)');
  });

  it.each([
    ['success', 'rgb(74, 222, 128)'],
    ['warning', 'rgb(255, 180, 0)'],
    ['error', 'rgb(255, 79, 44)'],
    ['info', 'rgb(96, 165, 250)'],
  ] as const)('tone=%s renders with status %s', (tone, rgb) => {
    const w = mount(Dot, { props: { tone } });
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe(rgb);
  });
});
```

- [ ] **Step 3: Run failing tests**

```bash
cd web && bun run test src/components/atoms/Bar.spec.ts src/components/atoms/Dot.spec.ts
```

Expected: fail (modules not found).

- [ ] **Step 4: Write `Bar.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  value: number;
  tone?: 'accent' | 'success' | 'warning' | 'error' | 'info';
}>(), { tone: 'accent' });

const widthPct = computed(() => {
  const clamped = Math.max(0, Math.min(1, props.value));
  return `${clamped * 100}%`;
});
</script>

<template>
  <div class="ff-bar" :class="`ff-bar--${tone}`" :style="{ width: widthPct }" />
</template>

<style scoped>
.ff-bar { height: 4px; background: var(--ac); }
.ff-bar--success { background: var(--status-success); }
.ff-bar--warning { background: var(--status-warning); }
.ff-bar--error   { background: var(--status-error); }
.ff-bar--info    { background: var(--status-info); }
</style>
```

- [ ] **Step 5: Write `Dot.vue`**

```vue
<script setup lang="ts">
withDefaults(defineProps<{
  tone?: 'accent' | 'success' | 'warning' | 'error' | 'info';
}>(), { tone: 'accent' });
</script>

<template>
  <span class="ff-dot" :class="`ff-dot--${tone}`" aria-hidden="true" />
</template>

<style scoped>
.ff-dot { display: inline-block; width: 8px; height: 8px; background: var(--ac); }
.ff-dot--success { background: var(--status-success); }
.ff-dot--warning { background: var(--status-warning); }
.ff-dot--error   { background: var(--status-error); }
.ff-dot--info    { background: var(--status-info); }
</style>
```

- [ ] **Step 6: Run tests, verify pass**

```bash
cd web && bun run test src/components/atoms/Bar.spec.ts src/components/atoms/Dot.spec.ts
```

Expected: all pass.

- [ ] **Step 7: Update barrel**

Append to `web/src/components/atoms/index.ts`:

```ts
export { default as Bar } from './Bar.vue';
export { default as Dot } from './Dot.vue';
```

- [ ] **Step 8: Commit**

```bash
git add web/src/components/atoms/Bar.vue web/src/components/atoms/Bar.spec.ts web/src/components/atoms/Dot.vue web/src/components/atoms/Dot.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add Bar + Dot status indicators"
```

---

### Task 8: Icon atom + registry

The Icon atom takes a `name` and `size` prop and renders an inline SVG from a typed registry. The registry initially holds the icons the legacy app uses (chevron, search, theme toggle, menu hamburger, x close, check, upload, download, more, eye, eye-off, plus, trash, folder, file, share).

**Files:**
- Create: `web/src/components/atoms/icons.ts`
- Create: `web/src/components/atoms/Icon.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

- [ ] **Step 1: Write `icons.ts` (the SVG path registry)**

```ts
// web/src/components/atoms/icons.ts
// SVG path-data registry. Each entry is the `d` attribute of a single <path>.
// Icons are designed on a 24×24 grid with stroke-width 2, line-cap round,
// line-join round. Source: hand-curated minimalist set, matches B aesthetic.

export const ICONS = {
  chevronDown: 'M6 9l6 6 6-6',
  chevronRight: 'M9 6l6 6-6 6',
  chevronLeft: 'M15 6l-6 6 6 6',
  chevronUp: 'M6 15l6-6 6 6',
  search: 'M11 4a7 7 0 1 0 4.9 12l4.6 4.6 1.4-1.4-4.6-4.6A7 7 0 0 0 11 4',
  menu: 'M3 6h18M3 12h18M3 18h18',
  close: 'M6 6l12 12M18 6L6 18',
  check: 'M4 12l5 5L20 6',
  upload: 'M12 4v12M6 10l6-6 6 6M4 20h16',
  download: 'M12 20V8M6 14l6 6 6-6M4 4h16',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  eyeOff: 'M3 3l18 18M10.5 10.5a3 3 0 0 0 4 4M9 5.5C9.9 5.2 10.9 5 12 5c6.5 0 10 7 10 7-.5 1-1.4 2.3-2.7 3.4M5.3 8.4C3.5 9.9 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.3-1',
  plus: 'M12 5v14M5 12h14',
  trash: 'M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6',
  folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6',
  share: 'M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13',
  sun: 'M12 5V2m0 20v-3m7-7h3M2 12h3m11.3 4.3l2.1 2.1M5.6 5.6l2.1 2.1m8.6 0l2.1-2.1m-12.8 12.8l2.1-2.1M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8',
  moon: 'M21 13a8 8 0 1 1-10-10a7 7 0 0 0 10 10',
} as const;

export type IconName = keyof typeof ICONS;
```

- [ ] **Step 2: Write `Icon.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Icon from './Icon.vue';

describe('atoms/Icon', () => {
  it('renders an <svg> with the requested icon path', () => {
    const w = mount(Icon, { props: { name: 'search' } });
    const svg = w.find('svg');
    expect(svg.exists()).toBe(true);
    const path = svg.find('path');
    expect(path.exists()).toBe(true);
    expect(path.attributes('d')).toContain('M11 4a7 7 0 1 0');
  });

  it('default size is 18px', () => {
    const w = mount(Icon, { props: { name: 'check' } });
    expect(w.find('svg').attributes('width')).toBe('18');
    expect(w.find('svg').attributes('height')).toBe('18');
  });

  it('respects size prop', () => {
    const w = mount(Icon, { props: { name: 'check', size: 24 } });
    expect(w.find('svg').attributes('width')).toBe('24');
    expect(w.find('svg').attributes('height')).toBe('24');
  });

  it('uses currentColor for stroke', () => {
    const w = mount(Icon, { props: { name: 'check' } });
    expect(w.find('svg').attributes('stroke')).toBe('currentColor');
  });

  it('decorative by default (aria-hidden true)', () => {
    const w = mount(Icon, { props: { name: 'check' } });
    expect(w.find('svg').attributes('aria-hidden')).toBe('true');
  });

  it('label prop exposes accessibility', () => {
    const w = mount(Icon, { props: { name: 'check', label: 'Done' } });
    const svg = w.find('svg');
    expect(svg.attributes('aria-hidden')).toBeUndefined();
    expect(svg.attributes('role')).toBe('img');
    expect(svg.attributes('aria-label')).toBe('Done');
  });
});
```

- [ ] **Step 3: Run failing test**

```bash
cd web && bun run test src/components/atoms/Icon.spec.ts
```

Expected: fail (Icon.vue missing).

- [ ] **Step 4: Write `Icon.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { ICONS, type IconName } from './icons';

const props = withDefaults(defineProps<{
  name: IconName;
  size?: number;
  label?: string;
}>(), { size: 18 });

const path = computed(() => ICONS[props.name]);
const a11y = computed(() =>
  props.label
    ? { role: 'img', 'aria-label': props.label }
    : { 'aria-hidden': 'true' },
);
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    v-bind="a11y"
  >
    <path :d="path" />
  </svg>
</template>
```

- [ ] **Step 5: Run test, verify pass**

```bash
cd web && bun run test src/components/atoms/Icon.spec.ts
```

Expected: all pass.

- [ ] **Step 6: Update barrel**

Append:

```ts
export { default as Icon } from './Icon.vue';
export type { IconName } from './icons';
```

- [ ] **Step 7: Commit**

```bash
git add web/src/components/atoms/Icon.vue web/src/components/atoms/Icon.spec.ts web/src/components/atoms/icons.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add Icon atom + 19-entry SVG registry"
```

---

### Task 9: Spinner + Surface atoms

**Files:**
- Create: `web/src/components/atoms/Spinner.vue` + `.spec.ts`
- Create: `web/src/components/atoms/Surface.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

- [ ] **Step 1: Write `Spinner.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Spinner from './Spinner.vue';

describe('atoms/Spinner', () => {
  it('renders a div with role=status', () => {
    const w = mount(Spinner);
    expect(w.attributes('role')).toBe('status');
  });

  it('default label is "Loading"', () => {
    const w = mount(Spinner);
    expect(w.find('.ff-visually-hidden').text()).toBe('Loading');
  });

  it('custom label is read by screen readers', () => {
    const w = mount(Spinner, { props: { label: 'Uploading file' } });
    expect(w.find('.ff-visually-hidden').text()).toBe('Uploading file');
  });

  it('renders 3 scan bars for the B-style indicator', () => {
    const w = mount(Spinner);
    expect(w.findAll('.ff-spinner-bar')).toHaveLength(3);
  });
});
```

- [ ] **Step 2: Write `Surface.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Surface from './Surface.vue';

describe('atoms/Surface', () => {
  it('renders a div with base surface background by default', () => {
    const w = mount(Surface, { slots: { default: 'x' } });
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe('rgb(14, 14, 16)');
  });

  it('elevation=raised uses raised surface', () => {
    const w = mount(Surface, { props: { elevation: 'raised' }, slots: { default: 'x' } });
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe('rgb(21, 21, 26)');
  });

  it('elevation=inset uses inset surface', () => {
    const w = mount(Surface, { props: { elevation: 'inset' }, slots: { default: 'x' } });
    expect(getComputedStyle(w.element as Element).backgroundColor).toBe('rgb(10, 10, 12)');
  });

  it('bordered=true adds 1px hairline border', () => {
    const w = mount(Surface, { props: { bordered: true }, slots: { default: 'x' } });
    expect(getComputedStyle(w.element as Element).borderTopWidth).toBe('1px');
  });
});
```

- [ ] **Step 3: Run failing tests**

```bash
cd web && bun run test src/components/atoms/Spinner.spec.ts src/components/atoms/Surface.spec.ts
```

Expected: fail.

- [ ] **Step 4: Write `Spinner.vue`**

```vue
<script setup lang="ts">
withDefaults(defineProps<{ label?: string }>(), { label: 'Loading' });
</script>

<template>
  <div class="ff-spinner" role="status">
    <span class="ff-spinner-bar" />
    <span class="ff-spinner-bar" />
    <span class="ff-spinner-bar" />
    <span class="ff-visually-hidden">{{ label }}</span>
  </div>
</template>

<style scoped>
.ff-spinner { display: inline-flex; gap: 3px; align-items: center; height: 12px; }
.ff-spinner-bar {
  display: block; width: 2px; height: 100%;
  background: var(--ac);
  animation: ff-scan 0.9s linear infinite;
}
.ff-spinner-bar:nth-child(2) { animation-delay: 0.15s; }
.ff-spinner-bar:nth-child(3) { animation-delay: 0.3s; }
@keyframes ff-scan {
  0%, 100% { transform: scaleY(0.3); opacity: 0.4; }
  50%      { transform: scaleY(1); opacity: 1; }
}
.ff-visually-hidden {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
[data-motion="reduced"] .ff-spinner-bar { animation: none; opacity: 0.7; }
</style>
```

- [ ] **Step 5: Write `Surface.vue`**

```vue
<script setup lang="ts">
withDefaults(defineProps<{
  elevation?: 'base' | 'raised' | 'inset';
  bordered?: boolean;
}>(), { elevation: 'base', bordered: false });
</script>

<template>
  <div class="ff-surface" :class="[
    `ff-surface--${elevation}`,
    bordered && 'ff-surface--bordered',
  ]">
    <slot />
  </div>
</template>

<style scoped>
.ff-surface--base   { background: var(--surface-base); }
.ff-surface--raised { background: var(--surface-raised); }
.ff-surface--inset  { background: var(--surface-inset); }
.ff-surface--bordered { border: 1px solid var(--border-default); }
</style>
```

- [ ] **Step 6: Tests pass**

```bash
cd web && bun run test src/components/atoms/Spinner.spec.ts src/components/atoms/Surface.spec.ts
```

- [ ] **Step 7: Update barrel + commit**

Append to barrel:
```ts
export { default as Spinner } from './Spinner.vue';
export { default as Surface } from './Surface.vue';
```

```bash
git add web/src/components/atoms/Spinner.vue web/src/components/atoms/Spinner.spec.ts web/src/components/atoms/Surface.vue web/src/components/atoms/Surface.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add Spinner (scan-line loader) + Surface (themed bg container)"
```

---

### Task 10: Input + Checkbox atoms

Form atoms. Input is the raw text input wrapper (TextField molecule will add label + helper). Checkbox is a fully styled custom checkbox.

**Files:**
- Create: `web/src/components/atoms/Input.vue` + `.spec.ts`
- Create: `web/src/components/atoms/Checkbox.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

- [ ] **Step 1: Write `Input.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Input from './Input.vue';

describe('atoms/Input', () => {
  it('renders an <input> with type=text by default', () => {
    const w = mount(Input);
    const input = w.find('input');
    expect(input.exists()).toBe(true);
    expect(input.attributes('type')).toBe('text');
  });

  it('binds modelValue via v-model', async () => {
    const w = mount(Input, { props: { modelValue: 'hello' } });
    expect((w.find('input').element as HTMLInputElement).value).toBe('hello');
    await w.find('input').setValue('world');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['world']);
  });

  it('disabled prop disables the input', () => {
    const w = mount(Input, { props: { disabled: true } });
    expect(w.find('input').attributes('disabled')).toBeDefined();
  });

  it('invalid prop applies error border', () => {
    const w = mount(Input, { props: { invalid: true } });
    expect(getComputedStyle(w.find('input').element).borderColor).toBe('rgb(255, 79, 44)');
  });

  it('passes through type prop (e.g. password)', () => {
    const w = mount(Input, { props: { type: 'password' } });
    expect(w.find('input').attributes('type')).toBe('password');
  });
});
```

- [ ] **Step 2: Write `Checkbox.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Checkbox from './Checkbox.vue';

describe('atoms/Checkbox', () => {
  it('renders a hidden native checkbox + custom box', () => {
    const w = mount(Checkbox, { props: { modelValue: false } });
    expect(w.find('input[type="checkbox"]').exists()).toBe(true);
    expect(w.find('.ff-checkbox-box').exists()).toBe(true);
  });

  it('toggles modelValue on click', async () => {
    const w = mount(Checkbox, { props: { modelValue: false } });
    await w.find('input').setValue(true);
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true]);
  });

  it('checked variant shows the check icon', () => {
    const w = mount(Checkbox, { props: { modelValue: true } });
    expect(w.find('.ff-checkbox--checked').exists()).toBe(true);
  });

  it('disabled prop blocks interaction', () => {
    const w = mount(Checkbox, { props: { modelValue: false, disabled: true } });
    expect(w.find('input').attributes('disabled')).toBeDefined();
  });
});
```

- [ ] **Step 3: Run failing tests**

```bash
cd web && bun run test src/components/atoms/Input.spec.ts src/components/atoms/Checkbox.spec.ts
```

- [ ] **Step 4: Write `Input.vue`**

```vue
<script setup lang="ts">
withDefaults(defineProps<{
  modelValue?: string;
  type?: string;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
}>(), { type: 'text' });

defineEmits<{ 'update:modelValue': [value: string] }>();
</script>

<template>
  <input
    class="ff-input"
    :class="{ 'ff-input--invalid': invalid }"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<style scoped>
.ff-input {
  width: 100%;
  height: 32px;
  padding: 0 12px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-body);
  outline: none;
  transition: border-color var(--mo-duration-fast) var(--mo-easing),
              background-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-input:focus { border-color: var(--ac); background: var(--surface-raised); }
.ff-input:disabled { opacity: 0.5; cursor: not-allowed; }
.ff-input--invalid { border-color: var(--status-error); }
.ff-input--invalid:focus { border-color: var(--status-error); }
.ff-input::placeholder { color: var(--text-dim); }
</style>
```

- [ ] **Step 5: Write `Checkbox.vue`**

```vue
<script setup lang="ts">
import { useId } from 'vue';
import Icon from './Icon.vue';

withDefaults(defineProps<{
  modelValue: boolean;
  disabled?: boolean;
  label?: string;
}>(), {});

defineEmits<{ 'update:modelValue': [value: boolean] }>();

// Vue 3.5+ provides a stable, SSR-safe id generator.
const id = useId();
</script>

<template>
  <label class="ff-checkbox" :class="{ 'ff-checkbox--checked': modelValue, 'ff-checkbox--disabled': disabled }" :for="id">
    <input
      :id="id"
      type="checkbox"
      class="ff-checkbox-native"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="ff-checkbox-box" aria-hidden="true">
      <Icon v-if="modelValue" name="check" :size="12" />
    </span>
    <span v-if="label" class="ff-checkbox-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.ff-checkbox { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
.ff-checkbox--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-checkbox-native { position: absolute; opacity: 0; pointer-events: none; }
.ff-checkbox-box {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--ac-fg);
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-checkbox--checked .ff-checkbox-box { background: var(--ac); border-color: var(--ac); }
.ff-checkbox-label { font-size: var(--text-body); color: var(--text-secondary); }
</style>
```

- [ ] **Step 6: Tests pass + commit**

```bash
cd web && bun run test src/components/atoms/Input.spec.ts src/components/atoms/Checkbox.spec.ts
```

Append to barrel:
```ts
export { default as Input } from './Input.vue';
export { default as Checkbox } from './Checkbox.vue';
```

```bash
git add web/src/components/atoms/Input.vue web/src/components/atoms/Input.spec.ts web/src/components/atoms/Checkbox.vue web/src/components/atoms/Checkbox.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add Input + Checkbox form primitives"
```

---

### Task 11: Radio + Toggle atoms

**Files:**
- Create: `web/src/components/atoms/Radio.vue` + `.spec.ts`
- Create: `web/src/components/atoms/Toggle.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

- [ ] **Step 1: Write `Radio.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Radio from './Radio.vue';

describe('atoms/Radio', () => {
  it('renders a hidden native radio + custom dot', () => {
    const w = mount(Radio, { props: { modelValue: 'a', value: 'a', name: 'g' } });
    expect(w.find('input[type="radio"]').exists()).toBe(true);
    expect(w.find('.ff-radio-dot').exists()).toBe(true);
  });

  it('selected when modelValue === value', () => {
    const w = mount(Radio, { props: { modelValue: 'a', value: 'a', name: 'g' } });
    expect(w.find('.ff-radio--checked').exists()).toBe(true);
  });

  it('emits update on change', async () => {
    const w = mount(Radio, { props: { modelValue: 'b', value: 'a', name: 'g' } });
    await w.find('input').setValue(true);
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['a']);
  });
});
```

- [ ] **Step 2: Write `Toggle.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Toggle from './Toggle.vue';

describe('atoms/Toggle', () => {
  it('renders a button with role=switch', () => {
    const w = mount(Toggle, { props: { modelValue: false } });
    expect(w.find('button').attributes('role')).toBe('switch');
  });

  it('aria-checked reflects modelValue', () => {
    const a = mount(Toggle, { props: { modelValue: false } });
    const b = mount(Toggle, { props: { modelValue: true } });
    expect(a.find('button').attributes('aria-checked')).toBe('false');
    expect(b.find('button').attributes('aria-checked')).toBe('true');
  });

  it('emits update on click', async () => {
    const w = mount(Toggle, { props: { modelValue: false } });
    await w.find('button').trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true]);
  });

  it('disabled prop blocks interaction', async () => {
    const w = mount(Toggle, { props: { modelValue: false, disabled: true } });
    await w.find('button').trigger('click');
    expect(w.emitted('update:modelValue')).toBeUndefined();
  });
});
```

- [ ] **Step 3: Failing tests**

```bash
cd web && bun run test src/components/atoms/Radio.spec.ts src/components/atoms/Toggle.spec.ts
```

- [ ] **Step 4: Write `Radio.vue`**

```vue
<script setup lang="ts">
import { computed, useId } from 'vue';

const props = defineProps<{
  modelValue: string | number;
  value: string | number;
  name: string;
  disabled?: boolean;
  label?: string;
}>();

defineEmits<{ 'update:modelValue': [value: string | number] }>();

const id = useId();
const checked = computed(() => props.modelValue === props.value);
</script>

<template>
  <label class="ff-radio" :class="{ 'ff-radio--checked': checked, 'ff-radio--disabled': disabled }" :for="id">
    <input
      :id="id"
      type="radio"
      class="ff-radio-native"
      :name="name"
      :value="value"
      :checked="checked"
      :disabled="disabled"
      @change="$emit('update:modelValue', value)"
    />
    <span class="ff-radio-dot" aria-hidden="true" />
    <span v-if="label" class="ff-radio-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.ff-radio { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
.ff-radio--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-radio-native { position: absolute; opacity: 0; pointer-events: none; }
.ff-radio-dot {
  position: relative;
  width: 16px; height: 16px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: 50%;
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-radio-dot::after {
  content: ''; position: absolute; inset: 3px;
  background: var(--ac); border-radius: 50%;
  transform: scale(0);
  transition: transform var(--mo-duration-fast) var(--mo-easing);
}
.ff-radio--checked .ff-radio-dot { border-color: var(--ac); }
.ff-radio--checked .ff-radio-dot::after { transform: scale(1); }
.ff-radio-label { font-size: var(--text-body); color: var(--text-secondary); }
</style>
```

- [ ] **Step 5: Write `Toggle.vue`**

```vue
<script setup lang="ts">
const props = defineProps<{ modelValue: boolean; disabled?: boolean; label?: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();

function onClick() {
  if (!props.disabled) emit('update:modelValue', !props.modelValue);
}
</script>

<template>
  <button
    type="button"
    role="switch"
    class="ff-toggle"
    :class="{ 'ff-toggle--on': modelValue, 'ff-toggle--disabled': disabled }"
    :aria-checked="modelValue ? 'true' : 'false'"
    :disabled="disabled"
    @click="onClick"
  >
    <span class="ff-toggle-thumb" aria-hidden="true" />
    <span v-if="label" class="ff-toggle-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.ff-toggle {
  display: inline-flex; align-items: center; gap: 8px;
  background: transparent; border: 0; padding: 0;
  cursor: pointer; color: inherit;
}
.ff-toggle::before {
  content: ''; display: inline-block;
  width: 32px; height: 18px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  transition: background-color var(--mo-duration-fast) var(--mo-easing),
              border-color var(--mo-duration-fast) var(--mo-easing);
  position: relative;
}
.ff-toggle-thumb {
  position: absolute; top: 50%; left: 3px;
  width: 12px; height: 12px;
  background: var(--text-dim);
  border-radius: 50%;
  transform: translateY(-50%);
  transition: left var(--mo-duration-fast) var(--mo-easing),
              background-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-toggle--on::before { background: var(--ac); border-color: var(--ac); }
.ff-toggle--on .ff-toggle-thumb { left: 17px; background: var(--ac-fg); }
.ff-toggle--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-toggle-label { font-size: var(--text-body); color: var(--text-secondary); }
</style>
```

- [ ] **Step 6: Pass + commit**

```bash
cd web && bun run test src/components/atoms/Radio.spec.ts src/components/atoms/Toggle.spec.ts
```

Append to barrel:
```ts
export { default as Radio } from './Radio.vue';
export { default as Toggle } from './Toggle.vue';
```

```bash
git add web/src/components/atoms/Radio.vue web/src/components/atoms/Radio.spec.ts web/src/components/atoms/Toggle.vue web/src/components/atoms/Toggle.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add Radio + Toggle form primitives"
```

---

### Task 12: KeyHint atom + final atom verification

**Files:**
- Create: `web/src/components/atoms/KeyHint.vue` + `.spec.ts`
- Modify: `web/src/components/atoms/index.ts`

The KeyHint renders a keyboard shortcut chip (e.g., `⌘K`, `Shift+Enter`).

- [ ] **Step 1: Write `KeyHint.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import KeyHint from './KeyHint.vue';

describe('atoms/KeyHint', () => {
  it('renders each key in a <kbd> wrapper', () => {
    const w = mount(KeyHint, { props: { keys: ['Ctrl', 'K'] } });
    expect(w.findAll('kbd')).toHaveLength(2);
    expect(w.findAll('kbd')[0].text()).toBe('Ctrl');
    expect(w.findAll('kbd')[1].text()).toBe('K');
  });

  it('uses mono font', () => {
    const w = mount(KeyHint, { props: { keys: ['Esc'] } });
    expect(getComputedStyle(w.find('kbd').element).fontFamily).toMatch(/JetBrains Mono/);
  });

  it('renders a + separator between keys', () => {
    const w = mount(KeyHint, { props: { keys: ['Shift', 'Enter'] } });
    expect(w.text()).toContain('+');
  });
});
```

- [ ] **Step 2: Fail → write `KeyHint.vue`**

```vue
<script setup lang="ts">
defineProps<{ keys: string[] }>();
</script>

<template>
  <span class="ff-keyhint" aria-hidden="true">
    <template v-for="(k, i) in keys" :key="i">
      <kbd>{{ k }}</kbd>
      <span v-if="i < keys.length - 1" class="ff-keyhint-sep">+</span>
    </template>
  </span>
</template>

<style scoped>
.ff-keyhint { display: inline-flex; align-items: center; gap: 4px; }
.ff-keyhint kbd {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  color: var(--text-secondary);
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  line-height: 1.4;
}
.ff-keyhint-sep { color: var(--text-dim); font-size: var(--text-label); }
</style>
```

- [ ] **Step 3: Test + commit**

```bash
cd web && bun run test src/components/atoms/KeyHint.spec.ts
```

Append to barrel + run full atom test sweep:

```bash
cd web && bun run test src/components/atoms/
```

Expected: all atom tests pass (Text 5, MonoNumber 3, Divider 3, Bar 4, Dot 6, Icon 6, Spinner 4, Surface 4, Input 5, Checkbox 4, Radio 3, Toggle 4, KeyHint 3 = 54 tests minimum).

```bash
git add web/src/components/atoms/KeyHint.vue web/src/components/atoms/KeyHint.spec.ts web/src/components/atoms/index.ts
git commit -m "feat(atoms): add KeyHint atom + complete atoms layer (~13 components)"
```

**Natural release point: atoms layer is now complete.** Phase B is done.

---

## Phase C — Molecules (Tasks 13–22)

Molecules import from `atoms/`. Same TDD rhythm as atoms.

### Task 13: Button + IconButton molecules

**Files:**
- Create: `web/src/components/molecules/Button.vue` + `.spec.ts`
- Create: `web/src/components/molecules/IconButton.vue` + `.spec.ts`
- Modify: `web/src/components/molecules/index.ts`

- [ ] **Step 1: Write `Button.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Button from './Button.vue';

describe('molecules/Button', () => {
  it('renders a button with the slot text', () => {
    const w = mount(Button, { slots: { default: 'Click me' } });
    expect(w.find('button').text()).toBe('Click me');
  });

  it('default variant=primary uses accent bg', () => {
    const w = mount(Button, { slots: { default: 'x' } });
    expect(getComputedStyle(w.find('button').element).backgroundColor).toBe('rgb(182, 255, 61)');
  });

  it('variant=ghost has transparent bg', () => {
    const w = mount(Button, { props: { variant: 'ghost' }, slots: { default: 'x' } });
    expect(getComputedStyle(w.find('button').element).backgroundColor).toBe('rgba(0, 0, 0, 0)');
  });

  it('variant=danger uses error color', () => {
    const w = mount(Button, { props: { variant: 'danger' }, slots: { default: 'x' } });
    expect(getComputedStyle(w.find('button').element).backgroundColor).toBe('rgb(255, 79, 44)');
  });

  it('size=sm reduces height', () => {
    const lg = mount(Button, { props: { size: 'md' }, slots: { default: 'x' } });
    const sm = mount(Button, { props: { size: 'sm' }, slots: { default: 'x' } });
    const lgH = parseInt(getComputedStyle(lg.find('button').element).height, 10);
    const smH = parseInt(getComputedStyle(sm.find('button').element).height, 10);
    expect(smH).toBeLessThan(lgH);
  });

  it('emits click when not disabled', async () => {
    const w = mount(Button, { slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });

  it('does not emit click when disabled', async () => {
    const w = mount(Button, { props: { disabled: true }, slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toBeUndefined();
  });

  it('icon prop renders Icon atom before slot', () => {
    const w = mount(Button, { props: { icon: 'upload' }, slots: { default: 'Upload' } });
    expect(w.find('svg').exists()).toBe(true);
  });

  it('loading prop renders Spinner and disables', () => {
    const w = mount(Button, { props: { loading: true }, slots: { default: 'x' } });
    expect(w.find('[role="status"]').exists()).toBe(true);
    expect(w.find('button').attributes('disabled')).toBeDefined();
  });
});
```

- [ ] **Step 2: Write `IconButton.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import IconButton from './IconButton.vue';

describe('molecules/IconButton', () => {
  it('renders a square button with only an icon', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'Close' } });
    expect(w.find('svg').exists()).toBe(true);
    expect(w.find('button').text()).toBe('');
  });

  it('label is required for a11y (used as aria-label)', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'Close dialog' } });
    expect(w.find('button').attributes('aria-label')).toBe('Close dialog');
  });

  it('emits click', async () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });

  it('ghost variant is transparent', () => {
    const w = mount(IconButton, { props: { icon: 'close', label: 'x', variant: 'ghost' } });
    expect(getComputedStyle(w.find('button').element).backgroundColor).toBe('rgba(0, 0, 0, 0)');
  });
});
```

- [ ] **Step 3: Failing tests**

```bash
cd web && bun run test src/components/molecules/Button.spec.ts src/components/molecules/IconButton.spec.ts
```

- [ ] **Step 4: Write `Button.vue`**

```vue
<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import Spinner from '../atoms/Spinner.vue';
import type { IconName } from '../atoms/icons';

withDefaults(defineProps<{
  variant?: 'primary' | 'ghost' | 'danger';
  size?: 'sm' | 'md';
  icon?: IconName;
  loading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
}>(), { variant: 'primary', size: 'md', type: 'button' });

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    :type="type"
    class="ff-btn"
    :class="[`ff-btn--${variant}`, `ff-btn--${size}`, { 'ff-btn--loading': loading }]"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <Spinner v-if="loading" :label="'Loading'" />
    <Icon v-else-if="icon" :name="icon" :size="size === 'sm' ? 14 : 16" />
    <span class="ff-btn-label"><slot /></span>
  </button>
</template>

<style scoped>
.ff-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  cursor: pointer;
  transition: transform var(--mo-duration-fast) var(--mo-easing),
              filter var(--mo-duration-fast) var(--mo-easing),
              background-color var(--mo-duration-fast) var(--mo-easing),
              border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-btn:active:not(:disabled) { transform: scale(var(--mo-press-scale)); }
.ff-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ff-btn--md { height: 32px; }
.ff-btn--sm { height: 24px; padding: 0 10px; font-size: 9px; }

.ff-btn--primary { background: var(--ac); color: var(--ac-fg); }
.ff-btn--primary:hover:not(:disabled) { filter: brightness(1.1); box-shadow: var(--mo-hover-bloom); }

.ff-btn--ghost { background: transparent; color: var(--text-secondary); border-color: var(--border-default); }
.ff-btn--ghost:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }

.ff-btn--danger { background: var(--status-error); color: #fff; }
.ff-btn--danger:hover:not(:disabled) { filter: brightness(1.1); }
</style>
```

- [ ] **Step 5: Write `IconButton.vue`**

```vue
<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import type { IconName } from '../atoms/icons';

withDefaults(defineProps<{
  icon: IconName;
  label: string;
  variant?: 'primary' | 'ghost';
  size?: 'sm' | 'md';
  disabled?: boolean;
}>(), { variant: 'ghost', size: 'md' });

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="ff-iconbtn"
    :class="[`ff-iconbtn--${variant}`, `ff-iconbtn--${size}`]"
    :aria-label="label"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <Icon :name="icon" :size="size === 'sm' ? 14 : 18" />
  </button>
</template>

<style scoped>
.ff-iconbtn {
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-iconbtn:disabled { opacity: 0.5; cursor: not-allowed; }
.ff-iconbtn:active:not(:disabled) { transform: scale(var(--mo-press-scale)); }
.ff-iconbtn--md { width: 32px; height: 32px; }
.ff-iconbtn--sm { width: 24px; height: 24px; }
.ff-iconbtn--ghost:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }
.ff-iconbtn--primary { background: var(--ac); color: var(--ac-fg); }
.ff-iconbtn--primary:hover:not(:disabled) { filter: brightness(1.1); }
</style>
```

- [ ] **Step 6: Tests pass + commit**

```bash
cd web && bun run test src/components/molecules/Button.spec.ts src/components/molecules/IconButton.spec.ts
```

Update `web/src/components/molecules/index.ts`:

```ts
export { default as Button } from './Button.vue';
export { default as IconButton } from './IconButton.vue';
```

```bash
git add web/src/components/molecules/Button.vue web/src/components/molecules/Button.spec.ts web/src/components/molecules/IconButton.vue web/src/components/molecules/IconButton.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add Button + IconButton"
```

---

### Task 14: TextField + SearchField

**Files:**
- Create: `web/src/components/molecules/TextField.vue` + `.spec.ts`
- Create: `web/src/components/molecules/SearchField.vue` + `.spec.ts`
- Modify: `web/src/components/molecules/index.ts`

- [ ] **Step 1: Write `TextField.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import TextField from './TextField.vue';

describe('molecules/TextField', () => {
  it('renders a label tied to an input', () => {
    const w = mount(TextField, { props: { modelValue: '', label: 'Username' } });
    const labelEl = w.find('label');
    const inputEl = w.find('input');
    expect(labelEl.text()).toContain('Username');
    expect(labelEl.attributes('for')).toBe(inputEl.attributes('id'));
  });

  it('binds modelValue', async () => {
    const w = mount(TextField, { props: { modelValue: 'a', label: 'L' } });
    expect((w.find('input').element as HTMLInputElement).value).toBe('a');
    await w.find('input').setValue('b');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['b']);
  });

  it('error prop renders error message + applies invalid styling', () => {
    const w = mount(TextField, { props: { modelValue: '', label: 'L', error: 'Required' } });
    expect(w.text()).toContain('Required');
    expect(getComputedStyle(w.find('input').element).borderColor).toBe('rgb(255, 79, 44)');
  });

  it('hint prop renders helper text below', () => {
    const w = mount(TextField, { props: { modelValue: '', label: 'L', hint: 'Min 8 chars' } });
    expect(w.text()).toContain('Min 8 chars');
  });

  it('type=password forwards to input', () => {
    const w = mount(TextField, { props: { modelValue: '', label: 'L', type: 'password' } });
    expect(w.find('input').attributes('type')).toBe('password');
  });
});
```

- [ ] **Step 2: Write `SearchField.spec.ts`**

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import SearchField from './SearchField.vue';

describe('molecules/SearchField', () => {
  it('renders an input with a search icon prefix', () => {
    const w = mount(SearchField, { props: { modelValue: '' } });
    expect(w.find('input').exists()).toBe(true);
    expect(w.find('svg').exists()).toBe(true);
  });

  it('renders clear icon button when value is non-empty', () => {
    const w = mount(SearchField, { props: { modelValue: 'q' } });
    expect(w.find('button[aria-label="Clear"]').exists()).toBe(true);
  });

  it('does not render clear button when empty', () => {
    const w = mount(SearchField, { props: { modelValue: '' } });
    expect(w.find('button[aria-label="Clear"]').exists()).toBe(false);
  });

  it('clicking clear emits update with empty string', async () => {
    const w = mount(SearchField, { props: { modelValue: 'q' } });
    await w.find('button[aria-label="Clear"]').trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['']);
  });
});
```

- [ ] **Step 3: Failing tests, then write components**

`TextField.vue`:

```vue
<script setup lang="ts">
import { useId } from 'vue';
import Input from '../atoms/Input.vue';
import Text from '../atoms/Text.vue';

defineProps<{
  modelValue: string;
  label: string;
  type?: string;
  placeholder?: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
}>();

defineEmits<{ 'update:modelValue': [value: string] }>();

const id = useId();
</script>

<template>
  <label class="ff-textfield" :for="id">
    <Text variant="label">{{ label }}</Text>
    <Input
      :id="id"
      :model-value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :invalid="!!error"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <Text v-if="error" variant="small" class="ff-textfield-error">{{ error }}</Text>
    <Text v-else-if="hint" variant="small" class="ff-textfield-hint">{{ hint }}</Text>
  </label>
</template>

<style scoped>
.ff-textfield { display: flex; flex-direction: column; gap: 6px; }
.ff-textfield-error { color: var(--status-error) !important; }
.ff-textfield-hint  { color: var(--text-dim) !important; }
</style>
```

`SearchField.vue`:

```vue
<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import IconButton from './IconButton.vue';

defineProps<{ modelValue: string; placeholder?: string; disabled?: boolean }>();

defineEmits<{ 'update:modelValue': [value: string] }>();
</script>

<template>
  <div class="ff-searchfield">
    <Icon name="search" :size="16" class="ff-searchfield-icon" />
    <input
      class="ff-searchfield-input"
      type="text"
      :value="modelValue"
      :placeholder="placeholder ?? 'Search…'"
      :disabled="disabled"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <IconButton
      v-if="modelValue"
      icon="close"
      label="Clear"
      size="sm"
      class="ff-searchfield-clear"
      @click="$emit('update:modelValue', '')"
    />
  </div>
</template>

<style scoped>
.ff-searchfield {
  display: inline-flex; align-items: center; gap: 8px;
  height: 32px; padding: 0 12px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  transition: border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-searchfield:focus-within { border-color: var(--ac); }
.ff-searchfield-icon { color: var(--text-dim); flex-shrink: 0; }
.ff-searchfield-input {
  flex: 1;
  background: transparent; border: 0; outline: none;
  font-family: var(--font-sans); font-size: var(--text-body);
  color: var(--text-primary);
}
.ff-searchfield-input::placeholder { color: var(--text-dim); }
</style>
```

- [ ] **Step 4: Tests pass + commit**

```bash
cd web && bun run test src/components/molecules/TextField.spec.ts src/components/molecules/SearchField.spec.ts
```

Append to barrel + commit:

```ts
export { default as TextField } from './TextField.vue';
export { default as SearchField } from './SearchField.vue';
```

```bash
git add web/src/components/molecules/TextField.vue web/src/components/molecules/TextField.spec.ts web/src/components/molecules/SearchField.vue web/src/components/molecules/SearchField.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add TextField + SearchField"
```

---

### Task 15: Badge + Tag

**Files:**
- Create: `web/src/components/molecules/Badge.vue` + `.spec.ts`
- Create: `web/src/components/molecules/Tag.vue` + `.spec.ts`
- Modify: `web/src/components/molecules/index.ts`

- [ ] **Step 1: Write tests**

`Badge.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Badge from './Badge.vue';

describe('molecules/Badge', () => {
  it('renders the slot text with default success tone', () => {
    const w = mount(Badge, { slots: { default: 'LIVE' } });
    expect(w.text()).toBe('LIVE');
    expect(getComputedStyle(w.element as Element).borderColor).toMatch(/rgba?\(74, 222, 128/);
  });

  it.each([
    ['success', /rgba?\(74, 222, 128/],
    ['warning', /rgba?\(255, 180, 0/],
    ['error', /rgba?\(255, 79, 44/],
    ['info', /rgba?\(96, 165, 250/],
    ['accent', /rgba?\(182, 255, 61/],
  ] as const)('tone=%s', (tone, regex) => {
    const w = mount(Badge, { props: { tone }, slots: { default: 'x' } });
    expect(getComputedStyle(w.element as Element).borderColor).toMatch(regex);
  });

  it('uppercase mono small text', () => {
    const w = mount(Badge, { slots: { default: 'x' } });
    const cs = getComputedStyle(w.element as Element);
    expect(cs.fontFamily).toMatch(/JetBrains Mono/);
    expect(cs.textTransform).toBe('uppercase');
  });
});
```

`Tag.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Tag from './Tag.vue';

describe('molecules/Tag', () => {
  it('renders the slot text', () => {
    const w = mount(Tag, { slots: { default: 'design' } });
    expect(w.text()).toBe('design');
  });

  it('removable=true shows a close button and emits remove', async () => {
    const w = mount(Tag, { props: { removable: true }, slots: { default: 'design' } });
    expect(w.find('button[aria-label="Remove"]').exists()).toBe(true);
    await w.find('button[aria-label="Remove"]').trigger('click');
    expect(w.emitted('remove')).toHaveLength(1);
  });

  it('not removable by default', () => {
    const w = mount(Tag, { slots: { default: 'design' } });
    expect(w.find('button').exists()).toBe(false);
  });
});
```

- [ ] **Step 2: Components**

`Badge.vue`:

```vue
<script setup lang="ts">
withDefaults(defineProps<{
  tone?: 'success' | 'warning' | 'error' | 'info' | 'accent';
}>(), { tone: 'success' });
</script>

<template>
  <span class="ff-badge" :class="`ff-badge--${tone}`">
    <slot />
  </span>
</template>

<style scoped>
.ff-badge {
  display: inline-flex; align-items: center;
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
}
.ff-badge--success { color: var(--status-success); border-color: rgba(var(--status-success-rgb), 0.45); background: rgba(var(--status-success-rgb), 0.12); }
.ff-badge--warning { color: var(--status-warning); border-color: rgba(var(--status-warning-rgb), 0.45); background: rgba(var(--status-warning-rgb), 0.12); }
.ff-badge--error   { color: var(--status-error);   border-color: rgba(var(--status-error-rgb), 0.45);   background: rgba(var(--status-error-rgb), 0.12); }
.ff-badge--info    { color: var(--status-info);    border-color: rgba(var(--status-info-rgb), 0.45);    background: rgba(var(--status-info-rgb), 0.12); }
.ff-badge--accent  { color: var(--ac);              border-color: rgba(var(--ac-rgb), 0.45);              background: rgba(var(--ac-rgb), 0.12); }
</style>
```

`Tag.vue`:

```vue
<script setup lang="ts">
import IconButton from './IconButton.vue';

defineProps<{ removable?: boolean }>();
defineEmits<{ remove: [] }>();
</script>

<template>
  <span class="ff-tag">
    <slot />
    <IconButton
      v-if="removable"
      icon="close"
      label="Remove"
      size="sm"
      class="ff-tag-remove"
      @click="$emit('remove')"
    />
  </span>
</template>

<style scoped>
.ff-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px;
  font-family: var(--font-sans);
  font-size: var(--text-small);
  color: var(--text-secondary);
  background: var(--surface-inset);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}
.ff-tag-remove { width: 16px; height: 16px; }
</style>
```

- [ ] **Step 3: Tests pass + commit**

```bash
cd web && bun run test src/components/molecules/Badge.spec.ts src/components/molecules/Tag.spec.ts
```

```ts
export { default as Badge } from './Badge.vue';
export { default as Tag } from './Tag.vue';
```

```bash
git add web/src/components/molecules/Badge.vue web/src/components/molecules/Badge.spec.ts web/src/components/molecules/Tag.vue web/src/components/molecules/Tag.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add Badge (semantic status pill) + Tag"
```

---

### Task 16: StatBlock + ProgressBar

**Files:**
- Create: `web/src/components/molecules/StatBlock.vue` + `.spec.ts`
- Create: `web/src/components/molecules/ProgressBar.vue` + `.spec.ts`

- [ ] **Step 1: Tests**

`StatBlock.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import StatBlock from './StatBlock.vue';

describe('molecules/StatBlock', () => {
  it('renders label + value', () => {
    const w = mount(StatBlock, { props: { label: 'TOTAL', value: '2,486' } });
    expect(w.text()).toContain('TOTAL');
    expect(w.text()).toContain('2,486');
  });

  it('value uses MonoNumber (mono font)', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100' } });
    const numEl = w.element.querySelector('.ff-statblock-value');
    expect(getComputedStyle(numEl!).fontFamily).toMatch(/JetBrains Mono/);
  });

  it('delta positive shows up arrow + accent color', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100', delta: 5 } });
    expect(w.text()).toMatch(/\+5|↑/);
  });

  it('delta negative shows down arrow + error color', () => {
    const w = mount(StatBlock, { props: { label: 'L', value: '100', delta: -3 } });
    expect(w.text()).toMatch(/-3|↓/);
  });
});
```

`ProgressBar.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import ProgressBar from './ProgressBar.vue';

describe('molecules/ProgressBar', () => {
  it('renders the Bar atom + percent value', () => {
    const w = mount(ProgressBar, { props: { value: 0.64 } });
    expect(w.text()).toContain('64%');
    expect(w.element.querySelector('.ff-bar')).toBeTruthy();
  });

  it('label slot is shown above the bar', () => {
    const w = mount(ProgressBar, { props: { value: 0.5 }, slots: { label: 'Uploading' } });
    expect(w.text()).toContain('Uploading');
  });

  it('tone=error passes through to Bar', () => {
    const w = mount(ProgressBar, { props: { value: 0.5, tone: 'error' } });
    const bar = w.element.querySelector('.ff-bar');
    expect(getComputedStyle(bar as Element).backgroundColor).toBe('rgb(255, 79, 44)');
  });
});
```

- [ ] **Step 2: Components**

`StatBlock.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue';
import Text from '../atoms/Text.vue';
import MonoNumber from '../atoms/MonoNumber.vue';

const props = defineProps<{
  label: string;
  value: string | number;
  delta?: number;
}>();

const deltaTone = computed(() => {
  if (!props.delta) return 'neutral';
  return props.delta > 0 ? 'up' : 'down';
});
</script>

<template>
  <div class="ff-statblock">
    <Text variant="label">{{ label }}</Text>
    <MonoNumber :value="value" accent class="ff-statblock-value" />
    <span v-if="delta != null" class="ff-statblock-delta" :class="`ff-statblock-delta--${deltaTone}`">
      <span v-if="delta > 0">↑</span><span v-else>↓</span> {{ Math.abs(delta) }}
    </span>
  </div>
</template>

<style scoped>
.ff-statblock { display: flex; flex-direction: column; gap: 4px; }
.ff-statblock-value { font-size: var(--text-data-big) !important; }
.ff-statblock-delta {
  font-family: var(--font-mono); font-size: var(--text-small);
}
.ff-statblock-delta--up   { color: var(--status-success); }
.ff-statblock-delta--down { color: var(--status-error); }
</style>
```

`ProgressBar.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue';
import Text from '../atoms/Text.vue';
import Bar from '../atoms/Bar.vue';

const props = withDefaults(defineProps<{
  value: number;
  tone?: 'accent' | 'success' | 'warning' | 'error' | 'info';
}>(), { tone: 'accent' });

const pct = computed(() => Math.round(Math.max(0, Math.min(1, props.value)) * 100));
</script>

<template>
  <div class="ff-progress">
    <div class="ff-progress-header">
      <slot name="label">
        <Text variant="label">PROGRESS</Text>
      </slot>
      <Text variant="data">{{ pct }}%</Text>
    </div>
    <div class="ff-progress-track">
      <Bar :value="value" :tone="tone" />
    </div>
  </div>
</template>

<style scoped>
.ff-progress { display: flex; flex-direction: column; gap: 6px; }
.ff-progress-header { display: flex; justify-content: space-between; align-items: baseline; }
.ff-progress-track { background: var(--surface-inset); }
</style>
```

- [ ] **Step 3: Tests + commit**

```bash
cd web && bun run test src/components/molecules/StatBlock.spec.ts src/components/molecules/ProgressBar.spec.ts
```

Append to barrel + commit:

```ts
export { default as StatBlock } from './StatBlock.vue';
export { default as ProgressBar } from './ProgressBar.vue';
```

```bash
git add web/src/components/molecules/StatBlock.vue web/src/components/molecules/StatBlock.spec.ts web/src/components/molecules/ProgressBar.vue web/src/components/molecules/ProgressBar.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add StatBlock + ProgressBar"
```

---

### Task 17: BreadcrumbItem + MenuItem

**Files:**
- Create: `web/src/components/molecules/BreadcrumbItem.vue` + `.spec.ts`
- Create: `web/src/components/molecules/MenuItem.vue` + `.spec.ts`

- [ ] **Step 1: Tests**

`BreadcrumbItem.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import BreadcrumbItem from './BreadcrumbItem.vue';

describe('molecules/BreadcrumbItem', () => {
  it('renders the slot as a link when href provided', () => {
    const w = mount(BreadcrumbItem, { props: { href: '/files' }, slots: { default: 'Files' } });
    expect(w.find('a').attributes('href')).toBe('/files');
    expect(w.text()).toContain('Files');
  });

  it('renders as a span when no href (last item)', () => {
    const w = mount(BreadcrumbItem, { slots: { default: 'Current' } });
    expect(w.find('a').exists()).toBe(false);
    expect(w.text()).toContain('Current');
  });

  it('shows a chevron when not last', () => {
    const w = mount(BreadcrumbItem, { props: { href: '/files' }, slots: { default: 'Files' } });
    expect(w.find('svg').exists()).toBe(true);
  });

  it('does not show chevron when last (no href)', () => {
    const w = mount(BreadcrumbItem, { slots: { default: 'Current' } });
    expect(w.find('svg').exists()).toBe(false);
  });
});
```

`MenuItem.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import MenuItem from './MenuItem.vue';

describe('molecules/MenuItem', () => {
  it('renders a button with slot label', () => {
    const w = mount(MenuItem, { slots: { default: 'Settings' } });
    expect(w.find('button').text()).toContain('Settings');
  });

  it('icon prop renders icon before label', () => {
    const w = mount(MenuItem, { props: { icon: 'trash' }, slots: { default: 'Delete' } });
    expect(w.find('svg').exists()).toBe(true);
  });

  it('keyHint prop renders KeyHint atom on the right', () => {
    const w = mount(MenuItem, { props: { keyHint: ['Ctrl', 'K'] }, slots: { default: 'Search' } });
    expect(w.findAll('kbd').length).toBeGreaterThanOrEqual(2);
  });

  it('danger variant uses error color', () => {
    const w = mount(MenuItem, { props: { variant: 'danger' }, slots: { default: 'Delete' } });
    expect(getComputedStyle(w.find('button').element).color).toBe('rgb(255, 79, 44)');
  });

  it('emits click', async () => {
    const w = mount(MenuItem, { slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Components**

`BreadcrumbItem.vue`:

```vue
<script setup lang="ts">
import Icon from '../atoms/Icon.vue';

defineProps<{ href?: string }>();
</script>

<template>
  <span class="ff-breadcrumb-item">
    <a v-if="href" :href="href" class="ff-breadcrumb-link"><slot /></a>
    <span v-else class="ff-breadcrumb-current"><slot /></span>
    <Icon v-if="href" name="chevronRight" :size="12" class="ff-breadcrumb-sep" />
  </span>
</template>

<style scoped>
.ff-breadcrumb-item { display: inline-flex; align-items: center; gap: 6px; }
.ff-breadcrumb-link { color: var(--text-secondary); text-decoration: none; font-size: var(--text-body); transition: color var(--mo-duration-fast) var(--mo-easing); }
.ff-breadcrumb-link:hover { color: var(--text-primary); }
.ff-breadcrumb-current { color: var(--text-primary); font-size: var(--text-body); font-weight: var(--weight-medium); }
.ff-breadcrumb-sep { color: var(--text-dim); }
</style>
```

`MenuItem.vue`:

```vue
<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import KeyHint from '../atoms/KeyHint.vue';
import type { IconName } from '../atoms/icons';

withDefaults(defineProps<{
  icon?: IconName;
  variant?: 'default' | 'danger';
  keyHint?: string[];
  disabled?: boolean;
}>(), { variant: 'default' });

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="ff-menuitem"
    :class="[`ff-menuitem--${variant}`, { 'ff-menuitem--disabled': disabled }]"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <Icon v-if="icon" :name="icon" :size="14" />
    <span class="ff-menuitem-label"><slot /></span>
    <KeyHint v-if="keyHint" :keys="keyHint" class="ff-menuitem-hint" />
  </button>
</template>

<style scoped>
.ff-menuitem {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 6px 10px;
  background: transparent; border: 0;
  color: var(--text-secondary);
  font-family: var(--font-sans); font-size: var(--text-body);
  text-align: left; cursor: pointer;
  transition: background-color var(--mo-duration-fast) var(--mo-easing), color var(--mo-duration-fast) var(--mo-easing);
}
.ff-menuitem:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }
.ff-menuitem--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-menuitem--danger { color: var(--status-error); }
.ff-menuitem-label { flex: 1; }
.ff-menuitem-hint { margin-left: auto; }
</style>
```

- [ ] **Step 3: Tests + commit**

```bash
cd web && bun run test src/components/molecules/BreadcrumbItem.spec.ts src/components/molecules/MenuItem.spec.ts
```

```ts
export { default as BreadcrumbItem } from './BreadcrumbItem.vue';
export { default as MenuItem } from './MenuItem.vue';
```

```bash
git add web/src/components/molecules/BreadcrumbItem.vue web/src/components/molecules/BreadcrumbItem.spec.ts web/src/components/molecules/MenuItem.vue web/src/components/molecules/MenuItem.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add BreadcrumbItem + MenuItem"
```

---

### Task 18: Tab + SegmentedControl

**Files:**
- Create: `web/src/components/molecules/Tab.vue` + `.spec.ts`
- Create: `web/src/components/molecules/SegmentedControl.vue` + `.spec.ts`

- [ ] **Step 1: Tests**

`Tab.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Tab from './Tab.vue';

describe('molecules/Tab', () => {
  it('renders a button with slot label', () => {
    const w = mount(Tab, { props: { active: false }, slots: { default: 'Files' } });
    expect(w.find('button').text()).toBe('Files');
  });

  it('active=true applies accent underline / color', () => {
    const w = mount(Tab, { props: { active: true }, slots: { default: 'x' } });
    expect(w.classes()).toContain('ff-tab--active');
  });

  it('emits click', async () => {
    const w = mount(Tab, { props: { active: false }, slots: { default: 'x' } });
    await w.find('button').trigger('click');
    expect(w.emitted('click')).toHaveLength(1);
  });
});
```

`SegmentedControl.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import SegmentedControl from './SegmentedControl.vue';

describe('molecules/SegmentedControl', () => {
  it('renders one button per option', () => {
    const opts = [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }, { value: 'c', label: 'C' }];
    const w = mount(SegmentedControl, { props: { modelValue: 'a', options: opts } });
    expect(w.findAll('button')).toHaveLength(3);
  });

  it('marks the active option with aria-pressed=true', () => {
    const opts = [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }];
    const w = mount(SegmentedControl, { props: { modelValue: 'b', options: opts } });
    const buttons = w.findAll('button');
    expect(buttons[0].attributes('aria-pressed')).toBe('false');
    expect(buttons[1].attributes('aria-pressed')).toBe('true');
  });

  it('clicking emits update with that option value', async () => {
    const opts = [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }];
    const w = mount(SegmentedControl, { props: { modelValue: 'a', options: opts } });
    await w.findAll('button')[1].trigger('click');
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['b']);
  });

  it('disabled prop disables all buttons', () => {
    const opts = [{ value: 'a', label: 'A' }];
    const w = mount(SegmentedControl, { props: { modelValue: 'a', options: opts, disabled: true } });
    expect(w.find('button').attributes('disabled')).toBeDefined();
  });
});
```

- [ ] **Step 2: Components**

`Tab.vue`:

```vue
<script setup lang="ts">
defineProps<{ active: boolean }>();
defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="ff-tab"
    :class="{ 'ff-tab--active': active }"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.ff-tab {
  display: inline-flex; align-items: center;
  padding: 8px 14px;
  background: transparent; border: 0;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-family: var(--font-sans); font-size: var(--text-body); font-weight: var(--weight-medium);
  cursor: pointer;
  transition: color var(--mo-duration-fast) var(--mo-easing), border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-tab:hover { color: var(--text-primary); }
.ff-tab--active { color: var(--ac); border-bottom-color: var(--ac); }
</style>
```

`SegmentedControl.vue`:

```vue
<script setup lang="ts">
export type Option<T> = { value: T; label: string };

defineProps<{
  modelValue: string | number;
  options: Option<string | number>[];
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
      :class="{ 'ff-segmented-option--active': opt.value === modelValue }"
      :aria-pressed="opt.value === modelValue ? 'true' : 'false'"
      :disabled="disabled"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
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
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-segmented-option:hover:not(:disabled) { color: var(--text-primary); }
.ff-segmented-option--active { background: var(--ac); color: var(--ac-fg); }
.ff-segmented-option:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
```

- [ ] **Step 3: Tests + commit**

```bash
cd web && bun run test src/components/molecules/Tab.spec.ts src/components/molecules/SegmentedControl.spec.ts
```

```ts
export { default as Tab } from './Tab.vue';
export { default as SegmentedControl } from './SegmentedControl.vue';
export type { Option as SegmentedOption } from './SegmentedControl.vue';
```

```bash
git add web/src/components/molecules/Tab.vue web/src/components/molecules/Tab.spec.ts web/src/components/molecules/SegmentedControl.vue web/src/components/molecules/SegmentedControl.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add Tab + SegmentedControl"
```

---

### Task 19: Toolbar + Avatar

**Files:**
- Create: `web/src/components/molecules/Toolbar.vue` + `.spec.ts`
- Create: `web/src/components/molecules/Avatar.vue` + `.spec.ts`

- [ ] **Step 1: Tests**

`Toolbar.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Toolbar from './Toolbar.vue';

describe('molecules/Toolbar', () => {
  it('renders a horizontal group containing slot content', () => {
    const w = mount(Toolbar, { slots: { default: '<button>a</button><button>b</button>' } });
    expect(w.findAll('button')).toHaveLength(2);
  });

  it('renders a divider via Divider atom between groups when split slot is used', () => {
    const w = mount(Toolbar, {
      slots: {
        default: '<button>a</button>',
        split: '<button>b</button>',
      },
    });
    expect(w.find('.ff-divider').exists()).toBe(true);
  });

  it('default role is toolbar', () => {
    const w = mount(Toolbar, { slots: { default: 'x' } });
    expect(w.attributes('role')).toBe('toolbar');
  });
});
```

`Avatar.spec.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { mount } from '../../test/mount';
import Avatar from './Avatar.vue';

describe('molecules/Avatar', () => {
  it('renders an img when src provided', () => {
    const w = mount(Avatar, { props: { src: '/x.png', name: 'Alice' } });
    expect(w.find('img').exists()).toBe(true);
    expect(w.find('img').attributes('alt')).toBe('Alice');
  });

  it('renders initials fallback when no src', () => {
    const w = mount(Avatar, { props: { name: 'Alice Wong' } });
    expect(w.text()).toBe('AW');
  });

  it('falls back to ? when name is empty', () => {
    const w = mount(Avatar, { props: { name: '' } });
    expect(w.text()).toBe('?');
  });

  it('size=sm reduces dimensions', () => {
    const md = mount(Avatar, { props: { name: 'A', size: 'md' } });
    const sm = mount(Avatar, { props: { name: 'A', size: 'sm' } });
    expect(parseInt(getComputedStyle(md.element as Element).width, 10))
      .toBeGreaterThan(parseInt(getComputedStyle(sm.element as Element).width, 10));
  });
});
```

- [ ] **Step 2: Components**

`Toolbar.vue`:

```vue
<script setup lang="ts">
import Divider from '../atoms/Divider.vue';
import { computed, useSlots } from 'vue';

const slots = useSlots();
const hasSplit = computed(() => !!slots.split);
</script>

<template>
  <div class="ff-toolbar" role="toolbar">
    <div class="ff-toolbar-group">
      <slot />
    </div>
    <Divider v-if="hasSplit" orientation="vertical" class="ff-toolbar-divider" />
    <div v-if="hasSplit" class="ff-toolbar-group">
      <slot name="split" />
    </div>
  </div>
</template>

<style scoped>
.ff-toolbar { display: inline-flex; align-items: center; gap: 4px; }
.ff-toolbar-group { display: inline-flex; align-items: center; gap: 4px; }
.ff-toolbar-divider { height: 20px; margin: 0 6px; }
</style>
```

`Avatar.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  name: string;
  src?: string;
  size?: 'sm' | 'md';
}>(), { size: 'md' });

const initials = computed(() => {
  const parts = props.name.trim().split(/\s+/);
  if (!parts[0]) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
});
</script>

<template>
  <span class="ff-avatar" :class="`ff-avatar--${size}`">
    <img v-if="src" :src="src" :alt="name" />
    <span v-else class="ff-avatar-initials">{{ initials }}</span>
  </span>
</template>

<style scoped>
.ff-avatar {
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  border: 1px solid var(--border-subtle);
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}
.ff-avatar--md { width: 28px; height: 28px; font-size: 11px; }
.ff-avatar--sm { width: 20px; height: 20px; font-size: 9px; }
.ff-avatar img { width: 100%; height: 100%; object-fit: cover; }
</style>
```

- [ ] **Step 3: Tests + commit**

```bash
cd web && bun run test src/components/molecules/Toolbar.spec.ts src/components/molecules/Avatar.spec.ts
```

```ts
export { default as Toolbar } from './Toolbar.vue';
export { default as Avatar } from './Avatar.vue';
```

```bash
git add web/src/components/molecules/Toolbar.vue web/src/components/molecules/Toolbar.spec.ts web/src/components/molecules/Avatar.vue web/src/components/molecules/Avatar.spec.ts web/src/components/molecules/index.ts
git commit -m "feat(molecules): add Toolbar + Avatar"
```

---

### Task 20: Full molecule test sweep

**Files:** none modified.

- [ ] **Step 1: Run all molecule tests**

```bash
cd web && bun run test src/components/molecules/
```

Expected: all molecule tests pass (Button 9, IconButton 4, TextField 5, SearchField 4, Badge 7, Tag 3, StatBlock 4, ProgressBar 3, BreadcrumbItem 4, MenuItem 5, Tab 3, SegmentedControl 4, Toolbar 3, Avatar 4 = ~62 tests minimum).

- [ ] **Step 2: Run the full test suite**

```bash
cd web && bun run test
```

Expected: all atom + molecule + mount-helper tests pass (~120 tests total). No failures, no skipped suites.

- [ ] **Step 3: Verify type-check still clean**

```bash
cd web && bun run check
```

Expected: exit 0.

No commit — this is verification only.

**Natural release point: atom + molecule layers complete.** Phase C done.

---

## Phase D — Dev Library Route (Tasks 21–23)

The library page renders every atom and molecule in every documented state. It's only available in dev (Vite's `import.meta.env.DEV`), guarded by both router and a route-level check.

### Task 21: Library page scaffolding

**Files:**
- Create: `web/src/pages/__dev/Library.vue`
- Create: `web/src/pages/__dev/index.ts` (lazy import)
- Modify: `web/src/router/routes.ts` (add the dev-only route)

- [ ] **Step 1: Create `web/src/pages/__dev/Library.vue`**

This is a long file (~250 lines) but mostly markup. Goal: render every component in a navigable index. We use only molecules + atoms — no Naive UI.

```vue
<script setup lang="ts">
import { ref } from 'vue';
import * as A from '../../components/atoms';
import * as M from '../../components/molecules';

const sections = [
  'Tokens', 'Atoms · Text', 'Atoms · Numbers', 'Atoms · Visual', 'Atoms · Form',
  'Molecules · Action', 'Molecules · Input', 'Molecules · Display', 'Molecules · Nav',
] as const;
type Section = typeof sections[number];

const activeSection = ref<Section>('Tokens');

// Theme controls
const theme = ref<'dark' | 'light'>(document.documentElement.dataset.theme as 'dark' | 'light' ?? 'dark');
const accent = ref<'lime' | 'amber' | 'oxide'>(document.documentElement.dataset.accent as 'lime' | 'amber' | 'oxide' ?? 'lime');
const motion = ref<'spring' | 'tight' | 'reduced'>(document.documentElement.dataset.motion as 'spring' | 'tight' | 'reduced' ?? 'spring');

function setTheme(v: typeof theme.value)   { theme.value = v;   document.documentElement.dataset.theme  = v; }
function setAccent(v: typeof accent.value) { accent.value = v; document.documentElement.dataset.accent = v; }
function setMotion(v: typeof motion.value) { motion.value = v; document.documentElement.dataset.motion = v; }

// Demo state
const text = ref('');
const checked = ref(false);
const radio = ref('a');
const toggled = ref(false);
const tab = ref(0);
</script>

<template>
  <div class="lib">
    <aside class="lib-side">
      <A.Text variant="display">FF Library</A.Text>
      <A.Text variant="small">Atoms + Molecules · dev only</A.Text>

      <div class="lib-controls">
        <A.Text variant="label">Theme</A.Text>
        <M.SegmentedControl :model-value="theme" :options="[{value:'dark',label:'Dark'},{value:'light',label:'Light'}]" @update:model-value="setTheme($event as any)" />
        <A.Text variant="label">Accent</A.Text>
        <M.SegmentedControl :model-value="accent" :options="[{value:'lime',label:'Lime'},{value:'amber',label:'Amber'},{value:'oxide',label:'Oxide'}]" @update:model-value="setAccent($event as any)" />
        <A.Text variant="label">Motion</A.Text>
        <M.SegmentedControl :model-value="motion" :options="[{value:'spring',label:'Spring'},{value:'tight',label:'Tight'},{value:'reduced',label:'Reduced'}]" @update:model-value="setMotion($event as any)" />
      </div>

      <nav class="lib-nav">
        <M.MenuItem v-for="s in sections" :key="s" @click="activeSection = s">{{ s }}</M.MenuItem>
      </nav>
    </aside>

    <main class="lib-main">
      <section v-if="activeSection === 'Tokens'">
        <A.Text as="h1" variant="h1">Design Tokens</A.Text>
        <p>See <code>web/src/styles/tokens/*.css</code> for the full table. The controls in the sidebar live-switch them.</p>
        <div class="swatches">
          <div class="sw" v-for="t in ['--surface-base','--surface-raised','--surface-inset','--border-default','--text-primary','--text-secondary','--ac']" :key="t">
            <span class="sw-block" :style="{ background: `var(${t})` }" />
            <A.Text variant="data">{{ t }}</A.Text>
          </div>
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Text'">
        <A.Text as="h1" variant="h1">Atoms · Text</A.Text>
        <div class="grid">
          <div><A.Text variant="display">Display 32</A.Text></div>
          <div><A.Text as="h1" variant="h1">H1 22</A.Text></div>
          <div><A.Text as="h2" variant="h2">H2 17</A.Text></div>
          <div><A.Text variant="body">Body 13.5 — 中英混排测试 / Mixed CJK + Latin</A.Text></div>
          <div><A.Text variant="small">Small 12</A.Text></div>
          <div><A.Text variant="label">LABEL · 10</A.Text></div>
          <div><A.Text variant="data">DATA · 0.05 MB · 12:00</A.Text></div>
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Numbers'">
        <A.Text as="h1" variant="h1">Atoms · Numbers</A.Text>
        <div class="grid">
          <A.MonoNumber value="2.4 MB" />
          <A.MonoNumber value="100%" accent />
          <A.KeyHint :keys="['Ctrl', 'K']" />
          <A.KeyHint :keys="['Esc']" />
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Visual'">
        <A.Text as="h1" variant="h1">Atoms · Visual</A.Text>
        <div class="grid">
          <A.Bar :value="0.64" />
          <A.Bar :value="0.4" tone="warning" />
          <A.Bar :value="0.9" tone="error" />
          <div class="dots"><A.Dot /><A.Dot tone="success" /><A.Dot tone="warning" /><A.Dot tone="error" /><A.Dot tone="info" /></div>
          <A.Divider />
          <A.Spinner label="Loading library" />
          <A.Surface elevation="raised" bordered style="padding:12px;">Surface raised+bordered</A.Surface>
        </div>
        <div class="grid">
          <A.Icon name="search" /><A.Icon name="upload" /><A.Icon name="folder" /><A.Icon name="trash" /><A.Icon name="moon" /><A.Icon name="sun" />
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Form'">
        <A.Text as="h1" variant="h1">Atoms · Form</A.Text>
        <div class="grid">
          <A.Input v-model="text" placeholder="Type…" />
          <A.Input v-model="text" placeholder="Disabled" disabled />
          <A.Input v-model="text" placeholder="Invalid" invalid />
          <A.Checkbox v-model="checked" label="Accept terms" />
          <A.Radio v-model="radio" value="a" name="demo-r" label="Option A" />
          <A.Radio v-model="radio" value="b" name="demo-r" label="Option B" />
          <A.Toggle v-model="toggled" label="Enabled" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Action'">
        <A.Text as="h1" variant="h1">Molecules · Action</A.Text>
        <div class="grid">
          <M.Button>Primary</M.Button>
          <M.Button variant="ghost">Ghost</M.Button>
          <M.Button variant="danger">Danger</M.Button>
          <M.Button icon="upload">Upload</M.Button>
          <M.Button loading>Loading</M.Button>
          <M.Button disabled>Disabled</M.Button>
          <M.Button size="sm">Small</M.Button>
          <M.IconButton icon="close" label="Close" />
          <M.IconButton icon="upload" label="Upload" variant="primary" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Input'">
        <A.Text as="h1" variant="h1">Molecules · Input</A.Text>
        <div class="grid">
          <M.TextField v-model="text" label="Username" hint="Min 3 characters" />
          <M.TextField v-model="text" label="Password" type="password" error="Required" />
          <M.SearchField v-model="text" placeholder="Search files…" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Display'">
        <A.Text as="h1" variant="h1">Molecules · Display</A.Text>
        <div class="grid">
          <M.Badge>Live</M.Badge>
          <M.Badge tone="warning">Pending</M.Badge>
          <M.Badge tone="error">Failed</M.Badge>
          <M.Badge tone="info">Info</M.Badge>
          <M.Badge tone="accent">Accent</M.Badge>
          <M.Tag>design</M.Tag>
          <M.Tag removable>removable</M.Tag>
          <M.StatBlock label="TOTAL FILES" value="2,486" />
          <M.StatBlock label="STORAGE" value="124.7 GB" :delta="3" />
          <M.StatBlock label="ERRORS" value="12" :delta="-2" />
          <M.ProgressBar :value="0.64" />
          <M.ProgressBar :value="0.92" tone="warning" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Nav'">
        <A.Text as="h1" variant="h1">Molecules · Nav</A.Text>
        <div class="grid">
          <div class="row">
            <M.BreadcrumbItem href="/">Home</M.BreadcrumbItem>
            <M.BreadcrumbItem href="/files">Files</M.BreadcrumbItem>
            <M.BreadcrumbItem>Current</M.BreadcrumbItem>
          </div>
          <div class="row">
            <M.Tab :active="tab === 0" @click="tab = 0">Tab one</M.Tab>
            <M.Tab :active="tab === 1" @click="tab = 1">Tab two</M.Tab>
            <M.Tab :active="tab === 2" @click="tab = 2">Tab three</M.Tab>
          </div>
          <M.MenuItem icon="upload" :key-hint="['Ctrl','U']">Upload file</M.MenuItem>
          <M.MenuItem icon="trash" variant="danger">Delete</M.MenuItem>
          <M.Toolbar>
            <M.IconButton icon="upload" label="Upload" />
            <M.IconButton icon="download" label="Download" />
            <template #split>
              <M.IconButton icon="trash" label="Delete" />
            </template>
          </M.Toolbar>
          <div class="row">
            <M.Avatar name="Alice Wong" />
            <M.Avatar name="B" size="sm" />
            <M.Avatar name="" />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.lib { display: grid; grid-template-columns: 260px 1fr; height: 100vh; background: var(--surface-base); color: var(--text-primary); font-family: var(--font-sans); }
.lib-side { padding: 18px; border-right: 1px solid var(--border-default); display: flex; flex-direction: column; gap: 14px; overflow: auto; }
.lib-controls { display: flex; flex-direction: column; gap: 6px; }
.lib-nav { display: flex; flex-direction: column; gap: 0; margin-top: 12px; }
.lib-main { padding: 32px; overflow: auto; display: flex; flex-direction: column; gap: 28px; }
.grid { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; padding: 12px 0; }
.row { display: inline-flex; align-items: center; gap: 8px; }
.dots { display: inline-flex; gap: 6px; align-items: center; }
.swatches { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.sw { display: flex; align-items: center; gap: 10px; padding: 10px; border: 1px solid var(--border-subtle); }
.sw-block { width: 28px; height: 28px; border: 1px solid var(--border-subtle); flex-shrink: 0; }
code { font-family: var(--font-mono); font-size: var(--text-data); color: var(--ac); }
</style>
```

- [ ] **Step 2: Create `web/src/pages/__dev/index.ts`**

```ts
export { default } from './Library.vue';
```

- [ ] **Step 3: Add the dev-only route to `web/src/router/routes.ts`**

Read the existing file first, then add this entry only when `import.meta.env.DEV` is true. Append to the `routes` array (or wherever the catch-all is):

Modify the top of `routes.ts` to look like:

```ts
import type { RouteRecordRaw } from 'vue-router';
import MainLayout from '../components/layout/MainLayout.vue';

const devRoutes: Array<RouteRecordRaw> = import.meta.env.DEV
  ? [{
      path: '/__dev/library',
      name: 'DevLibrary',
      component: () => import('../pages/__dev/index.ts'),
    }]
  : [];

export const routes: Array<RouteRecordRaw> = [
  ...devRoutes,
  // ... rest of existing routes unchanged
];
```

Make sure `devRoutes` is spread **before** the catch-all `/:pathMatch(.*)*` route, otherwise the catch-all swallows `/__dev/library`.

- [ ] **Step 4: Check the route guard**

The route should also bypass `requiresAuth`. Read `web/src/router/gurad.ts` (note: filename misspelled "gurad" in the codebase — preserve that) and verify that `meta.requiresAuth` is opt-in, not opt-out. Our `/__dev/library` route has no `meta`, so it should pass unauthenticated. If the guard rejects routes without `meta.requiresAuth: false`, add that meta flag.

```ts
// If needed in routes.ts:
{
  path: '/__dev/library',
  // ... existing fields,
  meta: { requiresAuth: false },
}
```

- [ ] **Step 5: Type-check + commit**

```bash
cd web && bun run check
```

```bash
git add web/src/pages/__dev/ web/src/router/routes.ts
git commit -m "feat(web): add dev-only /__dev/library route showcasing atoms + molecules"
```

---

### Task 22: Verify library renders in dev

**Files:** none modified.

- [ ] **Step 1: Start dev server**

```bash
cd web && bun run dev
```

- [ ] **Step 2: Open `http://localhost:5173/__dev/library`**

(Or whichever port Vite assigns.)

Verify:
- Sidebar lists all 9 sections
- Each section's components render without errors
- Sidebar's Theme / Accent / Motion segmented controls live-update the page
- No console errors (network errors for `localhost:8080/api` are expected — backend not running)

- [ ] **Step 3: Toggle each theme/accent/motion combination**

Click through:
- Theme: Dark, Light
- Accent: Lime, Amber, Oxide
- Motion: Spring, Tight, Reduced

For each combination, confirm:
- Component backgrounds + text remain legible
- Accent color updates everywhere (buttons, badges, dots)
- Motion preset visibly changes the duration of hover transitions on buttons

If anything looks broken, record which component + which state, fix the component spec in its task, re-run tests, recommit.

- [ ] **Step 4: Build the library page into production bundle**

```bash
cd web && bun run build 2>&1 | tail -5
```

Expected: build succeeds. The library page should NOT appear in production unless `import.meta.env.DEV` is true; the `devRoutes` array is empty in production builds.

Verify the library is excluded:
```bash
grep -rE "DevLibrary|__dev/library" web/dist/ 2>/dev/null | head -5
```

Expected: no matches in production output (or only matches in HMR-only files if any).

- [ ] **Step 5: Stop dev server**

`Ctrl+C` in the dev server terminal.

No commit — this is verification.

---

### Task 23: P1 milestone commit

**Files:** none modified.

- [ ] **Step 1: Verify full suite passes**

```bash
cd web && bun run test && bun run check && bun run build 2>&1 | tail -3
```

Expected: tests pass, type-check passes, build succeeds.

- [ ] **Step 2: Confirm commit history**

```bash
cd D:/pyprj/fileflash && git log --oneline | head -30
```

Expected: see the P1 commits in order (chore vitest, mount helper, atoms one by one, molecules one by one, library route).

- [ ] **Step 3: Update memory with P1 progress**

Update `C:/Users/xc150/.claude/projects/D--pyprj-fileflash/memory/frontend_redesign_progress.md`:

Move P1 from "进行中 / 待开始" to "已完成", listing the major sub-deliverables:

```markdown
**已完成**：
- **P0 Foundation**（2026-05-11）— …（existing entry unchanged）
- **P1 Atoms + Molecules**（YYYY-MM-DD）— 13 atoms + 14 molecules + Vitest 基建 + dev library 路由。
  - Vitest + @vue/test-utils + happy-dom，token-aware `mount` 助手
  - Atoms: Text / MonoNumber / Divider / Bar / Dot / Icon (+ icons.ts 注册表) / Spinner / Surface / Input / Checkbox / Radio / Toggle / KeyHint
  - Molecules: Button / IconButton / TextField / SearchField / Badge / Tag / StatBlock / ProgressBar / BreadcrumbItem / MenuItem / Tab / SegmentedControl / Toolbar / Avatar
  - `/__dev/library` 路由（仅 dev 模式可访问）展示所有组件 × theme × accent × motion 组合
  - ~120 个单元测试全部通过
```

Replace `YYYY-MM-DD` with the actual completion date.

No git commit needed (memory is outside the repo).

---

## Self-Review

After completing all tasks:

1. **Spec coverage** (§ 3.1 Atoms + Molecules):
   - [x] Text atom with 7 variants → Task 5
   - [x] MonoNumber → Task 6
   - [x] Divider → Task 6
   - [x] Bar + Dot → Task 7
   - [x] Icon + icons registry → Task 8
   - [x] Spinner + Surface → Task 9
   - [x] Input + Checkbox → Task 10
   - [x] Radio + Toggle → Task 11
   - [x] KeyHint → Task 12
   - [x] Button + IconButton → Task 13
   - [x] TextField + SearchField → Task 14
   - [x] Badge + Tag → Task 15
   - [x] StatBlock + ProgressBar → Task 16
   - [x] BreadcrumbItem + MenuItem → Task 17
   - [x] Tab + SegmentedControl → Task 18
   - [x] Toolbar + Avatar → Task 19
   - [x] dev library route → Task 21

2. **Quality gates passing**:
   - [x] All ~120 unit tests pass
   - [x] Type-check clean
   - [x] Production build succeeds
   - [x] Library page loads and switches theme/accent/motion live

3. **Constraints honored**:
   - [x] No existing pages or components modified outside of `routes.ts` (one append)
   - [x] No Naive UI components used in new code
   - [x] Every atom + molecule is under the size budget (atoms ≤ 80 lines, molecules ≤ 200 lines)
   - [x] Public façades (`atoms/index.ts`, `molecules/index.ts`) export each component

---

## Out of Scope (deferred to later phases)

- preferencesStore (replacing themeStore) → **P6**
- Theme/Accent/Motion picker UI in the actual Settings page → **P6** (library's controls are dev-only)
- Replacing Naive UI in agent pages → **P7**
- Page transitions / layout-persistent routing → **P2**
- File domain organisms (FileRow, FileTable, etc.) → **P3**
- Shell organisms (AppHeader, LeftSidebar, etc.) → **P2**

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-frontend-redesign-p1-atoms-molecules.md`. Recommended execution:

**Inline execution in the current session.** Given P0's subagent dispatch failures (1M-context proxy issue), inline is the proven path. The task-by-task structure provides natural checkpoints — pause after Task 12 (atoms complete) and Task 19 (molecules complete) for human review if desired. Total estimate: ~3-4 hours of execution time with tight focus.

If subagent dispatch resumes working in this environment, the writing-plans → subagent-driven-development path remains the official one.
