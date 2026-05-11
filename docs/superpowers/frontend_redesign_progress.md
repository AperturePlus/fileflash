---
name: Frontend redesign progress
description: Phase tracker for the FileFlash Industrial Dashboard redesign — which phases (P0–P8) have landed
type: project
originSessionId: 19f3a1e2-b428-4855-87de-e6c9ca410525
---
FileFlash 前端重塑分 8 阶段（P0 Foundation → P8 Cleanup）。Spec 在
`docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md`。
每个阶段的 plan 在 `docs/superpowers/plans/2026-05-11-frontend-redesign-p<N>-*.md`。

**已完成**：
- **P0 Foundation**（2026-05-11）— 设计 token 系统就位：
  - `web/src/styles/tokens/{color,color.accent,type,space,motion,edge,shadow}.css`
  - `web/src/styles/{theme,reset,legacy-compat}.css`
  - `web/index.html` 加了 hydration script + 字体 preconnect/link
  - `web/src/style.css` 缩为 11 行 import shim
  - 三轴切换实测通过：`data-theme` (dark/light) × `data-accent` (lime/amber/oxide) × `data-motion` (spring/tight/reduced)
  - Legacy compat 层让所有现有组件继续渲染（不动 Vue/store）
  - 注意：现有页面（Login/Register 等）的 hardcoded 样式 P0 不动；视觉转换从 P2 shell 开始
- **P1 Atoms + Molecules**（2026-05-11）— 13 atoms + 14 molecules + Vitest 基建 + dev library 路由
  - Vitest + @vue/test-utils + happy-dom，token-aware `mount` 助手 + `readToken`
  - Atoms: Text / MonoNumber / Divider / Bar / Dot / Icon (+ icons.ts 注册表) / Spinner / Surface / Input / Checkbox / Radio / Toggle / KeyHint
  - Molecules: Button / IconButton / TextField / SearchField / Badge / Tag / StatBlock / ProgressBar / BreadcrumbItem / MenuItem / Tab / SegmentedControl / Toolbar / Avatar
  - `/__dev/library` 路由（仅 dev 模式可访问）展示所有组件 × theme × accent × motion 组合
  - 172 个单元测试全部通过，类型检查通过，生产构建成功

**进行中 / 待开始**：
- **P2** Shell + Templates — MainLayout/AuthLayout/BareLayout/ShareLayout/AgentLayout + 6 个 shell organism + 路由层级调整（这里开始视觉变化）
- **P3** Core File Path — MyFiles + 9 个 files organism
- **P4** Other File Surfaces — Shared / Trash / ShareAccess
- **P5** Public Auth Flow — Login / Register / ForgotPassword / VerifyEmail
- **P6** Account — Profile / Settings + preferencesStore（替换 themeStore）
- **P7** Admin & Agent — Dashboard / AgentWorkspace / AgentSkills + 移除 Naive UI 依赖
- **P8** Cleanup — 删除 legacy-compat、旧目录、Skills.vue、空 layouts/

**How to apply**：开始下一阶段时先读 spec 和上一阶段 plan，确认验收标准全过；否则补完再前进。新阶段 plan 写到 `docs/superpowers/plans/2026-05-11-frontend-redesign-p<N>-*.md`。
