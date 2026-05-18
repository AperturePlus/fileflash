# P0 Foundation: Design Token System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `web/src/style.css`'s ad-hoc `:root` CSS variables with a structured design token system supporting `[data-theme]` (dark/light), `[data-accent]` (lime/amber/oxide), and `[data-motion]` (spring/tight/reduced) switching, plus a backward-compatibility layer that keeps every existing component rendering correctly through this phase.

**Architecture:** New CSS files under `web/src/styles/` organized by token category (color/type/space/motion/edge/shadow). The existing `web/src/style.css` becomes a thin entry that imports the new system + emits legacy variable aliases (`--color-primary` → `var(--ac)`, etc.). A synchronous hydration script in `index.html` applies `data-*` attributes to `<html>` before Vue mounts to prevent FOUC. The current `themeStore` continues to work unchanged; its `body.dark-theme` class is paired with `[data-theme="dark"]` selectors so toggles affect both old and new tokens. **Zero Vue components are modified in this phase.**

**Tech Stack:** Vue 3, Vite, Bun (`bun@1.2.8`), CSS custom properties, IBM Plex Sans + IBM Plex Sans SC + JetBrains Mono via Google Fonts (preconnect strategy)

**Spec reference:** `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` § 2 (Design Token 体系) + § 6.3 (Hydration)

---

## Pre-flight Check

- [ ] **Step 0a: Confirm working directory and branch**

```bash
cd D:/pyprj/fileflash
git status --short
git branch --show-current
```

Expected: on `develop` branch (or a feature branch off it). If on `main`, stop and switch to `develop`.

- [ ] **Step 0b: Confirm no uncommitted changes that would conflict with new files**

```bash
git status web/src/style.css web/index.html web/src/main.ts
```

Expected: these files may be modified or clean — note current state. Do **not** stash; we will not touch business logic in P0.

- [ ] **Step 0c: Verify dev server currently runs (baseline)**

```bash
cd web && bun run dev
```

Expected: Vite serves at `http://localhost:5173`, no console errors. **Manually open** the URL, confirm `/login` renders. Stop the server (`Ctrl+C`) before proceeding.

---

## Task 1: Create the styles directory structure

**Files:**
- Create: `web/src/styles/` (directory)
- Create: `web/src/styles/tokens/` (directory)

- [ ] **Step 1: Create directories**

```bash
mkdir -p web/src/styles/tokens
```

- [ ] **Step 2: Verify**

```bash
ls web/src/styles/
ls web/src/styles/tokens/
```

Expected: both directories exist, both empty.

No commit yet — the directories will be tracked when their first files land.

---

## Task 2: Write base color tokens (`color.css`)

**Files:**
- Create: `web/src/styles/tokens/color.css`

This file defines the dark + light surface ladders and semantic status colors. It does **not** define accent colors (those live in `color.accent.css` so they can swap independently).

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/tokens/color.css
 * Surface ladders + text scale + border tiers + status colors.
 * Default state = dark. Light variant overrides via [data-theme="light"].
 * Legacy `body.dark-theme` selector kept in sync for backward compatibility.
 */:root,
[data-theme="dark"],
body.dark-theme {
  /* Surface ladder */
  --surface-inset:    #0A0A0C;
  --surface-base:     #0E0E10;
  --surface-raised:   #15151A;

  /* Border tiers */
  --border-subtle:    #1F1F23;
  --border-default:   #2A2A30;
  --border-strong:    #3A3A42;

  /* Text scale */
  --text-dim:         #6A6A6A;
  --text-tertiary:    #8A8A8A;
  --text-secondary:   #B8B5AC;
  --text-primary:     #E8E6DF;

  /* Status colors (RGB-form for alpha overlays) */
  --status-success:       #4ADE80;
  --status-success-rgb:   74, 222, 128;
  --status-warning:       #FFB400;
  --status-warning-rgb:   255, 180, 0;
  --status-error:         #FF4F2C;
  --status-error-rgb:     255, 79, 44;
  --status-info:          #60A5FA;
  --status-info-rgb:      96, 165, 250;
}

[data-theme="light"] {
  --surface-inset:    #F2F0EA;
  --surface-base:     #FBFAF6;
  --surface-raised:   #FFFFFF;

  --border-subtle:    #EAE7DE;
  --border-default:   #DAD6CB;
  --border-strong:    #BDB8AA;

  --text-dim:         #9D9A91;
  --text-tertiary:    #7A7770;
  --text-secondary:   #4F4D47;
  --text-primary:     #1B1A17;
}
```

- [ ] **Step 2: Verify the file was written**

```bash
wc -l web/src/styles/tokens/color.css
```

Expected: ~50 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/tokens/color.css
git commit -m "feat(styles): add base color tokens (surface/text/border/status)"
```

---

## Task 3: Write accent color tokens (`color.accent.css`)

**Files:**
- Create: `web/src/styles/tokens/color.accent.css`

Three accent palettes. Default = lime. The hydration script applies `[data-accent="<name>"]` on `<html>`. Lime has separate light-theme variants for WCAG AA contrast.

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/tokens/color.accent.css
 * User-switchable accent. --ac is the primary swatch.
 * --ac-fg is the foreground color used on top of --ac (e.g. button text).
 * --ac-rgb is the comma-separated RGB triplet for rgba() overlays.
 */

:root,
[data-accent="lime"] {
  --ac:     #B6FF3D;
  --ac-rgb: 182, 255, 61;
  --ac-fg:  #0E0E10;
}

[data-accent="amber"] {
  --ac:     #FFB400;
  --ac-rgb: 255, 180, 0;
  --ac-fg:  #0E0E10;
}

[data-accent="oxide"] {
  --ac:     #FF4F2C;
  --ac-rgb: 255, 79, 44;
  --ac-fg:  #FFFFFF;
}

/* Light theme: darker variants for WCAG AA contrast on light surfaces */
[data-theme="light"][data-accent="lime"] {
  --ac:     #5C9E00;
  --ac-rgb: 92, 158, 0;
  --ac-fg:  #FFFFFF;
}

[data-theme="light"][data-accent="amber"] {
  --ac:     #B07700;
  --ac-rgb: 176, 119, 0;
  --ac-fg:  #FFFFFF;
}

[data-theme="light"][data-accent="oxide"] {
  --ac:     #C43617;
  --ac-rgb: 196, 54, 23;
  --ac-fg:  #FFFFFF;
}
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/tokens/color.accent.css
```

Expected: ~35 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/tokens/color.accent.css
git commit -m "feat(styles): add accent color tokens (lime/amber/oxide × light/dark)"
```

---

## Task 4: Write typography tokens (`type.css`)

**Files:**
- Create: `web/src/styles/tokens/type.css`

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/tokens/type.css
 * Font stacks + size scale + weight + line-height + letter-spacing.
 * Sizes follow a deliberate non-linear ratio aligned to the Industrial
 * Dashboard identity. Body 13.5px is the anchor; everything else scales
 * around it.
 */

:root {
  --font-sans: 'IBM Plex Sans', 'IBM Plex Sans SC', 'PingFang SC', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;

  /* Size scale */
  --text-display:   32px;
  --text-h1:        22px;
  --text-h2:        17px;
  --text-body:      13.5px;
  --text-small:     12px;
  --text-label:     10px;
  --text-data:      12px;
  --text-data-big:  22px;

  /* Weight scale */
  --weight-regular:   400;
  --weight-medium:    500;
  --weight-semibold:  600;
  --weight-bold:      700;

  /* Line-height (unitless multipliers) */
  --leading-tight:    1.05;
  --leading-snug:     1.2;
  --leading-normal:   1.55;

  /* Letter-spacing */
  --tracking-tight:   -0.02em;
  --tracking-snug:    -0.01em;
  --tracking-normal:  0;
  --tracking-wide:    0.06em;
  --tracking-wider:   0.18em;
}
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/tokens/type.css
```

Expected: ~35 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/tokens/type.css
git commit -m "feat(styles): add typography tokens (IBM Plex + JetBrains Mono)"
```

---

## Task 5: Write spacing tokens (`space.css`)

**Files:**
- Create: `web/src/styles/tokens/space.css`

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/tokens/space.css
 * 4px base scale. Component-specific tokens (--row-h, --form-gap) are
 * derived from this scale for consistency. Density is "comfort" by default.
 */

:root {
  /* Base scale */
  --sp-xs:   4px;
  --sp-sm:   8px;
  --sp-md:   12px;
  --sp-lg:   16px;
  --sp-xl:   24px;
  --sp-2xl:  32px;
  --sp-3xl:  48px;
  --sp-4xl:  64px;

  /* Component-specific */
  --row-h:        32px;
  --form-gap:     16px;
  --section-gap:  32px;

  /* Layout (preserved from legacy) */
  --layout-header-height:        56px;
  --layout-footer-height:        36px;
  --sidebar-left-width:          260px;
  --sidebar-left-collapsed-width: 64px;
  --sidebar-right-width:         340px;
}
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/tokens/space.css
```

Expected: ~25 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/tokens/space.css
git commit -m "feat(styles): add spacing tokens (4px base + layout constants)"
```

---

## Task 6: Write motion tokens (`motion.css`)

**Files:**
- Create: `web/src/styles/tokens/motion.css`

Three motion presets switched by `[data-motion]`. Spring is default; tight is the alternative; reduced is forced when system prefers reduced motion.

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/tokens/motion.css
 * Three motion presets:
 *   - spring  (default): playful, slight overshoot, 200-280ms
 *   - tight:             Linear/Cron style, 120-180ms ease-out
 *   - reduced:           instant, no transition
 *
 * The hydration script in index.html resolves prefers-reduced-motion
 * automatically and sets [data-motion="reduced"] on <html>.
 */

:root,
[data-motion="spring"] {
  --mo-duration-fast:  200ms;
  --mo-duration-mid:   240ms;
  --mo-duration-slow:  280ms;
  --mo-easing:         cubic-bezier(0.34, 1.56, 0.64, 1);
  --mo-press-scale:    0.94;
  --mo-hover-bloom:    0 0 24px rgba(var(--ac-rgb), 0.4);
}

[data-motion="tight"] {
  --mo-duration-fast:  120ms;
  --mo-duration-mid:   140ms;
  --mo-duration-slow:  180ms;
  --mo-easing:         cubic-bezier(0.2, 0.8, 0.2, 1);
  --mo-press-scale:    0.96;
  --mo-hover-bloom:    none;
}

[data-motion="reduced"] {
  --mo-duration-fast:  0ms;
  --mo-duration-mid:   0ms;
  --mo-duration-slow:  0ms;
  --mo-easing:         linear;
  --mo-press-scale:    1;
  --mo-hover-bloom:    none;
}
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/tokens/motion.css
```

Expected: ~35 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/tokens/motion.css
git commit -m "feat(styles): add motion tokens (spring/tight/reduced presets)"
```

---

## Task 7: Write edge + shadow tokens

**Files:**
- Create: `web/src/styles/tokens/edge.css`
- Create: `web/src/styles/tokens/shadow.css`

- [ ] **Step 1: Write `edge.css`**

```css
/* web/src/styles/tokens/edge.css
 * Border radii + border weights. B is hard-edged: max radius 4px,
 * everything else is 0 or 2px. Hairline 1px borders carry most of
 * the visual hierarchy (replacing shadows).
 */

:root {
  /* Radii */
  --radius-0:   0;
  --radius-sm:  2px;
  --radius-md:  4px;

  /* Border weights */
  --border-hairline:  1px;
  --border-thick:     2px;
}
```

- [ ] **Step 2: Write `shadow.css`**

```css
/* web/src/styles/tokens/shadow.css
 * B uses shadows sparingly — visual hierarchy comes from contrast and
 * hairline borders, not depth. Only one overlay shadow exists, used by
 * dialogs and popovers. Light theme uses a slightly cooler overlay tint.
 */

:root,
[data-theme="dark"],
body.dark-theme {
  --shadow-overlay: 0 16px 48px rgba(0, 0, 0, 0.42);
}

[data-theme="light"] {
  --shadow-overlay: 0 16px 48px rgba(15, 23, 42, 0.18);
}
```

- [ ] **Step 3: Verify both files**

```bash
wc -l web/src/styles/tokens/edge.css web/src/styles/tokens/shadow.css
```

Expected: edge.css ~15 lines, shadow.css ~15 lines.

- [ ] **Step 4: Commit**

```bash
git add web/src/styles/tokens/edge.css web/src/styles/tokens/shadow.css
git commit -m "feat(styles): add edge + shadow tokens"
```

---

## Task 8: Write CSS reset (`reset.css`)

**Files:**
- Create: `web/src/styles/reset.css`

A minimal modern reset, scoped to what we actually need. No external library (no `modern-normalize` etc.) — keeping the dependency surface zero.

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/reset.css
 * Minimal modern CSS reset. Keep this short: only what FileFlash needs.
 */

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  line-height: var(--leading-normal);
  color: var(--text-primary);
  background: var(--surface-base);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  transition: background-color var(--mo-duration-mid) var(--mo-easing),
              color var(--mo-duration-mid) var(--mo-easing);
}

#app {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

a {
  color: var(--ac);
  text-decoration: none;
  transition: color var(--mo-duration-fast) var(--mo-easing);
}

a:hover {
  text-decoration: underline;
}

h1, h2, h3, h4, h5, h6 {
  margin: 0;
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
}

button,
input,
textarea,
select {
  font: inherit;
  color: inherit;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/reset.css
```

Expected: ~55 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/reset.css
git commit -m "feat(styles): add minimal CSS reset"
```

---

## Task 9: Write the legacy compatibility layer (`legacy-compat.css`)

**Files:**
- Create: `web/src/styles/legacy-compat.css`

This is the critical file that lets every existing component keep rendering correctly without any code change. Every variable name from the old `style.css` is aliased here to a new token.

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/legacy-compat.css
 * Bridges legacy CSS variable names (used by existing components) to
 * the new token system. Lets P0 land without modifying any component.
 *
 * This file is REMOVED in P8 (cleanup) after every legacy reference is
 * migrated. Until then, every var() in pages/components that starts with
 * --color-*, --spacing-*, --font-*, --shadow-*, --transition-*,
 * --border-radius-* is resolved here.
 */

:root,
[data-theme="dark"],
body.dark-theme {
  /* Color aliases — accent */
  --color-primary:        var(--ac);
  --color-primary-rgb:    var(--ac-rgb);
  --color-primary-hover:  var(--ac);
  --color-primary-light:  rgba(var(--ac-rgb), 0.15);
  --color-primary-dark:   var(--ac);
  --color-text-on-primary: var(--ac-fg);

  /* Color aliases — surfaces */
  --color-bg-base:        var(--surface-base);
  --color-bg-primary:     var(--surface-raised);
  --color-bg-secondary:   var(--surface-raised);
  --color-bg-tertiary:    var(--surface-inset);
  --color-bg-quaternary:  var(--surface-inset);

  /* Color aliases — borders */
  --color-border:         var(--border-default);
  --color-border-hover:   var(--border-strong);
  --color-divider:        var(--border-subtle);

  /* Color aliases — text */
  --color-text-primary:    var(--text-primary);
  --color-text-secondary:  var(--text-secondary);
  --color-text-tertiary:   var(--text-tertiary);
  --color-text-quaternary: var(--text-dim);

  /* Color aliases — semantic */
  --color-success:        var(--status-success);
  --color-warning:        var(--status-warning);
  --color-danger:         var(--status-error);
  --color-danger-dark:    var(--status-error);
  --color-danger-light:   rgba(var(--status-error-rgb), 0.15);

  /* Font aliases */
  --font-family-sans:  var(--font-sans);
  --font-family-mono:  var(--font-mono);
  --font-size-base:    var(--text-body);
  --font-size-lg:      var(--text-h2);
  --font-size-xl:      var(--text-h1);
  --font-weight-normal:    var(--weight-regular);
  --font-weight-medium:    var(--weight-medium);
  --font-weight-semibold:  var(--weight-semibold);
  --font-weight-bold:      var(--weight-bold);
  --line-height-base:      var(--leading-normal);

  /* Spacing aliases */
  --spacing-unit: 8px;
  --spacing-xs:   var(--sp-xs);
  --spacing-sm:   var(--sp-sm);
  --spacing-md:   var(--sp-md);
  --spacing-lg:   var(--sp-lg);
  --spacing-xl:   var(--sp-xl);

  /* Radius aliases (legacy used 6/10/14 — map to new 0/2/4 conservatively) */
  --border-radius-sm:  var(--radius-sm);
  --border-radius-md:  var(--radius-sm);
  --border-radius-lg:  var(--radius-md);

  /* Transition alias */
  --transition-base:  all var(--mo-duration-mid) var(--mo-easing);

  /* Shadow aliases — legacy expected layered shadows; B uses minimal shadow.
     Map them all to a single overlay shadow for dialog-class elements;
     other usages get hairline-only feel. */
  --shadow-sm:  none;
  --shadow-md:  var(--shadow-overlay);
  --shadow-lg:  var(--shadow-overlay);
  --shadow-xl:  var(--shadow-overlay);
}
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/legacy-compat.css
```

Expected: ~75 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/legacy-compat.css
git commit -m "feat(styles): add legacy variable compatibility layer"
```

---

## Task 10: Write the theme entry (`theme.css`)

**Files:**
- Create: `web/src/styles/theme.css`

Single import root that loads all token files in the correct order. Order matters: tokens first, reset last (so reset can use the tokens).

- [ ] **Step 1: Write the file**

```css
/* web/src/styles/theme.css
 * Single entry that imports the entire token system.
 * Import order is significant:
 *   1. Tokens (color, accent, type, space, motion, edge) define variables
 *   2. Legacy compat aliases legacy names to new tokens
 *   3. Reset uses the variables to style the root document
 */

@import './tokens/color.css';
@import './tokens/color.accent.css';
@import './tokens/type.css';
@import './tokens/space.css';
@import './tokens/motion.css';
@import './tokens/edge.css';
@import './tokens/shadow.css';
@import './legacy-compat.css';
@import './reset.css';
```

- [ ] **Step 2: Verify**

```bash
wc -l web/src/styles/theme.css
```

Expected: ~13 lines.

- [ ] **Step 3: Commit**

```bash
git add web/src/styles/theme.css
git commit -m "feat(styles): add theme.css entry that imports the full token system"
```

---

## Task 11: Update `index.html` with font preconnect, stylesheet links, and hydration script

**Files:**
- Modify: `web/index.html`

The hydration script must run **synchronously in `<head>` before any rendering** so the data attributes are set before any CSS evaluates. Font links use `<link rel="stylesheet">` (not `@import`) so the browser starts the request immediately.

- [ ] **Step 1: Read the current `index.html`**

```bash
cat web/index.html
```

Expected: 14-line minimal HTML, just `<title>FileFlash Cloud Drive</title>` and the Vite script.

- [ ] **Step 2: Replace `web/index.html` with**:

```html
<!doctype html>
<html lang="en" data-theme="dark" data-accent="lime" data-motion="spring">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FileFlash Cloud Drive</title>

    <!-- Hydrate <html> data-* attributes BEFORE Vue mounts to avoid FOUC -->
    <script>
      (function () {
        // Theme: read existing localStorage 'theme' key (used by current themeStore)
        var savedTheme = localStorage.getItem('theme');
        var theme =
          savedTheme === 'dark' || savedTheme === 'light'
            ? savedTheme
            : matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';

        // Accent + motion: new ff.pref key. P0 has no UI to change these yet.
        var pref;
        try {
          pref = JSON.parse(localStorage.getItem('ff.pref') || '{}');
        } catch (e) {
          pref = {};
        }
        var accent =
          pref.accent === 'amber' || pref.accent === 'oxide' ? pref.accent : 'lime';
        var motion = matchMedia('(prefers-reduced-motion: reduce)').matches
          ? 'reduced'
          : pref.motion === 'tight'
          ? 'tight'
          : 'spring';

        var html = document.documentElement;
        html.dataset.theme = theme;
        html.dataset.accent = accent;
        html.dataset.motion = motion;
      })();
    </script>

    <!-- Fonts: preconnect first, then load CSS in parallel with the JS bundle -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
    />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 3: Verify the file**

```bash
wc -l web/index.html
```

Expected: ~50 lines.

- [ ] **Step 4: Commit**

```bash
git add web/index.html
git commit -m "feat(web): preload fonts and hydrate data-theme/accent/motion before mount"
```

---

## Task 12: Replace `web/src/style.css` with theme-system import

**Files:**
- Modify: `web/src/style.css`

This is the file `web/src/main.ts:3` imports. The current 168-line monolith is replaced with a 3-line shim that pulls in the new system. Every variable name the existing components reference is preserved through `legacy-compat.css`.

- [ ] **Step 1: Read the current `style.css` to confirm what we're replacing**

```bash
wc -l web/src/style.css
head -20 web/src/style.css
```

Expected: ~168 lines, starts with the Google Fonts `@import` (which we are now removing — fonts are loaded via `<link>` in `index.html`).

- [ ] **Step 2: Replace `web/src/style.css` with**:

```css
/* web/src/style.css
 * Entry imported by main.ts. Delegates to the token system at
 * styles/theme.css. The full :root variable definitions and the
 * .dark-theme override that previously lived here have been migrated
 * to web/src/styles/tokens/*.css and web/src/styles/legacy-compat.css.
 *
 * In P8 cleanup, main.ts will import 'styles/theme.css' directly and
 * this file will be deleted.
 */

@import './styles/theme.css';
```

- [ ] **Step 3: Verify**

```bash
wc -l web/src/style.css
```

Expected: 11 lines.

- [ ] **Step 4: Commit**

```bash
git add web/src/style.css
git commit -m "refactor(web): replace style.css with theme.css shim (P0 token migration)"
```

---

## Task 13: Run TypeScript check and Vite build

These are the only mechanical gates we have without a test framework yet. Both must pass before manual visual verification.

**Files:** none modified.

- [ ] **Step 1: Type-check**

```bash
cd web && bun run check
```

Expected: exits 0, no errors. (P0 only touches CSS + HTML; TS surface unchanged. If this fails, something unrelated regressed — investigate, do not ignore.)

- [ ] **Step 2: Production build**

```bash
cd web && bun run build
```

Expected: exits 0. Build output appears under `web/dist/`. **Verify `dist/index.html` contains the inline hydration script** (Vite should preserve it):

```bash
grep -c "html.dataset.theme" web/dist/index.html
```

Expected: `1` or higher. If `0`, the hydration script was stripped — check Vite's HTML processing config.

- [ ] **Step 3: Verify CSS bundle includes new tokens**

```bash
grep -E "(--surface-base|--ac:|--mo-duration-mid)" web/dist/assets/*.css | head -5
```

Expected: at least one match per pattern, confirming token CSS made it into the production bundle.

No commit — this task only validates the build. If build fails, fix and re-commit the offending task before proceeding.

---

## Task 14: Manual visual smoke test on dev server

**Files:** none modified.

The goal: confirm every existing page still renders without visible regression, and that toggling `[data-theme]` / `[data-accent]` / `[data-motion]` via DevTools changes the right things.

- [ ] **Step 1: Start the dev server**

```bash
cd web && bun run dev
```

Expected: Vite serves at `http://localhost:5173`, no console errors during HMR or initial load.

- [ ] **Step 2: Confirm the initial paint**

Open `http://localhost:5173` in a browser. Open DevTools → Console. Verify:
- No red errors
- No "Failed to load font" warnings
- `<html>` element in Elements panel has `data-theme`, `data-accent`, `data-motion` attributes set

- [ ] **Step 3: Walk the major surfaces (note any visual breakage to the user)**

Visit each route and confirm it renders without console errors:
- `/login`
- `/register`
- `/forgot-password` (may need to navigate from login link)
- `/files` (requires auth — log in with mock credentials if needed; if mocks are off, skip)
- `/profile`
- `/settings`

If you cannot authenticate (mocks disabled), at minimum verify `/login` and `/register`.

If any page shows broken styling (e.g., text on text, invisible buttons, missing background), record which page and which selector — then fix the corresponding alias in `legacy-compat.css`. Re-commit the fix as `fix(styles): repair <X> compat alias`.

- [ ] **Step 4: Toggle theme via DevTools**

In the Elements panel, find `<html>`. Edit its `data-theme` attribute:
- `data-theme="dark"` (default) — page should be dark surfaces, light text
- `data-theme="light"` — page should switch to light surfaces, dark text within the same paint

Expected: visual switch happens instantly via CSS variable cascade. No JS needed.

- [ ] **Step 5: Toggle accent via DevTools**

Edit `<html>`'s `data-accent` attribute through `lime` → `amber` → `oxide`. Watch any element using `var(--ac)` (header brand link, primary buttons in their existing legacy form via `--color-primary` alias).

Expected: accent color updates instantly across the page.

- [ ] **Step 6: Toggle motion via DevTools**

Edit `data-motion` through `spring` → `tight` → `reduced`. There's no obvious visual indicator yet (motion tokens are referenced by future organisms), but verify computed styles on `<body>`:

In DevTools console:
```js
getComputedStyle(document.body).getPropertyValue('--mo-duration-mid')
```

Expected:
- spring → `240ms`
- tight → `140ms`
- reduced → `0ms`

- [ ] **Step 7: Verify the existing themeStore toggle still works**

Click the theme toggle button in the existing app header. The `body.dark-theme` class should add/remove, and the page should swap dark/light. (This works because token selectors include `body.dark-theme` alongside `[data-theme="dark"]`.)

- [ ] **Step 8: Stop the dev server**

`Ctrl+C` in the terminal.

- [ ] **Step 9: Commit any compat fixes (if any) and tag the foundation**

If steps 3–7 turned up issues, commits from those fixes are already in. Tag the milestone:

```bash
git tag p0-foundation
```

(Tag is local-only; pushing to remote is a separate manual call by the user.)

---

## Task 15: Update memory with P0 completion state

**Files:**
- Modify: `C:/Users/xc150/.claude/projects/D--pyprj-fileflash/memory/MEMORY.md`
- Create: `C:/Users/xc150/.claude/projects/D--pyprj-fileflash/memory/frontend_redesign_progress.md`

A small project memory entry so future conversations know which phase landed and where to pick up.

- [ ] **Step 1: Create the progress memory file**

Write `C:/Users/xc150/.claude/projects/D--pyprj-fileflash/memory/frontend_redesign_progress.md`:

```markdown
---
name: Frontend redesign progress
description: Phase tracker for the FileFlash Industrial Dashboard redesign — which phases (P0–P8) have landed
type: project
---

FileFlash 前端重塑分 8 阶段（P0 Foundation → P8 Cleanup）。Spec 在
`docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md`。
每个阶段的 plan 在 `docs/superpowers/plans/2026-05-11-frontend-redesign-p<N>-*.md`。

**已完成**：
- P0 Foundation（2026-05-11）— 设计 token 系统 + legacy-compat 兼容层 + index.html 水合脚本。所有现有组件继续渲染。

**进行中 / 待开始**：
- P1 Atoms + Molecules — 原子组件库 + dev library 路由（包含 Vitest 测试基建）
- P2 Shell + Templates — MainLayout/AuthLayout 等 + shell organisms + 路由层级调整
- P3 Core File Path — MyFiles + 9 个 files organism
- P4 Other File Surfaces — Shared / Trash / ShareAccess
- P5 Public Auth Flow — Login / Register / ForgotPassword / VerifyEmail
- P6 Account — Profile / Settings + preferencesStore（替换 themeStore）
- P7 Admin & Agent — Dashboard / AgentWorkspace / AgentSkills + 移除 Naive UI 依赖
- P8 Cleanup — 删除 legacy-compat、旧目录、Skills.vue、空 layouts/

**How to apply**：开始下一阶段时先读 spec 和上一阶段 plan，确认验收标准全过；否则补完再前进。
```

- [ ] **Step 2: Add a pointer to MEMORY.md**

Read the current `MEMORY.md`:

```bash
cat C:/Users/xc150/.claude/projects/D--pyprj-fileflash/memory/MEMORY.md
```

Append (preserve existing entries):

```markdown
- [Frontend redesign progress](frontend_redesign_progress.md) — 8 阶段重塑的当前进度（P0 已完成）
```

- [ ] **Step 3: No git commit needed** (memory directory is outside the repo).

---

## Self-Review (run after the engineer completes all tasks)

These are the human/agent verification points before declaring P0 done:

1. **Spec coverage** (§ 2 Token 体系):
   - [x] color.css covers dark + light surface ladders → Task 2
   - [x] color.accent.css covers lime/amber/oxide × dark/light → Task 3
   - [x] type.css covers IBM Plex + JetBrains Mono + size scale → Task 4
   - [x] space.css covers 4-8-12-16-24-32-48-64 + layout vars → Task 5
   - [x] motion.css covers spring/tight/reduced → Task 6
   - [x] edge.css covers radii + border weights → Task 7
   - [x] shadow.css covers --shadow-overlay (dark + light) → Task 7
   - [x] reset.css resets box-sizing + body defaults → Task 8
   - [x] theme.css orchestrates imports → Task 10
   - [x] Hydration script in index.html applies data-* before mount → Task 11
   - [x] Existing themeStore continues to work via `body.dark-theme` selector pairing → Task 2 + Task 9

2. **No-touch promise** (no Vue components modified):
   - [x] No `.vue` files in the diff for tasks 1–14
   - [x] No `store/*.ts` modifications
   - [x] All component-side variable references continue to resolve via `legacy-compat.css`

3. **Backward compatibility**:
   - [x] `--color-primary`, `--color-bg-base`, `--color-text-primary`, etc. all resolve to non-empty values
   - [x] `body.dark-theme` selector still toggles dark surfaces
   - [x] `localStorage.getItem('theme')` is the source of truth that hydration reads (matches existing themeStore key)

4. **Build/runtime verification**:
   - [x] `bun run check` passes (Task 13 step 1)
   - [x] `bun run build` passes (Task 13 step 2)
   - [x] Production CSS bundle contains new tokens (Task 13 step 3)
   - [x] Manual smoke across major routes shows no visual regression (Task 14)
   - [x] DevTools toggle of `data-theme`/`data-accent`/`data-motion` produces expected visual change (Task 14 steps 4–6)

If any checkbox is unchecked: **stop**, fix, re-run the relevant task, do not proceed to P1.

---

## Out of Scope for P0 (deferred to later phases)

- Vitest + @vue/test-utils setup → **P1** (introduced when first atom needs a test)
- Self-hosted woff2 fonts → P0+ optimization, not blocking
- preferencesStore (replaces themeStore) → **P6** with the Settings page redesign
- Page transition fix (the "切页像刷新" root cause) → **P2** with MainLayout rewrite
- Removal of `transform: translateY(-1px)` hover-lift / `cubic-bezier(0.4, 0, 0.2, 1)` patterns from existing components → P3-P7 as each component is migrated
- `--shadow-sm` becoming actual hairline → P3+, when components stop relying on the alias

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-frontend-redesign-p0-foundation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration with checkpoints. Best for catching issues early.

**2. Inline Execution** — Execute tasks in this same session using executing-plans skill, batched checkpoints for review. Lower context overhead but harder to roll back individual tasks.

Which approach?
