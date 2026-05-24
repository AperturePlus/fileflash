# Admin Console（管理员控制台）全栈实现设计

- 日期：2026-05-24
- 范围：后端 admin API 全量补齐 + 前端 `pages/dashboard/` 重构为多页式 `pages/console/`
- 当前痛点：`Dashboard.vue` 把 9 个管理域塞在一个文件里；调用的 `/admin/*` 接口除 `registration-email-domain-rules` 外**均未实装**（仅有 mock）

---

## 1. 总体架构与目录布局

### 1.1 后端 `app/src/fileflash/`

```
routers/
  admin_users.py              ← /admin/users, /admin/users/{id}/status
  admin_storage.py            ← /admin/storage/summary, /admin/storage/users,
                                /admin/storage/users/{id}/quota,
                                /admin/storage/usage-trend
  admin_files.py              ← /admin/files, /admin/files/{id}/rescan
  admin_moderation.py         ← /admin/violations, /admin/violations/{id}/resolve
  admin_logs.py               ← /admin/logs
  admin_notifications.py      ← /admin/notifications, /broadcast,
                                /{id}/read, DELETE /{id}
  admin_system.py             ← /admin/system/health, /admin/system/rate-limit
  admin_registration_email_domain_rules.py  (已有, 不动)

services/admin/
  __init__.py
  users.py
  storage.py
  files.py
  moderation.py
  logs.py
  notifications.py
  system.py

schemas/admin/
  users.py, storage.py, files.py, moderation.py,
  logs.py, notifications.py, system.py
  （camelCase by alias，分页壳沿用现有 PaginatedData）

core/deps.py
  + get_admin_users_service()
  + get_admin_storage_service()
  + get_admin_files_service()
  + get_admin_moderation_service()
  + get_admin_logs_service()
  + get_admin_notifications_service()
  + get_admin_system_service()
```

### 1.2 前端 `web/src/`

```
pages/console/                ← 取代 pages/dashboard/
  ConsoleLayout.vue
  ConsoleSidebar.vue
  overview/OverviewPage.vue
  users/UsersPage.vue
  storage/StoragePage.vue
  content/ContentPage.vue
  moderation/ModerationPage.vue
  system/SystemPage.vue
  logs/LogsPage.vue
  notifications/NotificationsPage.vue
  rules/RulesPage.vue
  index.ts                    （按页 lazy import）

components/console/
  KpiCard.vue, TrendChart.vue, FilterBar.vue,
  AdminTable.vue, StatusBadge.vue, BroadcastComposer.vue,
  QuotaEditor.vue

api/                          ← 现有按域名分文件，按需扩展，不新增 admin.ts
mock/handlers/                ← 与后端新接口同步
router/routes.ts              ← 新增 /console 嵌套路由，/dashboard 重定向到 /console/overview
i18n/zh-CN/console.ts, i18n/en-US/console.ts   ← 新建 console.* 命名空间
```

### 1.3 风格与鉴权

- 视觉：复用 `frontend_aesthetic` 的 *Industrial Dashboard*——深色 + 等宽数字 (tabular-nums) + 直角硬边 + Electric Lime 主色。
- 后端：所有 `/admin/*` 路由统一 `Depends(require_admin)`。
- 前端：嵌套路由 `meta.requiresAdmin = true`；`router/gurad.ts` 已校验 `userStore.user?.role === 'admin'`。

---

## 2. 接口契约

通用约定：`api_success` 壳、`async def`、camelCase by alias、分页 `{items, pagination}`、错误用现有 `APIException`。

### 2.1 Users `/admin/users*`

| Method | Path | Query/Body | Response |
|---|---|---|---|
| GET | `/admin/users` | `search?, status?, role?, page=1, perPage=20, sort?, order?` | `PaginatedData<AdminUserItem>` |
| PATCH | `/admin/users/{userId}/status` | `{ status: 'active'\|'suspended' }` | `{ userId, status, updatedAt }` |

`AdminUserItem`：`userId, username, email, role, status, emailVerified, emailVerifiedAt, storageLimit, storageUsed, usagePercentage, lastLoginAt, lastActiveAt, createdAt`

`lastActiveAt` 来源：该用户最近一次未撤销的 `UserSession.last_seen_at` 的 MAX 值；无 session 则为 null。

错误：404 `USER_NOT_FOUND`；409 `LAST_ADMIN_CANNOT_SUSPEND`。

### 2.2 Storage `/admin/storage*`

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/storage/summary` | 全局聚合 `storageUsed/storageLimit/fileCount/userCount/storagePercentage` |
| GET | `/admin/storage/users` | per-user 配额表，`?page&perPage&sort` |
| PATCH | `/admin/storage/users/{userId}/quota` | `{ storageLimit }` (bytes，>=0) → `{ userId, storageLimit, storageUsed, usagePercentage, updatedAt }` |
| GET | `/admin/storage/usage-trend` | `?days=7\|14\|30` → `{ trends: [{date, used}], isEstimated? }` |

普通用户 `/storage/summary` 不动；前端 `api/storage.ts` 中新增 `getAdminStorageSummary()` 指向 `/admin/storage/summary`，现有 `getStorageStats() / getStorageSummary()`（个人视图）保持不变。

### 2.3 Files `/admin/files*`

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/files` | `?search, virusStatus?, ownerId?, mimeType?, page, perPage, sort, order`；左联 `ObjectScanResult` 取最近一次得到 `virusStatus`；`hash` 取 `storage_object.content_hash` 前 16 位 |
| POST | `/admin/files/{fileId}/rescan` | 插入 `ObjectScanResult(result='pending')` + 发布 `files.rescan_requested` 事件 → `{ fileId, virusStatus: 'pending', scannedAt }` |

### 2.4 Moderation `/admin/violations*`

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/violations` | `?status=pending\|under_review\|resolved&page&perPage`；JOIN `File` |
| POST | `/admin/violations/{caseId}/resolve` | 设 `status='resolved', resolution='admin_clear', handled_by, handled_at` |

映射：`id=caseId, fileId/fileName=join file, type=reason_type, level` 由 `confidence` 区间换算 (>0.8 high；>0.5 medium；else low)。

### 2.5 Logs `/admin/logs`

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/logs` | `?userId?, operation?, result?, from?, to?, page, perPage` → `{ logs, pagination }`（沿用现有 `LogsList` 形状） |

注：前端原 `getLogs()` 指向 `/logs` 系误用，本次新增 `getAdminLogs()` 指向 `/admin/logs`；用户自己活动日志保持 `/me/activity-log`。

### 2.6 Notifications `/admin/notifications*`

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/notifications` | `?status?, type?, page, perPage` |
| POST | `/admin/notifications/broadcast` | `{ title?, message, type='system' }` → `{ broadcastId, recipientCount, sentAt }`，对所有 active user 落 Notification 行 |
| PUT | `/admin/notifications/{id}/read` | admin 视角标记已读 |
| DELETE | `/admin/notifications/{id}` | 软删（设 `status='archived'`） |

普通用户 `/notifications*` 不动；前端 `broadcastNotification()` 改指向 `/admin/notifications/broadcast`。

### 2.7 System `/admin/system*`

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/system/health` | 聚合 `settings + 进程内 counter`，返回 `SystemHealth` |
| GET | `/admin/system/rate-limit` | `SCAN MATCH "rate_limit:*"` 读 Redis 聚合 `{rules, evaluatedAt}` |

字段来源：
- `activeUploadSessions` ← `UploadService.session_table_size()`
- 其余 boolean / 列表 / 阈值 ← `settings`

---

## 3. 数据流、聚合查询与并发/事务

### 3.1 Usage Trend（7/14/30 日存储趋势）

`User.storage_used` 只有当前值。方案：用 `Log` 事件**反向重放**：

1. `T_now = SELECT SUM(storage_used) FROM "user"`
2. 取 `Log` 过去 N 天 `file.created/deleted/restored` 的 `metadata.size` 增减，按天分桶 `delta_by_day`
3. 回填 `used[d] = T_now − Σ delta[d_now..d+1]`
4. Redis 缓存 `admin:storage:trend:{days}`，TTL 5 分钟
5. 降级：旧库无相应 Log 时返回平滑占位 + `isEstimated: true`

### 3.2 Broadcast Notification

约束：初版同步完成，目标用户上限 50k；超限 422。

1. `broadcast_id = uuid4()`
2. 分批 `chunk_size = 500` 流式查 active user id
3. 每批 `add_all + commit`，批次间独立事务；幂等键 = broadcastId
4. 完成后写 `Log(operation='admin.notification.broadcast', metadata={broadcastId, recipientCount})`
5. 发布 `notification.broadcast_completed` 事件
6. 同步返回 `{broadcastId, recipientCount, sentAt}`

### 3.3 Rescan File

1. 查 `File`；不存在 → 404 `FILE_NOT_FOUND`
2. 插入 `ObjectScanResult(scan_type='virus', result='pending')`
3. 发布 `files.rescan_requested {objectId, fileId, requestedBy}`
4. 返回 `{fileId, virusStatus: 'pending', scannedAt}`

### 3.4 Quota Update

1. `SELECT ... FOR UPDATE` 锁 `User` 行
2. 校验 `new_limit >= storage_used`，否则 409 `QUOTA_BELOW_USAGE`
3. 更新 + 写 `Log(operation='admin.user.quota_update', metadata={oldLimit, newLimit})`

### 3.5 User Status Change

1. 422 若 status ∉ {active, suspended}
2. **防误锁**：若把 admin 设为 suspended 且 active admin 仅余 1 → 409 `LAST_ADMIN_CANNOT_SUSPEND`
3. 改 `User.status`；转 suspended 时同时 `revoked_at = now()` 该用户全部 `UserSession`
4. 写 `Log(operation='admin.user.status_change', metadata={from, to})`

### 3.6 Violation Resolve

1. `SELECT ... FOR UPDATE` 锁 `ModerationCase`
2. 仅 `status in ('pending','under_review')` 可解决，否则 409 `CASE_ALREADY_RESOLVED`
3. 更新 + 写 `Log(operation='admin.violation.resolve', metadata={caseId, fileId})`

### 3.7 System Health 聚合

读源（全部只读，无锁）：

- `settings.virus_scan_enabled / thumbnail_generation_enabled / hash_computation_enabled / max_concurrent_uploads / platform_targets`
- 从 `settings.smtp_*` 推断 `registrationMailEnabled`
- `UploadService.session_table_size()`（新增只读方法）
- `lastUpdatedAt = datetime.now(UTC)`

### 3.8 Rate Limit 聚合

1. `SCAN MATCH "rate_limit:*"`（禁用 KEYS）
2. 解析 scope/window/limit；`ZCARD/INCR` 取 `currentUsage`；`blockedRequests` 从 `rate_limit_blocked:{scope}` 取
3. 在 `RateLimiter` reject 路径补一个原子 `INCR rate_limit_blocked:{scope}`（若未实现）

### 3.9 前端数据流

- 每个子页 `onMounted` 自取数据；不在 `ConsoleLayout` 集中拉
- 共享分页逻辑：`composables/usePagination(getter)` → `{items, pagination, page, perPage, sort, order, reload()}`
- 错误处理统一交给 `utils/http.ts` 拦截器：403/401 跳登录，422/409 toast warning，500 toast error
- 子页不自己 try/catch（除非要做局部 fallback）
- 旧 `/dashboard` 路由保留为 redirect 到 `/console/overview`

---

## 4. 前端组件分解

### 4.1 共享组件 `web/src/components/console/`

| 组件 | 职责 | Props |
|---|---|---|
| `ConsoleSidebar.vue` | 9 项导航 + 当前路由高亮 | — |
| `KpiCard.vue` | 单指标卡 | `{ title, value, unit?, delta?, accent? }` |
| `TrendChart.vue` | 7/14/30 日柱状（沿用现有 trend-bars 风格） | `{ points: {date,used}[], height? }` |
| `FilterBar.vue` | 筛选条 | slot: `filters`, emit: `change` |
| `AdminTable.vue` | 列表 + 分页 + 空态 + skeleton | `{ items, pagination, loading }`, slots: `cols`, `row` |
| `StatusBadge.vue` | 状态徽章 | `{ value, tone? }` |
| `BroadcastComposer.vue` | 广播输入 | emit: `submit` |
| `QuotaEditor.vue` | 配额输入（GB ↔ bytes） | `{ user }`, emit: `submit` |

共享组件**不做数据请求**，只接 props + emit。

### 4.2 ConsoleLayout

```
<ConsoleLayout>
  <header class="console-header">  ← 面包屑 + 当前页标题 + 全局刷新按钮
  <aside><ConsoleSidebar /></aside>
  <main><router-view /></main>
</ConsoleLayout>
```

仅暴露 `refreshNonce` ref，子页 watch 触发重拉。

### 4.3 9 个子页（每个 ≤ 250 行，超出则拆 `*Card.vue / *Row.vue`）

1. **Overview**：6 张 `KpiCard` + 1 张 `TrendChart` + 最近 5 条 Log + 最近 3 条 Violation。API：`getAdminStorageSummary, getStorageUsageTrend, getViolations({perPage:3}), getAdminLogs({perPage:5}), getSystemHealth`。
2. **Users**：`FilterBar(search/status/role)` + `AdminTable[username,email,role,status,lastLoginAt,action]`。API：`getAdminUsers, updateUserStatus`。
3. **Storage**：3 张 `KpiCard` + 大 `TrendChart`（可切 7/14/30）+ per-user 配额表 + `QuotaEditor`。API：`getAdminStorageSummary, getStorageUsageTrend, getStorageUsers, updateStorageQuota`。
4. **Content**（文件审计）：`FilterBar(search/virusStatus/ownerId/mimeType)` + `AdminTable[name,owner,size,hash,virusStatus,action]`。API：`getAdminFiles, rescanAdminFile`。
5. **Moderation**：`FilterBar(status)` + `AdminTable[fileName,type,level,reportedAt,status,action]`。API：`getViolations, resolveViolation`。
6. **System**：Health 开关组 + RateLimit 表（含进度条）。API：`getSystemHealth, getRateLimitStatus`。
7. **Logs**：`FilterBar(userId/operation/result/dateRange)` + `AdminTable[performedAt,user,operation,target,ipAddress,result]`。API：`getAdminLogs`。
8. **Notifications**：`BroadcastComposer` + `AdminTable[createdAt,message,type,recipientCount,status,action(Archive)]`。API：`getAdminNotifications, broadcastNotification, deleteAdminNotification`。
9. **Rules**：搬现有 Dashboard 中"Registration Email Domain Rules"段落为独立页 + `AdminTable`。API 不变。

### 4.4 路由表新增

```ts
{
  path: 'console',
  component: ConsoleLayout,
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

旧 `pages/dashboard/` 在 PR 末尾整段删除。

### 4.5 i18n

新增命名空间 `console.*`，分布于 `web/src/i18n/zh-CN/console.ts` 与 `en-US/console.ts`。具体 key 在 plan 执行阶段列出。

### 4.6 主框架导航集成

`MainLayout` 顶层导航把"Dashboard"项替换为"Console"，`requiresAdmin` 显隐由现有 `userStore.isAdmin` 控制。

---

## 5. 错误处理、可观测性、测试与回归

### 5.1 错误码

| Code | HTTP | 场景 |
|---|---|---|
| `USER_NOT_FOUND` | 404 | admin_users 目标不存在 |
| `LAST_ADMIN_CANNOT_SUSPEND` | 409 | 防误锁 |
| `QUOTA_BELOW_USAGE` | 409 | 配额低于已用 |
| `FILE_NOT_FOUND` | 404 | admin_files rescan |
| `CASE_NOT_FOUND` | 404 | moderation resolve |
| `CASE_ALREADY_RESOLVED` | 409 | 重复 resolve |
| `INVALID_STATUS_VALUE` | 422 | status 非法 |
| `INVALID_QUOTA_VALUE` | 422 | new_limit < 0 |
| `BROADCAST_EMPTY_MESSAGE` | 422 | message 空白 |
| `BROADCAST_TOO_MANY_RECIPIENTS` | 422 | active user > 50k |

### 5.2 日志（Log 表）

所有 admin 写操作 actor_type='admin'，metadata 约定：

- `admin.user.status_change`：`{from, to}`
- `admin.user.quota_update`：`{oldLimit, newLimit}`
- `admin.violation.resolve`：`{caseId, fileId}`
- `admin.file.rescan_requested`：`{fileId, objectId}`
- `admin.notification.broadcast`：`{broadcastId, recipientCount}`
- `admin.rule.*`：现有不动

### 5.3 事件（in-process publisher）

- `files.rescan_requested {objectId, fileId, requestedBy}` —— 新增
- `notification.broadcast_completed {broadcastId, recipientCount, durationMs}` —— 新增

事件名固化，未来接 RabbitMQ 不改 service 签名（agents.md §7）。

### 5.4 测试矩阵

**后端 `app/tests/`（pytest + httpx AsyncClient）**

| 模块 | 测例 |
|---|---|
| admin_users | list 默认分页 / search / status 切换 / 最后一名 admin 不能 suspend / 普通用户调 admin 接口 403 |
| admin_storage | quota 低于已用 → 409 / 正常调整 → 200 / usage-trend 7 日点数 == 7 / Redis 缓存命中 |
| admin_files | virusStatus 过滤 / rescan 写 ObjectScanResult + 发事件（spy publisher） |
| admin_moderation | resolve 已 resolved 案件 → 409 / 正常 resolve 改状态 + 写日志 |
| admin_logs | userId/operation 过滤 / 时间范围过滤 / 普通用户 403 |
| admin_notifications | broadcast 多用户落库 / 同 broadcastId 重入幂等 / 空 message → 422 |
| admin_system | health 字段齐全 / Redis 无 key 时返回空 rate-limit |

**前端 `web/tests/`（vitest + @vue/test-utils + MSW 现有 mock）**

| 模块 | 测例 |
|---|---|
| ConsoleSidebar | 当前路由高亮 / 非 admin 不渲染 |
| AdminTable | 空态 / 分页换页 / sort emit |
| 子页 smoke（每页 1 个） | 挂载即拉数据 / 字段渲染 |
| router | `/dashboard` redirect 到 `/console/overview` |

### 5.5 性能与回归边界

- `/admin/users` perPage 默认 20，max 100；客户端不全量加载
- `/admin/storage/usage-trend` Redis 缓存 5 min
- `/admin/notifications/broadcast` 上限 50k 用户；超出走 422，后续接异步队列
- `/dashboard` redirect 保护书签/外链
- 现有 `RegistrationEmailDomainRule` 路由/服务零改动

### 5.6 五件套一致性自检（PR 合入前清单）

每个新接口逐项打勾：

- [ ] `web/src/types/<域>.d.ts` 加/对齐类型
- [ ] `web/src/api/<域>.ts` 加函数
- [ ] `web/src/mock/handlers/<域>.ts` 同步路径/字段/分页壳
- [ ] `app/src/fileflash/schemas/admin/<域>.py` 加 Pydantic schema（by_alias=True）
- [ ] `app/src/fileflash/services/admin/<域>.py` 实现
- [ ] `app/src/fileflash/routers/admin_<域>.py` 接 `require_admin` 并 `api_success`
- [ ] 注册到 `routers/__init__.py` 的 `api_router.include_router(...)`
- [ ] 后端 pytest 覆盖正向 + 一个边界
- [ ] 前端子页对该接口渲染验过
