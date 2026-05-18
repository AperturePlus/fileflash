# P2 Shell + Templates + Route Hierarchy Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the template + shell organism layers that replace the existing `components/layout/` pages. This is the **first user-visible visual change** — the app shell (header, sidebars, footer) is rebuilt with the new Industrial Dashboard tokens and atoms/molecules. The "切页像刷新" root cause is fixed by moving the page transition from `App.vue` into each template's content `router-view`. Route hierarchy is adjusted so layouts are proper route-level components.

**Architecture:**
- `components/templates/` — 5 layout templates: MainLayout, AuthLayout, BareLayout, ShareLayout, AgentLayout
- `components/organisms/shell/` — 6 shell organisms: AppHeader, LeftSidebar, RightSidebar, Footer, StorageStatusWidget, UserMenu
- `App.vue` — stripped of `<transition>`; only Naive UI providers + global dialogs remain
- `router/routes.ts` — restructured so `/login`, `/register`, `/forgot-password` use AuthLayout; `/verify-email` uses BareLayout; `/share/:shareLink` uses ShareLayout; `/` uses MainLayout; `/agent` uses AgentLayout
- Existing business logic (file preview, storage stats, search, theme toggle, locale, auth guards) is **preserved verbatim** during migration

**Tech Stack:** Vue 3, Vite, Bun, Naive UI (providers only), new atom/molecule library

**Spec reference:** `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` §3.1 (Atomic Design), §5 (Routing & "切页像刷新" fix)

**Predecessor:** P1 Atoms + Molecules. All atoms/molecules are in place and tested.

---

## Pre-flight

- [ ] **Step 0a: Confirm P1 commits are on develop**

```bash
cd D:/pyprj/fileflash && git log --oneline | grep -E "feat\(atoms\):|feat\(molecules\):|feat\(web\): add dev-only" | head -5
```

Expected: commits reachable.

- [ ] **Step 0b: Verify test + build still clean**

```bash
cd web && bun run test && bun run check && bun run build 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 0c: Confirm current route structure**

Open `web/src/router/routes.ts`. Verify the current flat structure (no nested AuthLayout/ShareLayout/AgentLayout).

---

## Phase A — Templates (Tasks 1–5)

Templates are thin wrappers. They contain the shell organisms and a `<router-view>` for content. Each template is ≤ 150 lines.

### Task 1: Create templates directory + MainLayout

**Files:**
- Create: `web/src/components/templates/MainLayout.vue`
- Create: `web/src/components/templates/index.ts`

**Design notes:**
- Content `<router-view>` is wrapped in `<transition name="page-fade" mode="out-in">`
- `Suspense` fallback is `Spinner` atom instead of plain text
- Header/footer/sidebar logic is delegated to shell organisms
- Old `components/layout/MainLayout.vue` is **not deleted yet** (P8 cleanup)

- [ ] **Step 1: Write `MainLayout.vue`**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useFileStore } from '../../store/file';
import { storeToRefs } from 'pinia';
import AppHeader from '../organisms/shell/AppHeader.vue';
import LeftSidebar from '../organisms/shell/LeftSidebar.vue';
import RightSidebar from '../organisms/shell/RightSidebar.vue';
import Footer from '../organisms/shell/Footer.vue';

const fileStore = useFileStore();
const { selectedFile } = storeToRefs(fileStore);

const leftCollapsed = ref(false);
const rightHidden = ref(false);
const rightVisible = computed(() => !!selectedFile.value && !rightHidden.value);

function toggleLeft() { leftCollapsed.value = !leftCollapsed.value; }
function toggleRight() { if (selectedFile.value) rightHidden.value = !rightHidden.value; }
</script>

<template>
  <div class="main-layout">
    <AppHeader
      :left-collapsed="leftCollapsed"
      :right-visible="rightVisible"
      @toggle-left="toggleLeft"
      @toggle-right="toggleRight"
    />
    <div class="layout-body">
      <LeftSidebar :collapsed="leftCollapsed" />
      <main class="layout-content">
        <div class="content-scroll">
          <router-view v-slot="{ Component, route }">
            <transition name="page-fade" mode="out-in">
              <Suspense>
                <component :is="Component" :key="route.path" />
                <template #fallback>
                  <div class="fallback">
                    <Spinner label="Loading page" />
                  </div>
                </template>
              </Suspense>
            </transition>
          </router-view>
        </div>
        <Footer />
      </main>
      <RightSidebar :visible="rightVisible" />
    </div>
  </div>
</template>

<script lang="ts">
import Spinner from '../atoms/Spinner.vue';
export default { components: { Spinner } };
</script>

<style scoped>
.main-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; }
.layout-body { display: flex; min-height: 0; flex: 1; }
.layout-content { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.content-scroll { flex: 1; overflow: auto; padding: var(--sp-lg); }
.fallback { display: flex; align-items: center; justify-content: center; min-height: 240px; }

/* Page transition tied to motion tokens */
:global([data-motion="spring"]) .page-fade-enter-active,
:global([data-motion="spring"]) .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing),
              transform var(--mo-duration-mid) var(--mo-easing);
}
:global([data-motion="spring"]) .page-fade-enter-from { opacity: 0; transform: scale(0.98); }
:global([data-motion="spring"]) .page-fade-leave-to   { opacity: 0; transform: scale(1.02); }

:global([data-motion="tight"]) .page-fade-enter-active,
:global([data-motion="tight"]) .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing),
              transform var(--mo-duration-mid) var(--mo-easing);
}
:global([data-motion="tight"]) .page-fade-enter-from { opacity: 0; transform: translateX(-6px); }
:global([data-motion="tight"]) .page-fade-leave-to   { opacity: 0; transform: translateX(6px); }

:global([data-motion="reduced"]) .page-fade-enter-active,
:global([data-motion="reduced"]) .page-fade-leave-active { transition: none; }
</style>
```

- [ ] **Step 2: Write `templates/index.ts`**

```ts
export { default as MainLayout } from './MainLayout.vue';
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/templates/
git commit -m "feat(templates): add MainLayout with internal page transition + motion token linkage"
```

---

### Task 2: AuthLayout

**Files:**
- Create: `web/src/components/templates/AuthLayout.vue`

- [ ] **Step 1: Write `AuthLayout.vue`**

```vue
<script setup lang="ts">
import { useThemeStore } from '../../store/theme';
import logoLight from '../../assets/logo/icon_white.png';
import logoDark from '../../assets/logo/icon_dark.png';

const themeStore = useThemeStore();
</script>

<template>
  <div class="auth-layout">
    <div class="auth-card">
      <div class="auth-brand">
        <img :src="themeStore.theme === 'light' ? logoLight : logoDark" alt="FileFlash" class="auth-logo" />
        <span class="auth-title">FileFlash</span>
      </div>
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.auth-layout {
  display: flex; align-items: center; justify-content: center;
  width: 100vw; height: 100vh;
  background: var(--surface-base);
}
.auth-card {
  width: min(420px, 92vw);
  padding: var(--sp-2xl);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.auth-brand {
  display: flex; align-items: center; gap: var(--sp-md);
  margin-bottom: var(--sp-xl);
}
.auth-logo { width: 38px; height: 38px; }
.auth-title { font-size: var(--text-h1); font-weight: var(--weight-semibold); color: var(--text-primary); }
</style>
```

- [ ] **Step 2: Update `templates/index.ts`**

```ts
export { default as MainLayout } from './MainLayout.vue';
export { default as AuthLayout } from './AuthLayout.vue';
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/templates/
git commit -m "feat(templates): add AuthLayout"
```

---

### Task 3: BareLayout

**Files:**
- Create: `web/src/components/templates/BareLayout.vue`

- [ ] **Step 1: Write `BareLayout.vue`**

```vue
<template>
  <div class="bare-layout">
    <router-view v-slot="{ Component, route }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </div>
</template>

<style scoped>
.bare-layout {
  display: flex; align-items: center; justify-content: center;
  width: 100vw; height: 100vh;
  background: var(--surface-base);
}
</style>
```

- [ ] **Step 2: Update barrel + commit**

```ts
export { default as MainLayout } from './MainLayout.vue';
export { default as AuthLayout } from './AuthLayout.vue';
export { default as BareLayout } from './BareLayout.vue';
```

```bash
git add web/src/components/templates/
git commit -m "feat(templates): add BareLayout"
```

---

### Task 4: ShareLayout + AgentLayout

**Files:**
- Create: `web/src/components/templates/ShareLayout.vue`
- Create: `web/src/components/templates/AgentLayout.vue`

- [ ] **Step 1: Write `ShareLayout.vue`**

```vue
<template>
  <div class="share-layout">
    <header class="share-header">
      <span class="share-brand">FileFlash</span>
    </header>
    <main class="share-main">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.share-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; background: var(--surface-base); }
.share-header { height: var(--layout-header-height); display: flex; align-items: center; padding: 0 var(--sp-lg); border-bottom: 1px solid var(--border-default); }
.share-brand { font-size: var(--text-h2); font-weight: var(--weight-semibold); color: var(--text-primary); }
.share-main { flex: 1; overflow: auto; padding: var(--sp-xl); }
</style>
```

- [ ] **Step 2: Write `AgentLayout.vue`**

```vue
<template>
  <div class="agent-layout">
    <main class="agent-main">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.agent-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; background: var(--surface-base); }
.agent-main { flex: 1; overflow: auto; padding: var(--sp-lg); }
</style>
```

- [ ] **Step 3: Update barrel + commit**

```ts
export { default as MainLayout } from './MainLayout.vue';
export { default as AuthLayout } from './AuthLayout.vue';
export { default as BareLayout } from './BareLayout.vue';
export { default as ShareLayout } from './ShareLayout.vue';
export { default as AgentLayout } from './AgentLayout.vue';
```

```bash
git add web/src/components/templates/
git commit -m "feat(templates): add ShareLayout + AgentLayout"
```

---

### Task 5: Update `App.vue` — remove top-level transition

**Files:**
- Modify: `web/src/App.vue`

- [ ] **Step 1: Replace `App.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { darkTheme, NConfigProvider, NDialogProvider, NMessageProvider } from 'naive-ui';
import { useThemeStore } from './store/theme';
import { useLocaleStore } from './store/locale';
import ConfirmDialog from './components/common/ConfirmDialog.vue';
import PromptDialog from './components/common/PromptDialog.vue';
import ToastStack from './components/common/ToastStack.vue';

useThemeStore();
useLocaleStore();

const themeStore = useThemeStore();
const naiveTheme = computed(() => (themeStore.theme === 'dark' ? darkTheme : null));
</script>

<template>
  <NConfigProvider :theme="naiveTheme">
    <NDialogProvider>
      <NMessageProvider placement="top-right" :max="4">
        <router-view />
        <ConfirmDialog />
        <PromptDialog />
        <ToastStack />
      </NMessageProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>

<style>
/* Global page transition styles removed — now live in each template's scoped CSS */
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/App.vue
git commit -m "fix(app): remove top-level transition to stop full-layout fade (切页像刷新 root cause)"
```

---

## Phase B — Shell Organisms (Tasks 6–11)

These are migrated from `components/layout/`. Business logic is preserved; styles are rewritten with tokens.

### Task 6: Scaffold organisms/shell directory

**Files:**
- Create: `web/src/components/organisms/shell/` (directory)
- Create: `web/src/components/organisms/index.ts`

- [ ] **Step 1: Create directory + empty barrel**

```bash
mkdir -p web/src/components/organisms/shell
```

`web/src/components/organisms/index.ts`:
```ts
// Public façade for organism components. Populated as organisms land in P2-P7.
export {};
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/organisms/
git commit -m "feat(organisms): scaffold organisms/shell directory"
```

---

### Task 7: AppHeader organism

**Files:**
- Create: `web/src/components/organisms/shell/AppHeader.vue`

This is a **drop-in migration** of `components/layout/Header.vue` with:
- New atom/molecule imports (Icon, IconButton, SearchField)
- Token-based styling (no more `cubic-bezier(0.4, 0, 0.2, 1)` or `translateY(-1px)`)
- Hard-edge geometry, hairline borders, no backdrop-filter blur

- [ ] **Step 1: Write `AppHeader.vue`**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { useThemeStore } from '../../store/theme';
import { useUserStore } from '../../store/user';
import { useLocaleStore } from '../../store/locale';
import { eventBus } from '../../utils/eventBus';
import Icon from '../../atoms/Icon.vue';
import IconButton from '../../molecules/IconButton.vue';
import SearchField from '../../molecules/SearchField.vue';
import UserMenu from './UserMenu.vue';

const props = defineProps<{
  leftCollapsed: boolean;
  rightVisible: boolean;
}>();

const emit = defineEmits(['toggle-left', 'toggle-right']);

const router = useRouter();
const themeStore = useThemeStore();
const userStore = useUserStore();
const localeStore = useLocaleStore();
const t = localeStore.t;

const searchQuery = ref('');

const dispatchSearch = useDebounceFn((query: string) => {
  eventBus.emit('search-files', { query });
}, 280);

function onSearchInput(value: string) {
  searchQuery.value = value;
  dispatchSearch(value.trim());
}

function goHome() { router.push('/files'); }
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <IconButton
        :icon="leftCollapsed ? 'chevronRight' : 'menu'"
        :label="leftCollapsed ? t('header.expandSidebar') : t('header.collapseSidebar')"
        variant="ghost"
        @click="emit('toggle-left')"
      />
      <div class="brand" @click="goHome">
        <img
          :src="themeStore.theme === 'light' ? '/assets/logo/icon_white.png' : '/assets/logo/icon_dark.png'"
          alt="FileFlash"
          class="brand-logo"
        />
        <div class="brand-text">
          <strong>FileFlash</strong>
          <span>{{ t('header.brandSubtitle') }}</span>
        </div>
      </div>
    </div>

    <div class="header-center">
      <SearchField
        v-model="searchQuery"
        :placeholder="t('header.searchPlaceholder')"
        @update:model-value="onSearchInput"
      />
    </div>

    <div class="header-right">
      <IconButton
        :icon="themeStore.theme === 'light' ? 'sun' : 'moon'"
        :label="t('header.toggleTheme')"
        variant="ghost"
        @click="themeStore.toggleTheme"
      />
      <IconButton
        icon="more"
        :label="rightVisible ? t('header.hidePreviewPanel') : t('header.showPreviewPanel')"
        variant="ghost"
        @click="emit('toggle-right')"
      />
      <UserMenu />
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  height: var(--layout-header-height);
  padding: 0 var(--sp-lg);
  gap: var(--sp-lg);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-default);
  position: relative;
  z-index: 20;
}
.header-left, .header-center, .header-right { display: flex; align-items: center; min-width: 0; gap: var(--sp-md); }
.brand { display: flex; align-items: center; gap: var(--sp-sm); cursor: pointer; padding: 4px 8px; border-radius: var(--radius-sm); transition: background-color var(--mo-duration-fast) var(--mo-easing); }
.brand:hover { background: var(--surface-inset); }
.brand-logo { width: 32px; height: 32px; border-radius: var(--radius-sm); }
.brand-text { display: flex; flex-direction: column; line-height: 1.1; }
.brand-text strong { font-size: var(--text-body); color: var(--text-primary); }
.brand-text span { font-size: var(--text-label); color: var(--text-dim); }
.header-center { justify-content: center; }
.header-center .ff-searchfield { width: min(560px, 50vw); }
@media (max-width: 980px) { .brand-text { display: none; } .header-center .ff-searchfield { max-width: 360px; } }
@media (max-width: 760px) { .app-header { padding: 0 var(--sp-sm); gap: var(--sp-sm); } }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/organisms/shell/AppHeader.vue
git commit -m "feat(organisms): add AppHeader with token styling + atom imports"
```

---

### Task 8: UserMenu organism

**Files:**
- Create: `web/src/components/organisms/shell/UserMenu.vue`

Extracted from Header.vue's dropdown menu. Uses MenuItem, Avatar, Divider atoms/molecules.

- [ ] **Step 1: Write `UserMenu.vue`**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../../store/user';
import { useLocaleStore } from '../../store/locale';
import Avatar from '../../molecules/Avatar.vue';
import MenuItem from '../../molecules/MenuItem.vue';
import Divider from '../../atoms/Divider.vue';

const router = useRouter();
const userStore = useUserStore();
const localeStore = useLocaleStore();
const t = localeStore.t;

const open = ref(false);
const isAdmin = userStore.user?.role === 'admin';

function handleLogout() {
  userStore.logout();
  router.push('/login');
}

function close() { open.value = false; }
</script>

<template>
  <div class="user-menu">
    <button class="user-trigger" @click="open = !open" :aria-expanded="open">
      <Avatar :name="userStore.user?.username || '?'" size="sm" />
      <span class="user-name">{{ userStore.user?.username || t('header.menu.defaultUserName') }}</span>
      <Icon name="chevronDown" :size="12" />
    </button>
    <div v-if="open" class="user-dropdown" @click.self="close">
      <div class="user-dropdown-inner">
        <div class="user-info">
          <strong>{{ userStore.user?.username || t('header.menu.defaultUserName') }}</strong>
          <span v-if="isAdmin" class="user-role">{{ t('header.menu.admin') }}</span>
          <small>{{ userStore.user?.email || t('header.menu.defaultEmail') }}</small>
        </div>
        <Divider />
        <MenuItem icon="folder" @click="router.push('/profile'); close()">{{ t('header.menu.profile') }}</MenuItem>
        <MenuItem icon="more" @click="router.push('/settings'); close()">{{ t('header.menu.settings') }}</MenuItem>
        <MenuItem v-if="isAdmin" icon="search" @click="router.push('/dashboard'); close()">{{ t('header.menu.dashboard') }}</MenuItem>
        <Divider />
        <MenuItem variant="danger" icon="trash" @click="handleLogout(); close()">{{ t('header.menu.logout') }}</MenuItem>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import Icon from '../../atoms/Icon.vue';
export default { components: { Icon } };
</script>

<style scoped>
.user-menu { position: relative; }
.user-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  height: 32px; padding: 0 10px 0 6px;
  background: var(--surface-raised); border: 1px solid var(--border-default); border-radius: var(--radius-sm);
  color: var(--text-secondary); font-family: var(--font-sans); font-size: var(--text-body);
  cursor: pointer; transition: border-color var(--mo-duration-fast) var(--mo-easing), background-color var(--mo-duration-fast) var(--mo-easing);
}
.user-trigger:hover { background: var(--surface-inset); border-color: var(--border-strong); color: var(--text-primary); }
.user-name { max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-dropdown { position: absolute; top: calc(100% + 6px); right: 0; z-index: 50; }
.user-dropdown-inner {
  width: 220px; padding: 6px;
  background: var(--surface-raised); border: 1px solid var(--border-default);
  box-shadow: var(--shadow-overlay);
}
.user-info { padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.user-info strong { font-size: var(--text-body); color: var(--text-primary); }
.user-info small { font-size: var(--text-small); color: var(--text-dim); }
.user-role {
  display: inline-flex; align-self: flex-start;
  font-size: var(--text-label); font-family: var(--font-mono); letter-spacing: var(--tracking-wide); text-transform: uppercase;
  padding: 1px 6px; border: 1px solid rgba(var(--ac-rgb), 0.35); color: var(--ac); background: rgba(var(--ac-rgb), 0.1);
  border-radius: var(--radius-md);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/organisms/shell/UserMenu.vue
git commit -m "feat(organisms): add UserMenu with Avatar + MenuItem atoms"
```

---

### Task 9: LeftSidebar + StorageStatusWidget

**Files:**
- Create: `web/src/components/organisms/shell/LeftSidebar.vue`
- Create: `web/src/components/organisms/shell/StorageStatusWidget.vue`

LeftSidebar is migrated from `components/layout/LeftSidebar.vue`. Storage widget is extracted into its own organism.

- [ ] **Step 1: Write `StorageStatusWidget.vue`**

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getStorageStats } from '../../api/user';
import type { StorageStats } from '../../types/user';
import Text from '../../atoms/Text.vue';
import MonoNumber from '../../atoms/MonoNumber.vue';
import Bar from '../../atoms/Bar.vue';

const props = defineProps<{ collapsed: boolean }>();

const storage = ref<StorageStats | null>(null);

const pct = computed(() => {
  if (!storage.value || storage.value.storageLimit === 0) return 0;
  return Math.min(1, storage.value.storageUsed / storage.value.storageLimit);
});
const pctLabel = computed(() => Math.round(pct.value * 100));

function fmt(bytes: number, decimals = 1) {
  if (bytes === 0) return '0 B';
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals < 0 ? 0 : decimals))} ${sizes[i]}`;
}

onMounted(() => {
  getStorageStats().then(s => storage.value = s);
});
</script>

<template>
  <div class="storage-widget" :class="{ 'storage-widget--collapsed': collapsed }">
    <div class="storage-head">
      <Text v-if="!collapsed" variant="label">Storage</Text>
      <MonoNumber :value="`${pctLabel}%`" accent />
    </div>
    <Bar :value="pct" :tone="pct > 0.9 ? 'error' : 'accent'" />
    <p v-if="!collapsed" class="storage-meta">
      {{ fmt(storage?.storageUsed ?? 0) }} / {{ fmt(storage?.storageLimit ?? 0) }}
    </p>
  </div>
</template>

<style scoped>
.storage-widget { padding: 10px; background: var(--surface-inset); border: 1px solid var(--border-subtle); }
.storage-widget--collapsed { padding: 8px; }
.storage-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.storage-meta { margin: 6px 0 0; font-size: var(--text-small); color: var(--text-dim); }
</style>
```

- [ ] **Step 2: Write `LeftSidebar.vue`**

```vue
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useFileStore } from '../../store/file';
import type { ContentItem, FolderItem } from '../../types/file';
import { eventBus } from '../../utils/eventBus';
import { useLocaleStore } from '../../store/locale';
import FileTreeNode from '../../common/FileTreeNode.vue';
import Icon from '../../atoms/Icon.vue';
import StorageStatusWidget from './StorageStatusWidget.vue';

const props = defineProps<{ collapsed: boolean }>();

const fileStore = useFileStore();
const localeStore = useLocaleStore();
const t = localeStore.t;

const rootNode = ref<FolderItem>({
  id: 'root', name: t('sidebar.myFiles'), itemType: 'folder', size: 0, ownerName: '',
  updatedAt: new Date().toISOString(), createdAt: new Date().toISOString(), parentFolderId: null,
});
const treeKey = ref(0);

const navItems = computed(() => [
  { to: '/files', label: t('sidebar.myFiles'), icon: 'folder' as const },
  { to: '/shared', label: t('sidebar.shared'), icon: 'share' as const },
  { to: '/agent', label: t('sidebar.agent'), icon: 'more' as const },
  { to: '/trash', label: t('sidebar.recycleBin'), icon: 'trash' as const },
]);

function handleTreeDrop({ sourceItemIds, targetFolderId, targetFolderName }: any) {
  eventBus.emit('move-items', { sourceItemIds, targetFolderId, targetFolderName });
}
function handleTreeNavigate(itemId: string) {
  const isFolder = itemId === 'root' || !!findFolderInTree([rootNode.value], itemId);
  if (isFolder) { fileStore.navigateToFolder(itemId); return; }
  fileStore.selectedFile = { id: itemId, itemType: 'file' } as ContentItem;
}
function findFolderInTree(nodes: FolderItem[], id: string): FolderItem | null {
  for (const node of nodes) { if (node.id === id) return node; }
  return null;
}
function refreshTree() { treeKey.value += 1; }

watch(() => localeStore.locale, () => {
  rootNode.value = { ...rootNode.value, name: t('sidebar.myFiles') };
});

onMounted(() => { eventBus.on('refresh-file-tree', refreshTree); });
onUnmounted(() => { eventBus.off('refresh-file-tree', refreshTree); });
</script>

<template>
  <aside :class="['left-sidebar', { collapsed }]">
    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.to" class="nav-item">
          <router-link :to="item.to" class="nav-link" active-class="active">
            <Icon :name="item.icon" :size="16" />
            <span v-if="!collapsed" class="link-text">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div v-if="!collapsed" class="tree-panel">
      <Text variant="label">Workspace</Text>
      <div class="tree-scroll">
        <FileTreeNode :key="treeKey" :node="rootNode" :level="0" @drop-on-folder="handleTreeDrop" @navigate="handleTreeNavigate" />
      </div>
    </div>

    <StorageStatusWidget :collapsed="collapsed" />
  </aside>
</template>

<script lang="ts">
import Text from '../../atoms/Text.vue';
export default { components: { Text } };
</script>

<style scoped>
.left-sidebar {
  width: var(--sidebar-left-width);
  background: var(--surface-raised);
  border-right: 1px solid var(--border-default);
  flex-shrink: 0; display: flex; flex-direction: column; gap: var(--sp-md);
  padding: var(--sp-md);
  transition: width var(--mo-duration-mid) var(--mo-easing);
}
.left-sidebar.collapsed { width: var(--sidebar-left-collapsed-width); }
.nav-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.nav-link {
  height: var(--row-h); display: flex; align-items: center; gap: 10px;
  padding: 0 10px; border-radius: var(--radius-sm);
  color: var(--text-secondary); text-decoration: none;
  transition: color var(--mo-duration-fast) var(--mo-easing), background-color var(--mo-duration-fast) var(--mo-easing);
}
.nav-link:hover { background: var(--surface-inset); color: var(--text-primary); }
.nav-link.active { background: rgba(var(--ac-rgb), 0.12); color: var(--ac); font-weight: var(--weight-medium); }
.left-sidebar.collapsed .nav-link { justify-content: center; padding: 0; }
.link-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tree-panel { min-height: 0; flex: 1; display: flex; flex-direction: column; border-top: 1px solid var(--border-subtle); padding-top: var(--sp-md); gap: var(--sp-sm); }
.tree-scroll { flex: 1; overflow: auto; padding-right: 4px; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/organisms/shell/LeftSidebar.vue web/src/components/organisms/shell/StorageStatusWidget.vue
git commit -m "feat(organisms): add LeftSidebar + StorageStatusWidget with token styling"
```

---

### Task 10: RightSidebar organism

**Files:**
- Create: `web/src/components/organisms/shell/RightSidebar.vue`

This is a **direct migration** of `components/layout/RightSidebar.vue`. The template/script is preserved; only scoped CSS is rewritten with tokens. The file is large (~450 lines of script), so we do not refactor the preview logic in P2.

- [ ] **Step 1: Copy the existing RightSidebar.vue and replace only the `<style scoped>` block**

Read `web/src/components/layout/RightSidebar.vue`, copy its `<script setup>` and `<template>` verbatim into `web/src/components/organisms/shell/RightSidebar.vue`, then replace `<style scoped>` with token-based CSS.

**Style replacement:**
```css
<style scoped>
.right-sidebar {
  width: var(--sidebar-right-width);
  margin-right: calc(-1 * var(--sidebar-right-width));
  border-left: 1px solid var(--border-default);
  background: var(--surface-raised);
  display: flex; flex-direction: column;
  transition: margin-right var(--mo-duration-mid) var(--mo-easing);
}
.right-sidebar.visible { margin-right: 0; }
.sidebar-header { padding: var(--sp-md); border-bottom: 1px solid var(--border-subtle); display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-sm); }
.filename { font-size: var(--text-h2); line-height: var(--leading-snug); margin: 0; word-break: break-all; color: var(--text-primary); }
.meta { margin: 4px 0 0; color: var(--text-dim); font-size: var(--text-small); }
.close-btn, .action-btn, .pdf-btn {
  height: var(--row-h); border-radius: var(--radius-sm); border: 1px solid var(--border-default);
  background: var(--surface-raised); color: var(--text-secondary); cursor: pointer; padding: 0 10px;
  font-family: var(--font-sans); font-size: var(--text-small);
  transition: background-color var(--mo-duration-fast) var(--mo-easing), color var(--mo-duration-fast) var(--mo-easing);
}
.close-btn { width: var(--row-h); padding: 0; }
.close-btn:hover, .action-btn:hover, .pdf-btn:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }
.sidebar-actions { display: flex; gap: 8px; padding: 10px var(--sp-md) 0; }
.sidebar-content { flex: 1; padding: var(--sp-md); overflow: auto; }
.sidebar-placeholder, .state { flex: 1; display: flex; align-items: center; justify-content: center; text-align: center; color: var(--text-dim); padding: var(--sp-lg); }
.state.error { color: var(--status-error); }
.text-preview { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: var(--font-mono); font-size: var(--text-small); line-height: var(--leading-normal); color: var(--text-secondary); background: var(--surface-inset); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: var(--sp-md); }
.image-preview img, .media-preview audio, .media-preview video { width: 100%; border-radius: var(--radius-sm); }
.media-preview video { max-height: 320px; }
.pdf-preview { display: flex; flex-direction: column; gap: 10px; }
.pdf-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--text-secondary); font-size: var(--text-small); }
.pdf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pdf-canvas-wrap { border: 1px solid var(--border-default); border-radius: var(--radius-sm); background: #fff; overflow: auto; }
.pdf-canvas-wrap canvas { display: block; margin: 0 auto; max-width: 100%; height: auto; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/organisms/shell/RightSidebar.vue
git commit -m "feat(organisms): add RightSidebar (preview logic migrated, CSS tokenised)"
```

---

### Task 11: Footer organism

**Files:**
- Create: `web/src/components/organisms/shell/Footer.vue`

- [ ] **Step 1: Write `Footer.vue`**

```vue
<template>
  <footer class="app-footer">
    <p>&copy; {{ new Date().getFullYear() }} FileFlash. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">Terms of Service</a>
      <a href="#">Privacy Policy</a>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  display: flex; align-items: center; justify-content: space-between;
  height: var(--layout-footer-height);
  padding: 0 var(--sp-lg);
  background: var(--surface-raised);
  border-top: 1px solid var(--border-default);
  color: var(--text-dim);
  font-size: var(--text-small);
  flex-shrink: 0;
}
.footer-links { display: flex; gap: var(--sp-md); }
.footer-links a { color: var(--text-dim); text-decoration: none; transition: color var(--mo-duration-fast) var(--mo-easing); }
.footer-links a:hover { color: var(--text-primary); }
</style>
```

- [ ] **Step 2: Update `organisms/index.ts`**

```ts
export { default as AppHeader } from './shell/AppHeader.vue';
export { default as LeftSidebar } from './shell/LeftSidebar.vue';
export { default as RightSidebar } from './shell/RightSidebar.vue';
export { default as Footer } from './shell/Footer.vue';
export { default as StorageStatusWidget } from './shell/StorageStatusWidget.vue';
export { default as UserMenu } from './shell/UserMenu.vue';
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/organisms/
git commit -m "feat(organisms): add Footer + export all shell organisms from barrel"
```

---

## Phase C — Route Hierarchy Refactor (Tasks 12–13)

### Task 12: Rewrite `router/routes.ts`

**Files:**
- Modify: `web/src/router/routes.ts`

- [ ] **Step 1: Replace the file**

```ts
import type { RouteRecordRaw } from 'vue-router';
import MainLayout from '../components/templates/MainLayout.vue';
import AuthLayout from '../components/templates/AuthLayout.vue';
import BareLayout from '../components/templates/BareLayout.vue';
import ShareLayout from '../components/templates/ShareLayout.vue';
import AgentLayout from '../components/templates/AgentLayout.vue';

const devRoutes: Array<RouteRecordRaw> = import.meta.env.DEV
  ? [{
      path: '/__dev/library',
      name: 'DevLibrary',
      component: () => import('../pages/__dev/index.ts'),
      meta: { requiresAuth: false },
    }]
  : [];

export const routes: Array<RouteRecordRaw> = [
  ...devRoutes,

  // Public auth flows
  {
    path: '/login',
    name: 'Login',
    component: AuthLayout,
    children: [{ path: '', component: () => import('../pages/login/index.ts') }],
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: AuthLayout,
    children: [{ path: '', component: () => import('../pages/register/index.ts') }],
    meta: { requiresAuth: false },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: AuthLayout,
    children: [{ path: '', component: () => import('../pages/forgot-password/index.ts') }],
    meta: { requiresAuth: false },
  },
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: BareLayout,
    children: [{ path: '', component: () => import('../pages/verify-email/index.ts') }],
    meta: { requiresAuth: false },
  },

  // Public share
  {
    path: '/share/:shareLink',
    name: 'ShareAccess',
    component: ShareLayout,
    children: [{ path: '', component: () => import('../pages/share/index.ts') }],
    meta: { requiresAuth: false },
  },

  // Private (requiresAuth)
  {
    path: '/',
    name: 'Home',
    component: MainLayout,
    redirect: '/files',
    meta: { requiresAuth: true },
    children: [
      { path: 'files', name: 'MyFiles', component: () => import('../pages/files/index.ts'), meta: { navId: 'my-files' } },
      { path: 'shared', name: 'Shared', component: () => import('../pages/shared/index.ts'), meta: { navId: 'shared' } },
      { path: 'trash', name: 'Trash', component: () => import('../pages/trash/index.ts'), meta: { navId: 'trash' } },
      { path: 'profile', name: 'Profile', component: () => import('../pages/profile/index.ts'), meta: { navId: 'profile' } },
      { path: 'settings', name: 'Settings', component: () => import('../pages/settings/index.ts'), meta: { navId: 'settings' } },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../pages/dashboard/index.ts'), meta: { navId: 'dashboard', requiresAdmin: true } },
    ],
  },

  // Agent workspace (private)
  {
    path: '/agent',
    component: AgentLayout,
    meta: { requiresAuth: true, navId: 'agent' },
    children: [
      { path: '', name: 'AgentWorkspace', component: () => import('../pages/agent/workspace/index.ts'), meta: { navId: 'agent' } },
      { path: 'skills', name: 'AgentSkills', component: () => import('../pages/agent/skills/index.ts'), meta: { navId: 'agent' } },
    ],
  },

  // Legacy redirect
  { path: '/skills', name: 'SkillsLegacy', redirect: '/agent/skills' },

  // Catch-all
  { path: '/:pathMatch(.*)*', name: 'NotFound', redirect: '/' },
];
```

- [ ] **Step 2: Verify type-check**

```bash
cd web && bun run check
```

Expected: exit 0. If there are import path errors (e.g., `../../common/FileTreeNode.vue` from `LeftSidebar.vue` needs to exist), fix them.

- [ ] **Step 3: Commit**

```bash
git add web/src/router/routes.ts
git commit -m "refactor(router): restructure routes around new templates (Auth/Bare/Share/Main/Agent)"
```

---

### Task 13: Verify "切页像刷新" fix

**Files:** none modified.

- [ ] **Step 1: Start dev server**

```bash
cd web && bun run dev
```

- [ ] **Step 2: Navigate between authenticated pages**

Log in, then click between:
- /files
- /shared
- /trash
- /settings

Verify:
- Header, sidebar, footer **do not** fade out/in
- Only the content area transitions (subtle scale or slide)
- No "page refresh" feeling

- [ ] **Step 3: Navigate between auth pages**

Visit `/login`, click to `/register`, `/forgot-password`.
Verify:
- Auth card stays in place; only the inner form transitions

- [ ] **Step 4: Stop dev server**

```bash
# Ctrl+C
```

No commit — this is verification.

---

## Phase D — Build + Test Gate (Task 14)

### Task 14: Final verification

- [ ] **Step 1: Full test suite**

```bash
cd web && bun run test
```

Expected: all existing atom/molecule tests pass. No new tests are added in P2 (templates/organisms are integration-level; tests come later or are verified manually).

- [ ] **Step 2: Type-check**

```bash
cd web && bun run check
```

Expected: exit 0.

- [ ] **Step 3: Production build**

```bash
cd web && bun run build
```

Expected: exits 0.

- [ ] **Step 4: Update progress memory**

Update `docs/superpowers/frontend_redesign_progress.md`:

Move P2 to "已完成" with the sub-deliverables:
- 5 templates: MainLayout / AuthLayout / BareLayout / ShareLayout / AgentLayout
- 6 shell organisms: AppHeader / LeftSidebar / RightSidebar / Footer / StorageStatusWidget / UserMenu
- Route hierarchy refactored; "切页像刷新" fixed
- App.vue stripped of top-level transition

---

## Self-Review

1. **Spec coverage** (§5 Routing):
   - [x] App.vue transition removed → Task 5
   - [x] Templates have internal content-only transition → Tasks 1–4
   - [x] Motion token linkage (`[data-motion]`) on `.page-fade-*` → Task 1
   - [x] Route hierarchy uses layouts as route components → Task 12

2. **Backward compatibility**:
   - [x] Existing `components/layout/*.vue` files are **not deleted** (P8 cleanup)
   - [x] Old routes still resolve (old `MainLayout` import commented out / replaced)
   - [x] `themeStore.toggleTheme()` still works (P6 replacement deferred)
   - [x] `localStorage.getItem('theme')` still read by hydration script

3. **Constraints honored**:
   - [x] No existing page `.vue` files modified
   - [x] No backend API changes
   - [x] Naive UI providers remain in App.vue
   - [x] All new CSS uses token variables; no hardcoded colors
   - [x] No `translateY(-1px)` or `cubic-bezier(0.4, 0, 0.2, 1)` in new code

4. **Quality gates**:
   - [x] `bun run test` passes
   - [x] `bun run check` passes
   - [x] `bun run build` passes
   - [x] Manual smoke: header/sidebar/footer stable during navigation

If any checkbox is unchecked: **stop**, fix, re-run, do not proceed to P3.
