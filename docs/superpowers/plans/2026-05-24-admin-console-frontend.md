# Admin Console Frontend Implementation Plan (Plan B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `web/src/pages/dashboard/Dashboard.vue` 单页式管理面板重构为 `web/src/pages/console/` 多页式 Console（9 个子页 + 共享侧栏与组件），并补齐与 Plan A 后端契约对齐的 api 函数与 mock。

**Architecture:** 复用 `MainLayout` 顶层框架，在其下嵌一层 `ConsoleLayout`（含 `ConsoleSidebar` + `<router-view/>`）；9 个子页 lazy import；共享展示组件不持有数据，由子页 `onMounted` 拉数据后注入 props。视觉沿用 [[frontend_aesthetic]] 工业风。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript + Vue Router + Pinia (现有 userStore) + bun 工具链。

**Reference Spec:** `docs/superpowers/specs/2026-05-24-admin-console-design.md`
**Reference Backend Plan:** `docs/superpowers/plans/2026-05-24-admin-console-backend.md`

**前置知识（执行前必读）**

1. 工具链：`web/` 目录下一律用 `bun`（`bun install`, `bun run dev`, `bun run check`, `bun run build`），不用 npm/npx ([[tooling_bun]])。
2. 风格基线（[[frontend_aesthetic]]）：深色 + Electric Lime 主色 + tabular-nums + 直角硬边；不引入新主题变量；表格、按钮、徽章遵循现有 `components/atoms` / `components/molecules` 的 token。
3. mock 体系：`web/src/mock/handlers/*.ts` 已经对 Dashboard.vue 涉及的 admin 接口提供 mock；Plan B 中只需补 mock 与 Plan A 的 router 形状对齐（必要时新增 `/admin/logs`, `/admin/storage/summary`, `/admin/notifications/*` 等差异路径）。
4. api 客户端：`web/src/utils/http.ts` 已经自带响应拦截器；errors 统一冒泡到 `ui.toast`，子页**不**自己 try/catch。
5. i18n：`web/src/i18n/messages.ts` 单文件、扁平 dotted-key；新增 `console.*` 命名空间，中英都要补。
6. **依赖关系**：Plan B 可以独立完成（mock 兜底），无需等待 Plan A；上线时把 `web/src/mock/index.ts` 的 `setupMocks()` 注释或加环境开关即可切到真实后端。
7. 旧 `Dashboard.vue`：在 Task 12 删除前，先确认 router 重定向 / 链接均已切到 `/console/overview`，避免书签失效。

---

## File Structure

**新建**

```
web/src/pages/console/
  ConsoleLayout.vue
  ConsoleSidebar.vue
  index.ts                     ← 总入口（仅供 router 引用）
  overview/OverviewPage.vue
  overview/index.ts
  users/UsersPage.vue
  users/index.ts
  storage/StoragePage.vue
  storage/index.ts
  content/ContentPage.vue
  content/index.ts
  moderation/ModerationPage.vue
  moderation/index.ts
  system/SystemPage.vue
  system/index.ts
  logs/LogsPage.vue
  logs/index.ts
  notifications/NotificationsPage.vue
  notifications/index.ts
  rules/RulesPage.vue
  rules/index.ts

web/src/components/console/
  KpiCard.vue
  TrendChart.vue
  FilterBar.vue
  AdminTable.vue
  StatusBadge.vue
  BroadcastComposer.vue
  QuotaEditor.vue
  index.ts                     ← barrel export
```

**修改**

```
web/src/api/storage.ts          ← + getAdminStorageSummary
web/src/api/log.ts              ← + getAdminLogs
web/src/api/notification.ts     ← broadcast 路径切到 /admin/notifications/broadcast
web/src/types/log.d.ts          ← + GetAdminLogsRequest（如缺）
web/src/types/notification.d.ts ← + AdminNotificationItem（如缺）
web/src/mock/handlers/log.ts    ← + /admin/logs handler
web/src/mock/handlers/notification.ts ← /admin/notifications/* handlers
web/src/mock/handlers/storage.ts ← + /admin/storage/summary handler
web/src/router/routes.ts        ← 加 /console 嵌套，/dashboard redirect
web/src/components/organisms/shell/UserMenu.vue ← 把 dashboard 入口换成 console
web/src/i18n/messages.ts        ← + 'console.*' keys + 修改 'header.menu.dashboard' → 'header.menu.console'

# 删除
web/src/pages/dashboard/Dashboard.vue
web/src/pages/dashboard/index.ts
```

---

## Task 0: api / types / mock 对齐 Plan A 契约

**Files:**
- Modify: `web/src/api/storage.ts`, `web/src/api/log.ts`, `web/src/api/notification.ts`
- Modify: `web/src/types/log.d.ts`, `web/src/types/notification.d.ts`
- Modify: `web/src/mock/handlers/log.ts`, `web/src/mock/handlers/notification.ts`, `web/src/mock/handlers/storage.ts`

- [ ] **Step 0.1: 加 `getAdminStorageSummary`**

Edit `web/src/api/storage.ts`，在 `getStorageSummary` 之后追加：

```typescript
/**
 * 管理员视角：全局存储概览
 */
export const getAdminStorageSummary = () => {
  return http.get<StorageStats & { fileCount: number; userCount: number }>(
    '/admin/storage/summary'
  );
};
```

- [ ] **Step 0.2: 加 `getAdminLogs` + 类型**

Edit `web/src/types/log.d.ts`，在文件末追加：

```typescript
export interface GetAdminLogsRequest {
  userId?: string;
  operation?: string;
  result?: 'success' | 'failure';
  fromAt?: string;
  toAt?: string;
  page?: number;
  perPage?: number;
}
```

Edit `web/src/api/log.ts` 增加：

```typescript
import type { LogsList, GetLogsRequest, GetAdminLogsRequest } from '../types/log';

export const getAdminLogs = (params: GetAdminLogsRequest) => {
  return http.get<LogsList>('/admin/logs', params);
};
```

- [ ] **Step 0.3: 修改 `broadcastNotification` 指向 `/admin/notifications/broadcast`**

Edit `web/src/api/notification.ts`：

```typescript
export const broadcastNotification = (message: string, title?: string) => {
  return http.post<{ broadcastId: string; recipientCount: number; sentAt: string }>(
    '/admin/notifications/broadcast',
    { message, title, type: 'system' },
  );
};
```

并在该文件追加：

```typescript
export const getAdminNotifications = (params: { page?: number; perPage?: number; status?: string; type?: string }) => {
  return http.get<NotificationsList>('/admin/notifications', params);
};

export const archiveAdminNotification = (notificationId: string) => {
  return http.delete<{ notificationId: string; status: string }>(
    `/admin/notifications/${notificationId}`,
  );
};
```

- [ ] **Step 0.4: 补 mock — `/admin/storage/summary`**

Edit `web/src/mock/handlers/storage.ts`，在 `setupStorageMocks` 中追加：

```typescript
Mock.mock(/\/api\/v1\/admin\/storage\/summary$/, 'get', () => {
  const used = mockUsers.reduce((sum, u) => sum + u.storageUsed, 0);
  const limit = mockUsers.reduce((sum, u) => sum + u.storageLimit, 0);
  return {
    success: true,
    code: 200,
    data: {
      storageUsed: used,
      storageLimit: limit,
      storagePercentage: limit ? (used / limit) * 100 : 0,
      fileCount: 42,
      userCount: mockUsers.length,
      updatedAt: new Date().toISOString(),
    },
  };
});
```

> **注：** 如果 mock state 已有等价 handler 指向 `/storage/summary`，**保留**它（用户自己视图），新增的是 `/admin/storage/summary`。

- [ ] **Step 0.5: 补 mock — `/admin/logs` 与 `/admin/notifications/*`**

Edit `web/src/mock/handlers/log.ts`：

```typescript
Mock.mock(/\/api\/v1\/admin\/logs(?:\?.*)?$/, 'get', (options) => {
  const url = new URL(options.url, 'http://localhost');
  const page = Number(url.searchParams.get('page') || 1);
  const perPage = Number(url.searchParams.get('perPage') || 20);
  // 复用现有 mockLogs
  const slice = mockLogs.slice((page - 1) * perPage, page * perPage);
  return {
    success: true,
    code: 200,
    data: {
      logs: slice,
      pagination: {
        totalItems: mockLogs.length,
        totalPages: Math.max(1, Math.ceil(mockLogs.length / perPage)),
        perPage, currentPage: page,
        hasPrev: page > 1,
        hasNext: page * perPage < mockLogs.length,
      },
    },
  };
});
```

Edit `web/src/mock/handlers/notification.ts`：

```typescript
Mock.mock(/\/api\/v1\/admin\/notifications(?:\?.*)?$/, 'get', (options) => {
  const url = new URL(options.url, 'http://localhost');
  const page = Number(url.searchParams.get('page') || 1);
  const perPage = Number(url.searchParams.get('perPage') || 20);
  const slice = mockNotifications.slice((page - 1) * perPage, page * perPage);
  return {
    success: true,
    code: 200,
    data: {
      items: slice,
      pagination: {
        totalItems: mockNotifications.length,
        totalPages: Math.max(1, Math.ceil(mockNotifications.length / perPage)),
        perPage, currentPage: page,
        hasPrev: page > 1,
        hasNext: page * perPage < mockNotifications.length,
      },
    },
  };
});

Mock.mock(/\/api\/v1\/admin\/notifications\/broadcast$/, 'post', (options) => {
  const body = JSON.parse(options.body || '{}');
  addNotification(body.message);
  return {
    success: true,
    code: 200,
    data: {
      broadcastId: 'mock-' + Date.now(),
      recipientCount: mockUsers.length,
      sentAt: new Date().toISOString(),
    },
  };
});

Mock.mock(/\/api\/v1\/admin\/notifications\/([^/]+)$/, 'delete', (options) => {
  const id = (options.url.match(/\/api\/v1\/admin\/notifications\/([^/]+)/) || [])[1];
  return {
    success: true,
    code: 200,
    data: { notificationId: id, status: 'archived' },
  };
});
```

- [ ] **Step 0.6: 类型检查 + commit**

Run: `cd web && bun run check`
Expected: 0 errors

```bash
git add web/src/api/storage.ts web/src/api/log.ts web/src/api/notification.ts web/src/types/log.d.ts web/src/mock/handlers/storage.ts web/src/mock/handlers/log.ts web/src/mock/handlers/notification.ts
git commit -m "feat(web): align api+mock with Plan A admin contracts"
```

---

## Task 1: ConsoleLayout + Sidebar + 路由

**Files:**
- Create: `web/src/pages/console/ConsoleLayout.vue`, `ConsoleSidebar.vue`, `index.ts`
- Modify: `web/src/router/routes.ts`

- [ ] **Step 1.1: 写 ConsoleSidebar**

`web/src/pages/console/ConsoleSidebar.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useLocaleStore } from '../../store/locale';

const route = useRoute();
const router = useRouter();
const t = useLocaleStore().t;

interface NavItem { key: string; path: string; labelKey: string }

const items: NavItem[] = [
  { key: 'overview',      path: '/console/overview',      labelKey: 'console.nav.overview' },
  { key: 'users',         path: '/console/users',         labelKey: 'console.nav.users' },
  { key: 'storage',       path: '/console/storage',       labelKey: 'console.nav.storage' },
  { key: 'content',       path: '/console/content',       labelKey: 'console.nav.content' },
  { key: 'moderation',    path: '/console/moderation',    labelKey: 'console.nav.moderation' },
  { key: 'system',        path: '/console/system',        labelKey: 'console.nav.system' },
  { key: 'logs',          path: '/console/logs',          labelKey: 'console.nav.logs' },
  { key: 'notifications', path: '/console/notifications', labelKey: 'console.nav.notifications' },
  { key: 'rules',         path: '/console/rules',         labelKey: 'console.nav.rules' },
];

const activeKey = computed(() => items.find(i => route.path.startsWith(i.path))?.key);
</script>

<template>
  <aside class="console-sidebar">
    <div class="console-sidebar__header">{{ t('console.title') }}</div>
    <nav class="console-sidebar__nav">
      <button
        v-for="item in items"
        :key="item.key"
        class="console-sidebar__item"
        :class="{ 'is-active': activeKey === item.key }"
        @click="router.push(item.path)"
      >
        {{ t(item.labelKey) }}
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.console-sidebar {
  width: 200px;
  background: var(--surface-base);
  border-right: 1px solid var(--border-default);
  display: flex; flex-direction: column;
}
.console-sidebar__header {
  padding: 16px;
  font-family: var(--font-mono);
  font-size: var(--text-caption);
  color: var(--text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.console-sidebar__nav { display: flex; flex-direction: column; }
.console-sidebar__item {
  display: block;
  padding: 10px 16px;
  background: transparent; border: none;
  color: var(--text-secondary);
  font-family: var(--font-sans); font-size: var(--text-body);
  text-align: left; cursor: pointer;
  border-left: 2px solid transparent;
}
.console-sidebar__item:hover { background: var(--surface-raised); }
.console-sidebar__item.is-active {
  color: var(--text-primary);
  background: var(--surface-raised);
  border-left-color: var(--accent-primary);
}
</style>
```

- [ ] **Step 1.2: 写 ConsoleLayout**

`web/src/pages/console/ConsoleLayout.vue`：

```vue
<script setup lang="ts">
import ConsoleSidebar from './ConsoleSidebar.vue';
</script>

<template>
  <div class="console-layout">
    <ConsoleSidebar />
    <main class="console-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.console-layout {
  display: flex;
  min-height: 100%;
  background: var(--surface-base);
}
.console-main {
  flex: 1;
  min-width: 0;
  padding: 24px;
  overflow: auto;
}
</style>
```

- [ ] **Step 1.3: 写入口 index.ts（每个子目录都需要类似一个）**

`web/src/pages/console/index.ts`：

```typescript
export { default as ConsoleLayout } from './ConsoleLayout.vue';
```

(每个子页的 `<dir>/index.ts` 同样默认导出页面组件，例：)

`web/src/pages/console/overview/index.ts`（占位，Task 3 才实现）：

```typescript
import OverviewPage from './OverviewPage.vue';
export default OverviewPage;
```

> 在本任务里，先为 9 个子页都各建一个空 `.vue`（含最小模板 `<template><div>{{ pageKey }}</div></template>`）+ `index.ts`，让路由可以挂上不报错。代码示例：

```vue
<!-- web/src/pages/console/overview/OverviewPage.vue (placeholder) -->
<script setup lang="ts">
const pageKey = 'overview';
</script>

<template><div>{{ pageKey }} (TODO)</div></template>
```

为 9 个子目录都生成同样形状的 placeholder：`overview, users, storage, content, moderation, system, logs, notifications, rules`。

- [ ] **Step 1.4: 修改 router/routes.ts**

`web/src/router/routes.ts` —— 在 `children` 数组中把 `dashboard` 路由替换为 console 嵌套：

```typescript
// 删除原 dashboard 子路由块；新增：
{
  path: 'console',
  component: () => import('../pages/console/ConsoleLayout.vue'),
  meta: { navId: 'console', requiresAdmin: true },
  children: [
    { path: '', redirect: '/console/overview' },
    { path: 'overview',      name: 'ConsoleOverview',      component: () => import('../pages/console/overview/index.ts') },
    { path: 'users',         name: 'ConsoleUsers',         component: () => import('../pages/console/users/index.ts') },
    { path: 'storage',       name: 'ConsoleStorage',       component: () => import('../pages/console/storage/index.ts') },
    { path: 'content',       name: 'ConsoleContent',       component: () => import('../pages/console/content/index.ts') },
    { path: 'moderation',    name: 'ConsoleModeration',    component: () => import('../pages/console/moderation/index.ts') },
    { path: 'system',        name: 'ConsoleSystem',        component: () => import('../pages/console/system/index.ts') },
    { path: 'logs',          name: 'ConsoleLogs',          component: () => import('../pages/console/logs/index.ts') },
    { path: 'notifications', name: 'ConsoleNotifications', component: () => import('../pages/console/notifications/index.ts') },
    { path: 'rules',         name: 'ConsoleRules',         component: () => import('../pages/console/rules/index.ts') },
  ],
},
{ path: '/dashboard', redirect: '/console/overview' },
```

旧 `dashboard` route 移除（注意 `/` 父路由还是 MainLayout，console 是它的 child）。

- [ ] **Step 1.5: 类型检查 + 启动 dev server 烟测**

```bash
cd web && bun run check
cd web && bun run dev  # 浏览器访问 http://localhost:5173/console
```

预期：以 admin 用户登录后访问 `/console`，重定向至 `/console/overview`，能看到 sidebar + "overview (TODO)" 占位。

- [ ] **Step 1.6: Commit**

```bash
git add web/src/pages/console web/src/router/routes.ts
git commit -m "feat(web): scaffold Console layout, sidebar, and 9 subpage routes"
```

---

## Task 2: 共享组件（components/console/）

**Files:**
- Create: `web/src/components/console/KpiCard.vue`, `StatusBadge.vue`, `FilterBar.vue`, `AdminTable.vue`, `TrendChart.vue`, `BroadcastComposer.vue`, `QuotaEditor.vue`, `index.ts`

- [ ] **Step 2.1: KpiCard.vue**

```vue
<script setup lang="ts">
defineProps<{
  title: string;
  value: string | number;
  unit?: string;
  accent?: 'primary' | 'warning' | 'danger';
}>();
</script>

<template>
  <article class="kpi-card" :class="accent ? `is-${accent}` : ''">
    <h3 class="kpi-card__title">{{ title }}</h3>
    <div class="kpi-card__value">
      <strong>{{ value }}</strong>
      <small v-if="unit">{{ unit }}</small>
    </div>
  </article>
</template>

<style scoped>
.kpi-card {
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  padding: 16px;
  display: flex; flex-direction: column; gap: 8px;
}
.kpi-card__title {
  margin: 0;
  font-family: var(--font-mono); font-size: var(--text-caption);
  color: var(--text-muted); letter-spacing: 0.06em;
  text-transform: uppercase;
}
.kpi-card__value {
  display: flex; align-items: baseline; gap: 6px;
}
.kpi-card__value strong {
  font-family: var(--font-mono);
  font-size: var(--text-display);
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.kpi-card__value small {
  font-family: var(--font-mono); font-size: var(--text-caption);
  color: var(--text-muted);
}
.kpi-card.is-warning .kpi-card__value strong { color: var(--feedback-warning); }
.kpi-card.is-danger .kpi-card__value strong { color: var(--feedback-danger); }
</style>
```

- [ ] **Step 2.2: StatusBadge.vue**

```vue
<script setup lang="ts">
defineProps<{
  value: string;
  tone?: 'positive' | 'warning' | 'danger' | 'neutral';
}>();
</script>

<template>
  <span class="status-badge" :class="tone ? `is-${tone}` : 'is-neutral'">{{ value }}</span>
</template>

<style scoped>
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: var(--text-caption);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  border: 1px solid;
}
.status-badge.is-neutral  { color: var(--text-secondary); border-color: var(--border-default); background: transparent; }
.status-badge.is-positive { color: var(--feedback-success); border-color: var(--feedback-success); }
.status-badge.is-warning  { color: var(--feedback-warning); border-color: var(--feedback-warning); }
.status-badge.is-danger   { color: var(--feedback-danger);  border-color: var(--feedback-danger);  }
</style>
```

- [ ] **Step 2.3: FilterBar.vue**

```vue
<script setup lang="ts">
defineEmits<{ (e: 'change'): void }>();
</script>

<template>
  <div class="filter-bar">
    <slot />
    <button class="filter-bar__apply" @click="$emit('change')">Apply</button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  padding: 12px 16px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.filter-bar :deep(input),
.filter-bar :deep(select) {
  height: 32px; padding: 0 8px;
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono); font-size: var(--text-body);
}
.filter-bar__apply {
  height: 32px; padding: 0 14px;
  background: var(--accent-primary); border: none;
  color: var(--accent-on-primary);
  font-family: var(--font-mono); font-size: var(--text-caption);
  text-transform: uppercase; letter-spacing: 0.06em;
  cursor: pointer;
}
</style>
```

- [ ] **Step 2.4: AdminTable.vue**

```vue
<script setup lang="ts">
defineProps<{
  items: unknown[];
  loading?: boolean;
  totalPages?: number;
  currentPage?: number;
}>();
defineEmits<{ (e: 'page-change', page: number): void }>();
</script>

<template>
  <div class="admin-table">
    <div v-if="loading" class="admin-table__hint">Loading…</div>
    <div v-else-if="!items.length" class="admin-table__hint">No data.</div>
    <div v-else class="admin-table__rows">
      <slot v-for="(row, i) in items" :row="row" :index="i" name="row" />
    </div>
    <div v-if="totalPages && totalPages > 1" class="admin-table__pager">
      <button
        v-for="p in totalPages"
        :key="p"
        :class="{ 'is-active': p === currentPage }"
        @click="$emit('page-change', p)"
      >{{ p }}</button>
    </div>
  </div>
</template>

<style scoped>
.admin-table { display: flex; flex-direction: column; gap: 8px; }
.admin-table__hint {
  padding: 24px; text-align: center;
  color: var(--text-muted);
  background: var(--surface-raised);
  border: 1px dashed var(--border-default);
}
.admin-table__rows { display: flex; flex-direction: column; gap: 6px; }
.admin-table__pager {
  display: flex; gap: 4px; margin-top: 12px; justify-content: flex-end;
}
.admin-table__pager button {
  min-width: 28px; height: 28px;
  background: var(--surface-raised); color: var(--text-secondary);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono); cursor: pointer;
}
.admin-table__pager button.is-active {
  background: var(--accent-primary);
  color: var(--accent-on-primary);
  border-color: var(--accent-primary);
}
</style>
```

- [ ] **Step 2.5: TrendChart.vue**

```vue
<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  points: Array<{ date: string; used: number }>;
}>();

const maxValue = computed(() => Math.max(1, ...props.points.map(p => p.used)));
</script>

<template>
  <div class="trend-chart">
    <div v-for="p in points" :key="p.date" class="trend-chart__bar">
      <div
        class="trend-chart__fill"
        :style="{ height: `${Math.max(4, (p.used / maxValue) * 100)}%` }"
      />
      <small class="trend-chart__label">{{ p.date.slice(5) }}</small>
    </div>
  </div>
</template>

<style scoped>
.trend-chart {
  display: flex; align-items: flex-end; gap: 8px;
  height: 160px; padding: 16px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.trend-chart__bar {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  gap: 4px; height: 100%;
}
.trend-chart__fill {
  width: 100%; max-width: 24px;
  background: var(--accent-primary);
  margin-top: auto;
}
.trend-chart__label {
  font-family: var(--font-mono); font-size: var(--text-caption);
  color: var(--text-muted);
}
</style>
```

- [ ] **Step 2.6: BroadcastComposer.vue**

```vue
<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{ (e: 'submit', message: string, title?: string): void }>();

const title = ref('');
const message = ref('');

function submit() {
  const trimmed = message.value.trim();
  if (!trimmed) return;
  emit('submit', trimmed, title.value.trim() || undefined);
  title.value = '';
  message.value = '';
}
</script>

<template>
  <div class="broadcast">
    <input v-model="title" type="text" placeholder="Title (optional)" />
    <textarea v-model="message" rows="3" placeholder="Broadcast message..." />
    <button class="broadcast__submit" @click="submit">Send</button>
  </div>
</template>

<style scoped>
.broadcast {
  display: flex; flex-direction: column; gap: 8px;
  padding: 12px; background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.broadcast input, .broadcast textarea {
  background: var(--surface-base); color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 8px; font-family: var(--font-mono);
}
.broadcast__submit {
  align-self: flex-end;
  height: 32px; padding: 0 16px;
  background: var(--accent-primary); border: none;
  color: var(--accent-on-primary);
  font-family: var(--font-mono); font-size: var(--text-caption);
  text-transform: uppercase; letter-spacing: 0.06em;
  cursor: pointer;
}
</style>
```

- [ ] **Step 2.7: QuotaEditor.vue**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{ currentBytes: number; storageUsed: number }>();
const emit = defineEmits<{ (e: 'submit', newBytes: number): void }>();

const gb = ref((props.currentBytes / 1024 / 1024 / 1024).toFixed(1));
const errorMessage = ref('');
const usedGb = computed(() => (props.storageUsed / 1024 / 1024 / 1024).toFixed(2));

function submit() {
  const parsed = Number(gb.value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    errorMessage.value = 'Enter a positive number';
    return;
  }
  const bytes = Math.round(parsed * 1024 * 1024 * 1024);
  if (bytes < props.storageUsed) {
    errorMessage.value = `Cannot be below current usage (${usedGb.value} GB)`;
    return;
  }
  errorMessage.value = '';
  emit('submit', bytes);
}
</script>

<template>
  <div class="quota-editor">
    <input v-model="gb" type="number" step="0.1" min="0" />
    <small>GB · used {{ usedGb }} GB</small>
    <button class="quota-editor__submit" @click="submit">Save</button>
    <p v-if="errorMessage" class="quota-editor__error">{{ errorMessage }}</p>
  </div>
</template>

<style scoped>
.quota-editor { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.quota-editor input {
  width: 100px; height: 28px; padding: 0 8px;
  background: var(--surface-base); color: var(--text-primary);
  border: 1px solid var(--border-default); font-family: var(--font-mono);
}
.quota-editor small { color: var(--text-muted); font-family: var(--font-mono); font-size: var(--text-caption); }
.quota-editor__submit {
  height: 28px; padding: 0 12px;
  background: var(--accent-primary); border: none;
  color: var(--accent-on-primary); font-family: var(--font-mono);
  font-size: var(--text-caption); text-transform: uppercase; cursor: pointer;
}
.quota-editor__error {
  width: 100%; margin: 4px 0 0; color: var(--feedback-danger);
  font-family: var(--font-mono); font-size: var(--text-caption);
}
</style>
```

- [ ] **Step 2.8: barrel index.ts**

`web/src/components/console/index.ts`：

```typescript
export { default as KpiCard } from './KpiCard.vue';
export { default as StatusBadge } from './StatusBadge.vue';
export { default as FilterBar } from './FilterBar.vue';
export { default as AdminTable } from './AdminTable.vue';
export { default as TrendChart } from './TrendChart.vue';
export { default as BroadcastComposer } from './BroadcastComposer.vue';
export { default as QuotaEditor } from './QuotaEditor.vue';
```

- [ ] **Step 2.9: 类型检查 + commit**

```bash
cd web && bun run check
git add web/src/components/console
git commit -m "feat(web): add Console shared components (KpiCard, AdminTable, etc.)"
```

---

## Task 3: Overview 子页

**Files:**
- Replace placeholder: `web/src/pages/console/overview/OverviewPage.vue`

- [ ] **Step 3.1: 实现 OverviewPage**

`web/src/pages/console/overview/OverviewPage.vue`：

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminStorageSummary, getUsageTrend } from '../../../api/storage';
import { getViolations } from '../../../api/user';
import { getAdminLogs } from '../../../api/log';
import { getSystemHealth } from '../../../api/system';
import { KpiCard, TrendChart } from '../../../components/console';
import type { LogItem } from '../../../types/log';
import type { SystemHealth } from '../../../types/system';

const summary = ref<{ storageUsed: number; storageLimit: number; storagePercentage: number; fileCount: number; userCount: number } | null>(null);
const trend = ref<Array<{ date: string; used: number }>>([]);
const violations = ref<unknown[]>([]);
const recentLogs = ref<LogItem[]>([]);
const health = ref<SystemHealth | null>(null);

function formatBytes(bytes: number) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

onMounted(async () => {
  const [s, t, v, l, h] = await Promise.all([
    getAdminStorageSummary(),
    getUsageTrend({ days: 7 }),
    getViolations(),
    getAdminLogs({ page: 1, perPage: 5 }),
    getSystemHealth(),
  ]);
  summary.value = s;
  trend.value = t.trends;
  violations.value = v.items;
  recentLogs.value = l.logs;
  health.value = h;
});
</script>

<template>
  <section class="overview">
    <header class="overview__header"><h1>Overview</h1></header>

    <div v-if="summary && health" class="overview__kpis">
      <KpiCard title="Storage Used" :value="formatBytes(summary.storageUsed)" />
      <KpiCard title="Usage Ratio" :value="Math.round(summary.storagePercentage)" unit="%" />
      <KpiCard title="Total Files" :value="summary.fileCount" />
      <KpiCard title="Total Users" :value="summary.userCount" />
      <KpiCard title="Pending Violations" :value="violations.length" :accent="violations.length ? 'warning' : undefined" />
      <KpiCard title="Active Uploads" :value="health.activeUploadSessions" />
    </div>

    <h2 class="overview__section-title">7-Day Storage Trend</h2>
    <TrendChart v-if="trend.length" :points="trend" />

    <h2 class="overview__section-title">Recent Logs</h2>
    <ul class="overview__list">
      <li v-for="log in recentLogs" :key="log.id">
        <code>{{ new Date(log.performedAt).toLocaleString() }}</code>
        <span>{{ log.operationName }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.overview { display: flex; flex-direction: column; gap: 16px; }
.overview__kpis {
  display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.overview__section-title {
  margin: 8px 0 0; font-family: var(--font-mono); font-size: var(--text-caption);
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted);
}
.overview__list { list-style: none; padding: 0; margin: 0; }
.overview__list li {
  display: flex; gap: 12px; padding: 8px 12px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono); font-size: var(--text-body);
}
.overview__list li code { color: var(--text-muted); }
</style>
```

- [ ] **Step 3.2: 浏览器烟测 + commit**

`bun run dev` 后访问 `/console/overview`，确认 6 KPI 卡 + 趋势图 + 日志列表都渲染。

```bash
git add web/src/pages/console/overview/OverviewPage.vue
git commit -m "feat(web): Console Overview page"
```

---

## Task 4: Users 子页

**Files:** Replace `web/src/pages/console/users/UsersPage.vue`

- [ ] **Step 4.1: 实现 UsersPage**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminUsers, updateUserStatus } from '../../../api/user';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';

interface AdminUser {
  userId: string; username: string; email: string;
  role: string; status: 'active' | 'suspended';
  lastLoginAt: string | null; createdAt: string;
}

const items = ref<AdminUser[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const search = ref('');
const status = ref<'all' | 'active' | 'suspended'>('all');
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminUsers({
      page, perPage: 20,
      ...(search.value ? { search: search.value.trim() } : {}),
      ...(status.value !== 'all' ? { status: status.value } : {}),
    });
    items.value = resp.items as AdminUser[];
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally { loading.value = false; }
}

async function toggleStatus(user: AdminUser) {
  const next = user.status === 'active' ? 'suspended' : 'active';
  await updateUserStatus(user.userId, next);
  user.status = next;
  ui.toast({ type: 'success', message: `User ${user.username} → ${next}` });
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Users</h1></header>

    <FilterBar @change="load(1)">
      <input v-model="search" type="text" placeholder="Search username/email" />
      <select v-model="status">
        <option value="all">All status</option>
        <option value="active">Active</option>
        <option value="suspended">Suspended</option>
      </select>
    </FilterBar>

    <AdminTable
      :items="items"
      :loading="loading"
      :total-pages="totalPages"
      :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="row">
          <div class="row__main">
            <strong>{{ (row as AdminUser).username }}</strong>
            <small>{{ (row as AdminUser).email }} · {{ (row as AdminUser).role }}</small>
          </div>
          <div class="row__actions">
            <StatusBadge
              :value="(row as AdminUser).status"
              :tone="(row as AdminUser).status === 'active' ? 'positive' : 'danger'"
            />
            <button class="row__btn" @click="toggleStatus(row as AdminUser)">
              {{ (row as AdminUser).status === 'active' ? 'Suspend' : 'Activate' }}
            </button>
          </div>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.row {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.row__main { display: flex; flex-direction: column; min-width: 0; }
.row__main strong { font-family: var(--font-sans); font-size: var(--text-body); color: var(--text-primary); }
.row__main small { color: var(--text-muted); font-family: var(--font-mono); font-size: var(--text-caption); }
.row__actions { display: flex; gap: 8px; align-items: center; }
.row__btn {
  height: 28px; padding: 0 12px;
  background: var(--surface-base); border: 1px solid var(--border-default);
  color: var(--text-primary); font-family: var(--font-mono);
  font-size: var(--text-caption); cursor: pointer;
}
</style>
```

- [ ] **Step 4.2: 浏览器烟测 + commit**

访问 `/console/users` 验证列表 + suspend/activate 切换。

```bash
git add web/src/pages/console/users/UsersPage.vue
git commit -m "feat(web): Console Users page"
```

---

## Task 5: Storage 子页

**Files:** Replace `web/src/pages/console/storage/StoragePage.vue`

- [ ] **Step 5.1: 实现 StoragePage**

```vue
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import {
  getAdminStorageSummary, getStorageUsers,
  getUsageTrend, updateStorageQuota,
} from '../../../api/storage';
import { AdminTable, KpiCard, QuotaEditor, TrendChart } from '../../../components/console';
import { ui } from '../../../utils/ui';

interface StorageUserRow {
  userId: string; username: string; email: string;
  storageLimit: number; storageUsed: number; usagePercentage: number;
}

const summary = ref<{ storageUsed: number; storageLimit: number; storagePercentage: number; fileCount: number; userCount: number } | null>(null);
const trend = ref<Array<{ date: string; used: number }>>([]);
const days = ref<7 | 14 | 30>(7);
const users = ref<StorageUserRow[]>([]);
const editingId = ref<string | null>(null);

function fmt(b: number) {
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = b ? Math.floor(Math.log(b) / Math.log(1024)) : 0;
  return `${(b / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`;
}

async function reload() {
  const [s, t, u] = await Promise.all([
    getAdminStorageSummary(),
    getUsageTrend({ days: days.value }),
    getStorageUsers(),
  ]);
  summary.value = s;
  trend.value = t.trends;
  users.value = u.items as StorageUserRow[];
}

watch(days, () => reload());

async function applyQuota(user: StorageUserRow, bytes: number) {
  const result = await updateStorageQuota(user.userId, bytes);
  user.storageLimit = result.storageLimit;
  user.usagePercentage = result.usagePercentage;
  editingId.value = null;
  ui.toast({ type: 'success', message: 'Quota updated' });
}

onMounted(reload);
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Storage</h1></header>

    <div v-if="summary" class="kpis">
      <KpiCard title="Used" :value="fmt(summary.storageUsed)" />
      <KpiCard title="Limit" :value="fmt(summary.storageLimit)" />
      <KpiCard title="Users" :value="summary.userCount" />
    </div>

    <div class="trend-controls">
      <label v-for="opt in [7, 14, 30] as const" :key="opt">
        <input type="radio" :value="opt" v-model="days" /> {{ opt }}d
      </label>
    </div>
    <TrendChart v-if="trend.length" :points="trend" />

    <AdminTable :items="users">
      <template #row="{ row }">
        <div class="quota-row">
          <div class="quota-row__main">
            <strong>{{ (row as StorageUserRow).username }}</strong>
            <small>{{ fmt((row as StorageUserRow).storageUsed) }} / {{ fmt((row as StorageUserRow).storageLimit) }} · {{ (row as StorageUserRow).usagePercentage.toFixed(1) }}%</small>
          </div>
          <QuotaEditor
            v-if="editingId === (row as StorageUserRow).userId"
            :current-bytes="(row as StorageUserRow).storageLimit"
            :storage-used="(row as StorageUserRow).storageUsed"
            @submit="bytes => applyQuota(row as StorageUserRow, bytes)"
          />
          <button v-else class="quota-row__btn" @click="editingId = (row as StorageUserRow).userId">
            Adjust
          </button>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.trend-controls { display: flex; gap: 12px; font-family: var(--font-mono); font-size: var(--text-caption); color: var(--text-muted); }
.quota-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default); gap: 12px; }
.quota-row__main { display: flex; flex-direction: column; }
.quota-row__main strong { font-family: var(--font-sans); }
.quota-row__main small { color: var(--text-muted); font-family: var(--font-mono); }
.quota-row__btn {
  height: 28px; padding: 0 12px; background: var(--surface-base);
  border: 1px solid var(--border-default); color: var(--text-primary);
  font-family: var(--font-mono); font-size: var(--text-caption); cursor: pointer;
}
</style>
```

- [ ] **Step 5.2: 烟测 + commit**

```bash
git add web/src/pages/console/storage/StoragePage.vue
git commit -m "feat(web): Console Storage page with trend and quota editing"
```

---

## Task 6: Content 子页（文件审计）

**Files:** Replace `web/src/pages/console/content/ContentPage.vue`

- [ ] **Step 6.1: 实现**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminFiles, rescanAdminFile } from '../../../api/file';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';
import type { AdminFileAuditItem } from '../../../types/file';

const items = ref<AdminFileAuditItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const search = ref('');
const status = ref<'all' | 'clean' | 'pending' | 'flagged'>('all');
const loading = ref(false);

function fmt(b: number) {
  const u = ['B','KB','MB','GB','TB'];
  const i = b ? Math.floor(Math.log(b)/Math.log(1024)) : 0;
  return `${(b/Math.pow(1024,i)).toFixed(i?1:0)} ${u[i]}`;
}

const toneFor = (s: AdminFileAuditItem['virusStatus']) =>
  s === 'clean' ? 'positive' : s === 'flagged' ? 'danger' : 'warning';

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminFiles({
      page, perPage: 20, sort: 'updatedAt', order: 'desc',
      ...(search.value ? { search: search.value.trim() } : {}),
      ...(status.value !== 'all' ? { virusStatus: status.value } : {}),
    });
    items.value = resp.items;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally { loading.value = false; }
}

async function rescan(file: AdminFileAuditItem) {
  const result = await rescanAdminFile(file.id);
  file.virusStatus = result.virusStatus;
  ui.toast({ type: 'info', message: `Rescan requested for ${file.name}` });
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Content Audit</h1></header>

    <FilterBar @change="load(1)">
      <input v-model="search" type="text" placeholder="Search file name" />
      <select v-model="status">
        <option value="all">All status</option>
        <option value="clean">Clean</option>
        <option value="pending">Pending</option>
        <option value="flagged">Flagged</option>
      </select>
    </FilterBar>

    <AdminTable
      :items="items" :loading="loading"
      :total-pages="totalPages" :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="row">
          <div class="row__main">
            <strong>{{ (row as AdminFileAuditItem).name }}</strong>
            <small>{{ (row as AdminFileAuditItem).mimeType }} · {{ fmt((row as AdminFileAuditItem).size) }} · {{ (row as AdminFileAuditItem).hash }}</small>
          </div>
          <div class="row__actions">
            <StatusBadge
              :value="(row as AdminFileAuditItem).virusStatus"
              :tone="toneFor((row as AdminFileAuditItem).virusStatus)"
            />
            <button class="row__btn" @click="rescan(row as AdminFileAuditItem)">Rescan</button>
          </div>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default); }
.row__main { display: flex; flex-direction: column; min-width: 0; }
.row__main small { color: var(--text-muted); font-family: var(--font-mono); }
.row__actions { display: flex; gap: 8px; align-items: center; }
.row__btn { height: 28px; padding: 0 12px; background: var(--surface-base); border: 1px solid var(--border-default); color: var(--text-primary); font-family: var(--font-mono); font-size: var(--text-caption); cursor: pointer; }
</style>
```

- [ ] **Step 6.2: 烟测 + commit**

```bash
git add web/src/pages/console/content/ContentPage.vue
git commit -m "feat(web): Console Content audit page"
```

---

## Task 7: Moderation 子页（违规队列）

**Files:** Replace `web/src/pages/console/moderation/ModerationPage.vue`

- [ ] **Step 7.1: 实现**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getViolations, resolveViolation } from '../../../api/user';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';

interface ViolationRow {
  id: string; fileId: string | null; fileName: string | null;
  type: string; level: 'low' | 'medium' | 'high';
  reportedAt: string; status: 'pending' | 'under_review' | 'resolved';
}

const items = ref<ViolationRow[]>([]);
const statusFilter = ref<'all' | 'pending' | 'under_review' | 'resolved'>('pending');
const loading = ref(false);

const levelTone = (l: ViolationRow['level']) =>
  l === 'high' ? 'danger' : l === 'medium' ? 'warning' : 'neutral';

async function load() {
  loading.value = true;
  try {
    const resp = await getViolations();
    items.value = (resp.items as ViolationRow[])
      .filter(r => statusFilter.value === 'all' || r.status === statusFilter.value);
  } finally { loading.value = false; }
}

async function resolve(row: ViolationRow) {
  await resolveViolation(row.id);
  row.status = 'resolved';
  ui.toast({ type: 'success', message: 'Violation resolved' });
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Moderation</h1></header>

    <FilterBar @change="load">
      <select v-model="statusFilter">
        <option value="all">All</option>
        <option value="pending">Pending</option>
        <option value="under_review">Under Review</option>
        <option value="resolved">Resolved</option>
      </select>
    </FilterBar>

    <AdminTable :items="items" :loading="loading">
      <template #row="{ row }">
        <div class="row">
          <div class="row__main">
            <strong>{{ (row as ViolationRow).fileName || '—' }}</strong>
            <small>{{ (row as ViolationRow).type }} · {{ new Date((row as ViolationRow).reportedAt).toLocaleString() }}</small>
          </div>
          <div class="row__actions">
            <StatusBadge :value="(row as ViolationRow).level" :tone="levelTone((row as ViolationRow).level)" />
            <StatusBadge :value="(row as ViolationRow).status" :tone="(row as ViolationRow).status === 'resolved' ? 'positive' : 'warning'" />
            <button
              class="row__btn"
              :disabled="(row as ViolationRow).status === 'resolved'"
              @click="resolve(row as ViolationRow)"
            >Resolve</button>
          </div>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default); }
.row__main { display: flex; flex-direction: column; }
.row__main small { color: var(--text-muted); font-family: var(--font-mono); }
.row__actions { display: flex; gap: 8px; align-items: center; }
.row__btn {
  height: 28px; padding: 0 12px; background: var(--surface-base);
  border: 1px solid var(--border-default); color: var(--text-primary);
  font-family: var(--font-mono); font-size: var(--text-caption); cursor: pointer;
}
.row__btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
```

- [ ] **Step 7.2: 烟测 + commit**

```bash
git add web/src/pages/console/moderation/ModerationPage.vue
git commit -m "feat(web): Console Moderation page"
```

---

## Task 8: System 子页（Health + RateLimit）

**Files:** Replace `web/src/pages/console/system/SystemPage.vue`

- [ ] **Step 8.1: 实现**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getSystemHealth, getRateLimitStatus } from '../../../api/system';
import { AdminTable, StatusBadge } from '../../../components/console';
import type { RateLimitStatus, SystemHealth } from '../../../types/system';

const health = ref<SystemHealth | null>(null);
const rateLimit = ref<RateLimitStatus | null>(null);

onMounted(async () => {
  const [h, r] = await Promise.all([getSystemHealth(), getRateLimitStatus()]);
  health.value = h;
  rateLimit.value = r;
});
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>System</h1></header>

    <div v-if="health" class="health">
      <div class="health__item">
        <span>Virus Scan</span>
        <StatusBadge :value="health.virusScanEnabled ? 'on' : 'off'" :tone="health.virusScanEnabled ? 'positive' : 'neutral'" />
      </div>
      <div class="health__item">
        <span>Thumbnail</span>
        <StatusBadge :value="health.thumbnailGenerationEnabled ? 'on' : 'off'" :tone="health.thumbnailGenerationEnabled ? 'positive' : 'neutral'" />
      </div>
      <div class="health__item">
        <span>Registration Mail</span>
        <StatusBadge :value="health.registrationMailEnabled ? 'on' : 'off'" :tone="health.registrationMailEnabled ? 'positive' : 'neutral'" />
      </div>
      <div class="health__item">
        <span>Hash Computation</span>
        <StatusBadge :value="health.hashComputationEnabled ? 'on' : 'off'" :tone="health.hashComputationEnabled ? 'positive' : 'neutral'" />
      </div>
      <div class="health__item">
        <span>Active Upload Sessions</span>
        <strong class="num">{{ health.activeUploadSessions }}</strong>
      </div>
      <div class="health__item">
        <span>Max Concurrent</span>
        <strong class="num">{{ health.maxConcurrentUploads }}</strong>
      </div>
      <div class="health__targets">
        <span>Targets</span>
        <code v-for="t in health.platformTargets" :key="t">{{ t }}</code>
      </div>
    </div>

    <h2 class="page__section">Rate Limit Rules</h2>
    <AdminTable :items="rateLimit?.rules ?? []">
      <template #row="{ row }">
        <div class="rate-row">
          <strong>{{ (row as any).scope }}</strong>
          <small>{{ (row as any).limit }} / {{ (row as any).windowSeconds }}s · used {{ (row as any).currentUsage }} · blocked {{ (row as any).blockedRequests }}</small>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.health {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px;
}
.health__item, .health__targets {
  display: flex; justify-content: space-between; gap: 12px; align-items: center;
  padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default);
  font-family: var(--font-mono); font-size: var(--text-body);
  color: var(--text-secondary);
}
.health__item .num { color: var(--text-primary); }
.health__targets { flex-wrap: wrap; }
.health__targets code { color: var(--text-primary); }
.page__section { font-family: var(--font-mono); font-size: var(--text-caption); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 8px 0 0; }
.rate-row { display: flex; flex-direction: column; padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default); }
.rate-row small { color: var(--text-muted); }
</style>
```

- [ ] **Step 8.2: 烟测 + commit**

```bash
git add web/src/pages/console/system/SystemPage.vue
git commit -m "feat(web): Console System page"
```

---

## Task 9: Logs 子页

**Files:** Replace `web/src/pages/console/logs/LogsPage.vue`

- [ ] **Step 9.1: 实现**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminLogs } from '../../../api/log';
import { AdminTable, FilterBar } from '../../../components/console';
import type { LogItem } from '../../../types/log';

const items = ref<LogItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const userId = ref('');
const operation = ref('');
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminLogs({
      page, perPage: 20,
      ...(userId.value ? { userId: userId.value.trim() } : {}),
      ...(operation.value ? { operation: operation.value.trim() } : {}),
    });
    items.value = resp.logs;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally { loading.value = false; }
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Logs</h1></header>
    <FilterBar @change="load(1)">
      <input v-model="userId" type="text" placeholder="User ID" />
      <input v-model="operation" type="text" placeholder="Operation" />
    </FilterBar>
    <AdminTable
      :items="items" :loading="loading"
      :total-pages="totalPages" :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="log-row">
          <code>{{ new Date((row as LogItem).performedAt).toLocaleString() }}</code>
          <strong>{{ (row as LogItem).operationName }}</strong>
          <small>{{ (row as LogItem).ipAddress }} · {{ (row as LogItem).userId || 'system' }}</small>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.log-row {
  display: grid; grid-template-columns: 200px 1fr 200px; gap: 12px; align-items: center;
  padding: 8px 14px; background: var(--surface-raised); border: 1px solid var(--border-default);
  font-family: var(--font-mono); font-size: var(--text-caption);
}
.log-row code { color: var(--text-muted); }
.log-row small { color: var(--text-muted); text-align: right; }
</style>
```

- [ ] **Step 9.2: 烟测 + commit**

```bash
git add web/src/pages/console/logs/LogsPage.vue
git commit -m "feat(web): Console Logs page"
```

---

## Task 10: Notifications 子页

**Files:** Replace `web/src/pages/console/notifications/NotificationsPage.vue`

- [ ] **Step 10.1: 实现**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  archiveAdminNotification,
  broadcastNotification,
  getAdminNotifications,
} from '../../../api/notification';
import { AdminTable, BroadcastComposer, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';
import type { NotificationItem } from '../../../types/notification';

const items = ref<NotificationItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminNotifications({ page, perPage: 20 });
    items.value = resp.items;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally { loading.value = false; }
}

async function broadcast(message: string, title?: string) {
  await broadcastNotification(message, title);
  ui.toast({ type: 'success', message: 'Broadcast sent' });
  await load(1);
}

async function archive(row: NotificationItem) {
  await archiveAdminNotification(row.id);
  ui.toast({ type: 'success', message: 'Archived' });
  await load(currentPage.value);
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Notifications</h1></header>

    <BroadcastComposer @submit="broadcast" />

    <AdminTable
      :items="items" :loading="loading"
      :total-pages="totalPages" :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="note-row">
          <div class="note-row__main">
            <strong>{{ (row as NotificationItem).message }}</strong>
            <small>{{ new Date((row as NotificationItem).createdAt).toLocaleString() }}</small>
          </div>
          <div class="note-row__actions">
            <StatusBadge :value="(row as NotificationItem).isRead ? 'read' : 'unread'" :tone="(row as NotificationItem).isRead ? 'positive' : 'neutral'" />
            <button class="note-row__btn" @click="archive(row as NotificationItem)">Archive</button>
          </div>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.note-row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default); }
.note-row__main { display: flex; flex-direction: column; min-width: 0; }
.note-row__main small { color: var(--text-muted); font-family: var(--font-mono); font-size: var(--text-caption); }
.note-row__actions { display: flex; gap: 8px; align-items: center; }
.note-row__btn {
  height: 28px; padding: 0 12px; background: var(--surface-base);
  border: 1px solid var(--border-default); color: var(--text-primary);
  font-family: var(--font-mono); font-size: var(--text-caption); cursor: pointer;
}
</style>
```

- [ ] **Step 10.2: 烟测 + commit**

```bash
git add web/src/pages/console/notifications/NotificationsPage.vue
git commit -m "feat(web): Console Notifications page with broadcast"
```

---

## Task 11: Rules 子页（搬运 + AdminTable 化）

**Files:** Replace `web/src/pages/console/rules/RulesPage.vue`

- [ ] **Step 11.1: 实现**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  createRegistrationEmailDomainRule,
  deleteRegistrationEmailDomainRule,
  getRegistrationEmailDomainRules,
  updateRegistrationEmailDomainRule,
} from '../../../api/registration-email-domain-rule';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';
import type { RegistrationEmailDomainRuleItem } from '../../../types/registration-email-domain-rule';

const items = ref<RegistrationEmailDomainRuleItem[]>([]);
const queryText = ref('');
const enabledFilter = ref<'all' | 'enabled' | 'disabled'>('all');
const newName = ref('');
const newPattern = ref('');
const newEnabled = ref(true);

async function load() {
  const enabled = enabledFilter.value === 'all' ? undefined : enabledFilter.value === 'enabled';
  const resp = await getRegistrationEmailDomainRules({
    page: 1, perPage: 50,
    queryText: queryText.value.trim() || undefined,
    enabled,
  });
  items.value = resp.items;
}

async function create() {
  const name = newName.value.trim();
  const pattern = newPattern.value.trim();
  if (!name || !pattern) {
    ui.toast({ type: 'warning', message: 'Name and pattern required' });
    return;
  }
  await createRegistrationEmailDomainRule({ name, pattern, enabled: newEnabled.value });
  newName.value = ''; newPattern.value = '';
  await load();
}

async function toggle(row: RegistrationEmailDomainRuleItem) {
  await updateRegistrationEmailDomainRule(row.ruleId, { enabled: !row.enabled });
  row.enabled = !row.enabled;
}

async function remove(row: RegistrationEmailDomainRuleItem) {
  await deleteRegistrationEmailDomainRule(row.ruleId);
  items.value = items.value.filter(it => it.ruleId !== row.ruleId);
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Registration Rules</h1></header>

    <FilterBar @change="load">
      <input v-model="queryText" type="text" placeholder="Search name/pattern" />
      <select v-model="enabledFilter">
        <option value="all">All</option>
        <option value="enabled">Enabled</option>
        <option value="disabled">Disabled</option>
      </select>
    </FilterBar>

    <div class="rule-create">
      <input v-model="newName" type="text" placeholder="Rule name" />
      <input v-model="newPattern" type="text" placeholder="Regex e.g. .*\.example\.com" />
      <label><input v-model="newEnabled" type="checkbox" /> Enabled</label>
      <button class="rule-create__btn" @click="create">Add</button>
    </div>

    <AdminTable :items="items">
      <template #row="{ row }">
        <div class="rule-row">
          <div class="rule-row__main">
            <strong>{{ (row as RegistrationEmailDomainRuleItem).name }}</strong>
            <small>{{ (row as RegistrationEmailDomainRuleItem).pattern }}</small>
          </div>
          <div class="rule-row__actions">
            <StatusBadge
              :value="(row as RegistrationEmailDomainRuleItem).enabled ? 'enabled' : 'disabled'"
              :tone="(row as RegistrationEmailDomainRuleItem).enabled ? 'positive' : 'neutral'"
            />
            <button class="rule-row__btn" @click="toggle(row as RegistrationEmailDomainRuleItem)">
              {{ (row as RegistrationEmailDomainRuleItem).enabled ? 'Disable' : 'Enable' }}
            </button>
            <button class="rule-row__btn is-danger" @click="remove(row as RegistrationEmailDomainRuleItem)">
              Delete
            </button>
          </div>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.rule-create {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  padding: 12px; background: var(--surface-raised); border: 1px solid var(--border-default);
}
.rule-create input[type=text] {
  flex: 1; min-width: 180px; height: 32px; padding: 0 8px;
  background: var(--surface-base); border: 1px solid var(--border-default);
  color: var(--text-primary); font-family: var(--font-mono);
}
.rule-create__btn {
  height: 32px; padding: 0 16px; background: var(--accent-primary);
  border: none; color: var(--accent-on-primary);
  font-family: var(--font-mono); cursor: pointer;
}
.rule-row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 14px; background: var(--surface-raised); border: 1px solid var(--border-default); }
.rule-row__main small { color: var(--text-muted); font-family: var(--font-mono); }
.rule-row__actions { display: flex; gap: 8px; align-items: center; }
.rule-row__btn {
  height: 28px; padding: 0 12px; background: var(--surface-base);
  border: 1px solid var(--border-default); color: var(--text-primary);
  font-family: var(--font-mono); font-size: var(--text-caption); cursor: pointer;
}
.rule-row__btn.is-danger { color: var(--feedback-danger); border-color: var(--feedback-danger); }
</style>
```

- [ ] **Step 11.2: 烟测 + commit**

```bash
git add web/src/pages/console/rules/RulesPage.vue
git commit -m "feat(web): Console Rules page (registration email domains)"
```

---

## Task 12: 主框架集成、删除旧 Dashboard、i18n

**Files:**
- Modify: `web/src/components/organisms/shell/UserMenu.vue`
- Modify: `web/src/i18n/messages.ts`
- Delete: `web/src/pages/dashboard/Dashboard.vue`, `web/src/pages/dashboard/index.ts`

- [ ] **Step 12.1: 修改 UserMenu 入口指向 console**

Edit `web/src/components/organisms/shell/UserMenu.vue` 第 44 行：

```vue
<MenuItem v-if="isAdmin" icon="search" @click="router.push('/console/overview'); close()">{{ t('header.menu.console') }}</MenuItem>
```

- [ ] **Step 12.2: i18n 增 `console.*` + 改 `header.menu.console`**

Edit `web/src/i18n/messages.ts`：

1. 在类型联合 `'header.menu.dashboard'` 处改为 `'header.menu.console'`，并在末尾加入：

```
  | 'console.title'
  | 'console.nav.overview'
  | 'console.nav.users'
  | 'console.nav.storage'
  | 'console.nav.content'
  | 'console.nav.moderation'
  | 'console.nav.system'
  | 'console.nav.logs'
  | 'console.nav.notifications'
  | 'console.nav.rules'
```

2. 中英 messages 表中，把原 `'header.menu.dashboard': '仪表盘'` 改为 `'header.menu.console': '控制台'`（en-US 改为 `'Console'`）。追加：

中文表：
```
    'console.title': '控制台',
    'console.nav.overview': '概览',
    'console.nav.users': '用户',
    'console.nav.storage': '存储',
    'console.nav.content': '内容审计',
    'console.nav.moderation': '违规处理',
    'console.nav.system': '系统状态',
    'console.nav.logs': '操作日志',
    'console.nav.notifications': '通知',
    'console.nav.rules': '注册规则',
```

英文表：
```
    'console.title': 'Console',
    'console.nav.overview': 'Overview',
    'console.nav.users': 'Users',
    'console.nav.storage': 'Storage',
    'console.nav.content': 'Content Audit',
    'console.nav.moderation': 'Moderation',
    'console.nav.system': 'System',
    'console.nav.logs': 'Logs',
    'console.nav.notifications': 'Notifications',
    'console.nav.rules': 'Registration Rules',
```

- [ ] **Step 12.3: 确认旧 dashboard 路径无残留引用**

Run: `cd web && grep -rn "pages/dashboard\|/dashboard'" src/`
Expected: 仅出现在 `router/routes.ts` 的 `redirect: '/console/overview'` 那一行。

- [ ] **Step 12.4: 删除旧 Dashboard**

```bash
rm web/src/pages/dashboard/Dashboard.vue web/src/pages/dashboard/index.ts
rmdir web/src/pages/dashboard
```

- [ ] **Step 12.5: 类型检查 + dev 烟测**

```bash
cd web && bun run check
cd web && bun run dev
```

访问 `/dashboard` 应自动跳到 `/console/overview`；UserMenu 显示 "Console" / "控制台" 入口；切换语言能正常 i18n。

- [ ] **Step 12.6: Commit**

```bash
git add web/src/components/organisms/shell/UserMenu.vue web/src/i18n/messages.ts web/src/router/routes.ts
git rm web/src/pages/dashboard/Dashboard.vue web/src/pages/dashboard/index.ts
git commit -m "feat(web): wire Console into MainLayout, drop legacy Dashboard, add i18n"
```

---

## Task 13: 端到端冒烟 + 类型检查 + 构建

- [ ] **Step 13.1: 全量 check**

```bash
cd web && bun run check
```
Expected: 0 errors。

- [ ] **Step 13.2: 全量构建**

```bash
cd web && bun run build
```
Expected: dist/ 生成、无错误。

- [ ] **Step 13.3: dev server 手动巡检**

启动 `bun run dev`，以 admin 账号登录后逐一访问 9 个子页：

- `/console/overview` —— 6 KPI + 趋势 + 日志/违规列表
- `/console/users` —— 列表 + suspend/activate 即时反馈
- `/console/storage` —— summary + 7/14/30 切换 + Adjust 配额
- `/console/content` —— 列表过滤 + Rescan
- `/console/moderation` —— Resolve 按钮可点
- `/console/system` —— Health 开关 + RateLimit 列表
- `/console/logs` —— 列表 + filter
- `/console/notifications` —— BroadcastComposer 发送
- `/console/rules` —— Add + Toggle + Delete

非 admin 账号访问 `/console/*` 应被路由守卫拦截（`requiresAdmin`）。

- [ ] **Step 13.4: 单元测试（可选）**

如果项目有 vitest 配置，加一个最简 smoke：

```typescript
// web/src/pages/console/__tests__/router.spec.ts
import { describe, expect, it } from 'vitest';
import { routes } from '../../../router/routes';

describe('console routes', () => {
  it('legacy /dashboard redirects to /console/overview', () => {
    const r = routes.find(r => r.path === '/dashboard');
    expect(r?.redirect).toBe('/console/overview');
  });
});
```

Run: `cd web && bun run test` (若有此命令；不存在则跳过本步)

- [ ] **Step 13.5: Final commit**

```bash
git status
# 如果 13.4 加了测试：
# git add web/src/pages/console/__tests__/router.spec.ts && git commit -m "test(web): console route redirect smoke"
```

---

## Plan B 完工标准

- `/console/overview, /users, /storage, /content, /moderation, /system, /logs, /notifications, /rules` 9 个子页可访问，沿用工业风样式。
- 旧 `pages/dashboard/` 目录已删除；`/dashboard` 跳转 `/console/overview`。
- `bun run check` / `bun run build` 通过。
- 非 admin 用户访问 `/console/*` 被守卫拦截。
- 与 Plan A 后端独立工作（mock 兜底）；当 Plan A 合入后切换 `setupMocks()` 关闭，前端零代码改动即可对真实后端。
