# P7 — Agent 赛道前端重塑（Workspace + Skills）

**Date:** 2026-05-20
**Phase:** P7（部分） of the 8-phase Industrial Dashboard redesign
**Scope this spec:** `pages/agent/workspace/AgentWorkspace.vue`、`pages/agent/skills/AgentSkills.vue`、`pages/agent/AgentLayout.vue`
**Out of scope this spec:** Admin Dashboard 重写、其它页面的 Naive UI 清理、后端 conversation 持久化 API、agent 多模态 / 文件附件输入

参考：
- 设计身份 → `mem:frontend_aesthetic`（Industrial Dashboard / Electric Lime / IBM Plex + JetBrains Mono / 直角硬边）
- 阶段背景 → `mem:frontend_redesign_progress`（P0–P4 已完成，P7 待开始）
- 总 spec → `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md`

---

## 1. 动机

当前 Agent Workspace 是 ChatGPT 风格的圆角气泡 + 重 Naive UI 依赖，与项目的 Industrial Dashboard 身份完全冲突。同时 `bun run build` 因 TS 联合类型未收窄而失败，CI 红。

要解决的三件事：
1. **CI 失败**：`AgentWorkspace.vue` 161/162/164 行联合类型问题 + 234 行未使用变量
2. **风格不符**：圆角气泡、generic SaaS 蓝感、滥用 NSpin、缺失工业风密度与等宽
3. **结构不符**：直接用 Naive UI 组件、违反 P1–P4 建立的 atoms/molecules/organisms 三层架构

---

## 2. 总体方针

- **零 Naive UI**：本次新增/重写的 agent 页面、organisms、补位 molecules 不得 `import 'naive-ui'`
- **页面 ≤ 100 行**：沿用 P3/P4 硬指标；状态与副作用全部下放到 composables
- **三栏工程仪表盘式**：取代 ChatGPT 风对话气泡布局（已与用户确认）
- **localStorage 持久化 conversations**：不动后端
- **保留 Spring & Bloom 动效语言**：使用既有 `--mo-*` token

---

## 3. 架构

### 3.1 AgentWorkspace 三栏布局

```
┌──────────┬────────────────────────────────────────┬─────────────────┐
│ SESSIONS │  TIMELINE                              │ INSPECTOR       │
│ (240px,  │  (1fr)                                 │ (320px,         │
│  折叠)    │                                        │  ≥1280 常驻,     │
│          │  Turn #N  19:14:02 ─────────           │  <1280 抽屉)     │
│ ▌active  │  ► you: …                              │ Skill           │
│   …23m   │  ◯ plan / executing / done             │ Hash            │
│  ...     │  PlanActionRow ×N                      │ Cost            │
│          │  [ EXECUTE ]                           │ Warnings        │
│ + NEW    │                                        │                 │
│          │ ──────── TaskInputDock ──────────────  │                 │
│          │ > 输入新任务…  policy [Confirm ▼] [SEND]│                 │
└──────────┴────────────────────────────────────────┴─────────────────┘
```

| 区 | Organism | 职责 |
|---|---|---|
| 左 (240px, 可折叠) | `SessionList` | conversations 列表，localStorage 持久化；active 用 2px lime 左条 |
| 中 (1fr) | `TaskTimeline` + `TaskInputDock` | turn 时间线，底部固定输入栏 |
| 右 (320px, ≥1280 常驻) | `PlanInspector` | 选中 turn 的 skill / hash / cost / actions / warnings 详情 |

<1280 视口：右栏折叠为右侧抽屉，点击 turn 才滑入。

### 3.2 AgentSkills 单列布局

`SegmentedControl(Marketplace / My Skills) → SkillGrid(+Pagination) → SkillEditorPanel(slide-in 右抽屉) → SkillImportPanel(admin only, 折叠区)`

不再用 NModal 弹窗，编辑改用与 PlanInspector 同款的右抽屉，保持视觉/动效一致。

### 3.3 AgentLayout（内 tab 切换）

`pages/agent/AgentLayout.vue`：用 `SegmentedControl` + 两个 router 链接替换 NSpace/NButton；去掉 radial-gradient hero（不合工业仪表盘语言），改一行 `[ FILEFLASH · AGENT ]` 小写大字距标题 + 右侧 tab。目标 ≤ 60 行。

---

## 4. 新增组件清单

### 4.1 补位 molecules（4 个）

| 文件 | 替代 | API |
|---|---|---|
| `components/molecules/Modal.vue` | NModal | `<Modal :open size="sm\|md\|lg" @close>` + slot `header/body/footer` |
| `components/molecules/Pagination.vue` | NPagination | `<Pagination v-model:page :page-size :total>`，JetBrains Mono 数字 |
| `components/molecules/FileDrop.vue` | NUpload | `<FileDrop accept @file>`，返回 File 对象 |
| `components/molecules/Select.vue` | NSelect | `<Select v-model :options size="sm">`，基于 atoms/DropdownMenu |

每个配 `*.spec.ts`，≥3 vitest case（mount / 关键事件 / 边界）。

### 4.2 Agent organisms（10 个，`components/organisms/agent/`）

| 文件 | 用途 |
|---|---|
| `SessionList.vue` | 左栏：列出 sessions、active 高亮、新建/删除/切换 |
| `SessionItem.vue` | 单条 session（title + relativeTime + delete hover） |
| `TaskTimeline.vue` | 中栏滚动容器：迭代 turns，自动滚到底 |
| `TurnEntry.vue` | 单 turn：user 行 + agent 行（plan summary + actions + execute 按钮 + warnings） |
| `PlanActionRow.vue` | 单 step：step# / tool 名 / side-effect bar / input JSON 折叠 |
| `TaskInputDock.vue` | 底部输入区：textarea + policy Select + Send |
| `PlanInspector.vue` | 右栏：skill / hash / cost / warnings 详情 |
| `SkillCard.vue` | Skills 页：单卡片 |
| `SkillEditorPanel.vue` | Skills 页：右抽屉编辑器（表单 + advanced JSON 折叠） |
| `SkillImportPanel.vue` | Skills 页（admin only）：mode 选择 + FileDrop + JSON textarea |

`TurnEntry` / `SessionList` / `SkillCard` 各加 1 个 smoke test。其余 organism 不强制单测（页面集成已覆盖）。

### 4.3 Composables（2 个）

| 文件 | 职责 |
|---|---|
| `composables/useAgentSession.ts` | conversation CRUD + active 切换 + localStorage 持久化 + sendMessage/execute/cancel + polling 管理 |
| `composables/useAgentSkills.ts` | marketplace/mySkills 分页 + 搜索 debounce + create/update/delete/import |

LocalStorage key：`fileflash.agent.sessions.v1`（带版本号，便于以后破坏性升级）。

每个 composable ≥4 vitest case：
- `useAgentSession`：发消息→plan polling→succeeded、execute→polling、cancel、localStorage roundtrip
- `useAgentSkills`：load+search debounce、create、update、import upsert

---

## 5. TS 错误修复策略

**根因**：`getAgentJob<T>` 是泛型，但 `pollJob(msg, jobId, kind)` 用运行时 string 分支决定泛型，TS 静态推不出 `job.result` 的具体类型。

**修法**：拆成两个泛型化的 helper，编译期分开（移入 `useAgentSession.ts`）：

```ts
async function pollPlanJob(msg: ChatMessage, jobId: string) {
  const job = await getAgentJob<AgentPlanResult>(jobId);
  if (job.status === 'succeeded' && job.result) {
    msg.planResult = job.result;
    msg.planHash = job.result.planHash;
  }
  // status / errorMessage / polling-timer 逻辑同前
}

async function pollExecuteJob(msg: ChatMessage, jobId: string) {
  const job = await getAgentJob<AgentExecutionResult>(jobId);
  if (job.status === 'succeeded' && job.result) {
    msg.executeResult = job.result;
  }
  // ...
}
```

**未使用变量**：删 `reactiveUserMsg`（user 消息不再被改，不需要响应式代理）。

收益：页面层完全没有 polling / 泛型代码，TS 不会再卡住这里。

---

## 6. 视觉与交互语言

完全锚定 Industrial Dashboard token，**不引入新颜色或字体**。

### 6.1 几何 / 颜色

- 直角硬边为主，仅 `var(--radius-sm)` 用于 chips/buttons；所有 panel 直角
- 三栏间 1px hairline 分隔（`var(--color-border)`），不用阴影
- Active session：左侧 2px lime 条（`background: var(--ac)`），文字色升一档
- 章节标签全部 uppercase + `letter-spacing: 0.18em`（`SESSIONS` / `TIMELINE` / `INSPECTOR` / `MARKETPLACE` / `MY SKILLS`）

### 6.2 字体规则

- IBM Plex Sans：plan summary、skill desc、welcome 提示
- JetBrains Mono + `font-feature-settings: "tnum"`：hash、tool 名、token/call/sec 数字、timestamp、step#、skillKey
- 标签栏：`var(--text-label)` (12-13px) + mono

### 6.3 side-effect 视觉

- `read` → 灰中性 Tag（`var(--color-text-tertiary)` 框）
- `write` → 用当前 accent 的 desaturated 变体，左侧加 mono 字符 `▲`
- 不再用圆角 NTag

### 6.4 状态色（4 个）

- `succeeded` → `var(--ac)` lime
- `running` → 顶部 2px 动态进度条（既有 `Bar` atom），**不**用 spinner 满天飞
- `failed` → `var(--color-danger)`
- `canceled` → 中性灰 + 删除线

### 6.5 动效（沿用 Spring & Bloom token）

- TurnEntry 入场：`opacity 0→1` + `translateY(4px→0)`，220ms `var(--mo-easing)`
- Execute 按钮按下：scale 0.97
- session 切换：右侧两栏 fade 120ms（不做滑动）
- Inspector 抽屉：从右滑入 200ms
- `prefers-reduced-motion: reduce`：禁用所有 transition

### 6.6 键盘

- `Enter` 发送，`Shift+Enter` 换行（保留）
- `Cmd/Ctrl+K` 新建 session（新）
- `Cmd/Ctrl+/` 在 Workspace ↔ Skills 切换（新）

### 6.7 Welcome 空态

去掉圆形头像 SVG，改一段 mono 提示 + 3 个直角 chip 示例任务（沿用 P2 既有 hint-chip 风格但去圆角）。

---

## 7. `/__dev/library` 更新

- 新增 `Molecules · Forms` 段展示 Modal / Pagination / FileDrop / Select
- 新增 `Organisms · Agent` 段展示所有 9 个 agent organisms 的 isolated 状态（loading / empty / success / error）

---

## 8. 验收清单

实现完成后必须全过：

1. `bun run build` 通过（vue-tsc strict + vite build），CI 绿
2. `bun run test` 通过，新增 case 全部绿
3. `pages/agent/workspace/AgentWorkspace.vue` ≤ 100 行
4. `pages/agent/skills/AgentSkills.vue` ≤ 100 行
5. `pages/agent/AgentLayout.vue` ≤ 60 行
6. `grep -r "naive-ui" web/src/pages/agent web/src/components/organisms/agent` 零结果
7. 新增的 4 个 molecules 自身不依赖 Naive UI
8. `/__dev/library` 可访问，新段落正常渲染
9. localStorage key `fileflash.agent.sessions.v1`：刷新后会话保留、删除生效
10. 三个 execution policy（planOnly / confirm / autopilot）路径手测通过
11. `prefers-reduced-motion: reduce` 下无 transition

---

## 9. P8 清理预留（不本次做）

- 旧 `components/common/ConfirmDialog.vue` / `PromptDialog.vue` / `ShareDialog.vue` / `MoveItemDialog.vue` / `SelectFolderDialog.vue` / `FilePreviewDialog.vue` 都还用 NModal，迁移到新 `Modal` molecule
- 旧 `components/layout/` 与 `components/common/FolderTreeNode.vue` / `FileTreeNode.vue` / `Breadcrumb.vue` 已被 organisms 取代，列入 P8 删除

---

## 10. 交付物

- 本 spec（提交 git）
- 1 个 implementation plan（通过 `superpowers:writing-plans` 生成）
- 按阶段切的多个 PR-ready commit：molecules → composables → organisms → pages → /__dev/library → 删旧文件
