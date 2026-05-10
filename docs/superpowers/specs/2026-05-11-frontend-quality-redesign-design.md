# FileFlash 前端质感重塑 · 设计文档

**日期**：2026-05-11
**状态**：待审阅
**作者**：本会话产出
**范围**：`web/` 全部 13 个有效页面 + 整套样式系统 + 组件库结构 + 动效语言 + 偏好持久化

---

## 0. 背景与动机

FileFlash 当前 web 端 UI 大部分由 AI 在 2025 年生成，存在三类典型缺陷：

1. **字体无质感**：使用 Manrope（典型 SaaS 几何字），字重 400 默认偏轻，缺少分层；中文 fallback 直接落到 PingFang/微软雅黑，无搭配设计。
2. **组件无质感且互相牵动**：`MyFiles.vue` 564 行、`Dashboard.vue` 607 行、`Settings.vue` 921 行——大型 SFC 内联样式，原子组件未抽离。颜色、按钮、阴影、动效曲线（`cubic-bezier(0.4, 0, 0.2, 1)`）和 `transform: translateY(-1px)` hover lift 散布全站，是典型的"AI 生成器默认审美"。
3. **交互无质感**：`<router-view>` 顶层包了 `<transition mode="out-in">`，导致路由切换时整个 MainLayout（含 header/sidebar）淡出再淡入——即"切页像刷新"的根因。

本次重塑目标是**让产品有自己的工程感声音**，而非 AI 默认的 SaaS 中间值。

---

## 1. 关键决策摘要

| 维度 | 决策 | 备注 |
|---|---|---|
| 改造范围 | **全套重塑** | 设计 token + 组件库 + 动效 + 页面切换 |
| 表面覆盖 | **全部 13 页** | 含 Login/Register/ForgotPassword/VerifyEmail/MyFiles/Shared/Trash/Profile/Settings/AgentWorkspace/AgentSkills/Dashboard/ShareAccess |
| 美学方向 | **Industrial Dashboard**（候选 B） | 对标 Linear 暗色 / Datadog / Vercel CLI / Bloomberg Terminal |
| 主题策略 | **单一身份**（不做多套设计语言切换） | 但点缀色与动效偏好可切换 |
| 明暗 | **Dark + Light 双变体** | 同一身份语言 |
| 主点缀色 | **Electric Lime `#B6FF3D`** | Amber `#FFB400` / Oxide `#FF4F2C` 用户可切换 |
| 字体 | **IBM Plex Sans + IBM Plex Sans SC + JetBrains Mono** | 工程文档/代码字体家族 |
| 信息密度 | **舒适**（行高 32px / 字号 13.5px） | 与 Spring 动效协调 |
| 动效 | **Spring & Bloom** 默认 / **Tight Ease-Out** 可切换 / `prefers-reduced-motion` 自动降级 | 三套 motion token |
| 组件架构 | **完整 Atomic Design**（components/ 内 atoms / molecules / organisms / templates 四层 + pages/ 独立） | 严格分层 |
| 旧目录 | **直接删除迁移**（`components/common/` `components/layout/` `pages/files/components/` `web/src/layouts/` 全清） | 不保留过渡 |
| 死代码 | **删 `pages/skills/Skills.vue`** | 路由已重定向到 `/agent/skills` |
| 过渡期混搭 | **接受**（产品未上线） | P2 完成后 shell 已 B 风、内容区还在迁移 |

---

## 2. 设计 Token 体系

### 2.1 目录结构

```
web/src/styles/
├── tokens/
│   ├── color.css          # B-dark + B-light 全套语义色
│   ├── color.accent.css   # Lime / Amber / Oxide 三套点缀色
│   ├── type.css           # 字体家族 / 字号 / 字重 / 行高 / 字距
│   ├── space.css          # 4-8-12-16-24-32-48-64 八档间距
│   ├── motion.css         # Spring + Tight + reduced 三套
│   ├── edge.css           # 圆角 0/2/4 + 边框 1px 三档
│   └── shadow.css         # 仅深色用的微弱阴影（B 风极少用阴影）
├── theme.css              # 主入口，按 [data-theme]/[data-accent]/[data-motion] 切换
└── reset.css              # 清掉 box-sizing / margin / font 之类
```

### 2.2 颜色 Token

**Dark surface 阶梯**（语义化命名）：

| Token | 值 | 用途 |
|---|---|---|
| `--surface-inset` | `#0A0A0C` | 内陷区 / 输入框底 |
| `--surface-base` | `#0E0E10` | 基础底色 |
| `--surface-raised` | `#15151A` | 卡片 / header 背景 |
| `--border-subtle` | `#1F1F23` | 行分割线 |
| `--border-default` | `#2A2A30` | 卡片 / 输入框边框 |
| `--text-dim` | `#6A6A6A` | 时间戳 / 辅助 |
| `--text-secondary` | `#B8B5AC` | 副本文本 |
| `--text-primary` | `#E8E6DF` | 正文（暖白） |

**Light surface 阶梯**：

| Token | 值 | 用途 |
|---|---|---|
| `--surface-raised` | `#FFFFFF` | 卡片 |
| `--surface-base` | `#FBFAF6` | 基础（暖白纸面） |
| `--surface-inset` | `#F2F0EA` | 内陷区 |
| `--border-subtle` | `#EAE7DE` | 行分割 |
| `--border-default` | `#DAD6CB` | 卡片边 |
| `--text-dim` | `#9D9A91` | |
| `--text-secondary` | `#4F4D47` | |
| `--text-primary` | `#1B1A17` | 正文（暖黑） |

**点缀色三套**（CSS 变量化，仅切换 `--ac` 系列）：

| 名 | `--ac` | `--ac-rgb` | `--ac-fg` | 浅色变体 |
|---|---|---|---|---|
| Lime（默认） | `#B6FF3D` | `182,255,61` | `#0E0E10` | `#5C9E00` |
| Amber | `#FFB400` | `255,180,0` | `#0E0E10` | `#B07700` |
| Oxide | `#FF4F2C` | `255,79,44` | `#0E0E10` | `#C43617` |

**语义状态色**（双主题共用 RGB，仅 alpha 不同）：

```
--status-success: #4ADE80
--status-warning: #FFB400
--status-error:   #FF4F2C
--status-info:    #60A5FA
```

### 2.3 字型 Token

```css
--font-sans: 'IBM Plex Sans', 'IBM Plex Sans SC', 'PingFang SC', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;

--text-display: 32px;  /* 头部大标题，字重 600，letter-spacing -0.02em，line-height 1.05 */
--text-h1:      22px;  /* 字重 600，letter-spacing -0.015em */
--text-h2:      17px;  /* 字重 600，letter-spacing -0.01em */
--text-body:    13.5px;/* 字重 400，line-height 1.55 */
--text-small:   12px;
--text-label:   10px;  /* 字距 0.18em / uppercase */
--text-data:    12px;  /* mono + tnum */
--text-data-big: 22px; /* mono，accent 色，关键数字 */
```

字体加载策略：`index.html` 用 `<link rel="preload" as="font">` 预加载 woff2，`font-display: swap` 但 Plex 优先。

### 2.4 间距 Token（4px 基础刻度）

```css
--sp-xs: 4px; --sp-sm: 8px; --sp-md: 12px; --sp-lg: 16px;
--sp-xl: 24px; --sp-2xl: 32px; --sp-3xl: 48px; --sp-4xl: 64px;

--row-h: 32px;        /* 文件行高 */
--form-gap: 16px;
--section-gap: 32px;
```

### 2.5 动效 Token（双套预设）

```css
/* Spring（默认） */
[data-motion="spring"] {
  --mo-duration-fast: 200ms;
  --mo-duration-mid: 240ms;
  --mo-duration-slow: 280ms;
  --mo-easing: cubic-bezier(0.34, 1.56, 0.64, 1);
  --mo-press-scale: 0.94;
  --mo-hover-bloom: 0 0 24px rgba(var(--ac-rgb), 0.4);
}

/* Tight（可切换） */
[data-motion="tight"] {
  --mo-duration-fast: 120ms;
  --mo-duration-mid: 140ms;
  --mo-duration-slow: 180ms;
  --mo-easing: cubic-bezier(0.2, 0.8, 0.2, 1);
  --mo-press-scale: 0.96;
  --mo-hover-bloom: none;
}

/* Reduced（自动） */
[data-motion="reduced"] {
  --mo-duration-fast: 0ms;
  --mo-duration-mid: 0ms;
  --mo-duration-slow: 0ms;
  --mo-easing: linear;
  --mo-press-scale: 1;
  --mo-hover-bloom: none;
}
```

### 2.6 边缘 Token

```css
--radius-0: 0;     /* 卡片 / 按钮 / 行 */
--radius-sm: 2px;  /* 输入框 / 选中块 */
--radius-md: 4px;  /* 徽章 / 浮层 */

--border-hairline: 1px;
```

阴影几乎不用——B 风靠对比度和 hairline 制造层次，仅在 `--shadow-overlay` 用于 dialog backdrop。

### 2.7 切换机制

通过 `<html>` 三个 data 属性独立切换：

```html
<html data-theme="dark" data-accent="lime" data-motion="spring">
```

旧 `web/src/style.css` 的 `:root { ... }` 大杂烩**全部删除并迁入 token 体系**。

---

## 3. Atomic Design 组件结构

### 3.1 文件组织

```
web/src/components/
├── atoms/           # 12 个，每个 30-80 行
│   ├── Text.vue            # variant: display/h1/h2/body/small/label/data
│   ├── MonoNumber.vue      # 等宽数字 + tnum
│   ├── Icon.vue            # name + size，配 icons.ts 注册表
│   ├── Divider.vue
│   ├── Bar.vue             # 进度条 / 状态条原子
│   ├── Dot.vue             # 状态圆点
│   ├── Spinner.vue         # B 风扫描线 loader
│   ├── Surface.vue         # 主题感知容器
│   ├── Input.vue           # 裸 input
│   ├── Checkbox.vue
│   ├── Radio.vue
│   ├── Toggle.vue
│   └── KeyHint.vue         # ⌘K 键位提示
│
├── molecules/       # 13 个，每个 80-200 行
│   ├── Button.vue
│   ├── IconButton.vue
│   ├── TextField.vue
│   ├── SearchField.vue
│   ├── Badge.vue
│   ├── Tag.vue
│   ├── StatBlock.vue       # Label + MonoNumber + delta
│   ├── ProgressBar.vue
│   ├── BreadcrumbItem.vue
│   ├── MenuItem.vue
│   ├── Tab.vue
│   ├── SegmentedControl.vue # 派生 ThemePicker / AccentPicker / MotionPicker
│   ├── Toolbar.vue
│   └── Avatar.vue
│
├── organisms/       # 约 28 个，每个 150-400 行（实施时具体粒度可微调）
│   ├── files/
│   │   ├── FileRow.vue
│   │   ├── FileTable.vue           # 替代旧 FileItemsView，带 mode: list|grid|tree prop
│   │   ├── FileToolbar.vue
│   │   ├── FileDetailPanel.vue
│   │   ├── FileTreeNode.vue        # 迁移自 common/
│   │   ├── FolderTreeNode.vue      # 迁移自 common/
│   │   ├── EmptyState.vue
│   │   ├── UploadProgressTray.vue
│   │   └── BulkActionBar.vue
│   ├── shell/
│   │   ├── AppHeader.vue
│   │   ├── LeftSidebar.vue
│   │   ├── RightSidebar.vue
│   │   ├── Footer.vue
│   │   ├── StorageStatusWidget.vue
│   │   └── UserMenu.vue
│   ├── dialogs/
│   │   ├── ConfirmDialog.vue       # 迁移
│   │   ├── PromptDialog.vue        # 迁移
│   │   ├── ShareDialog.vue         # 迁移
│   │   ├── MoveItemDialog.vue      # 迁移
│   │   ├── SelectFolderDialog.vue  # 迁移
│   │   └── ExtractArchiveDialog.vue # 拆分为 dialog 主体 + ArchiveContentTree + ConflictResolver 三件
│   ├── overlay/
│   │   ├── ToastStack.vue          # 迁移
│   │   ├── DropdownMenu.vue        # 迁移
│   │   └── Breadcrumb.vue          # 迁移
│   ├── auth/
│   │   └── AuthForm.vue            # Login/Register/ForgotPassword 共用，靠 mode prop 区分
│   └── agent/
│       ├── AgentChatPanel.vue
│       └── AgentSkillCard.vue
│
└── templates/       # 5 个，每个 < 150 行
    ├── MainLayout.vue       # 应用 shell（header + 双 sidebar + 内容区 router-view）
    ├── AuthLayout.vue       # 居中认证卡
    ├── AgentLayout.vue      # agent 工作区 shell
    ├── ShareLayout.vue      # 公开分享页 shell
    └── BareLayout.vue       # 全屏状态页（VerifyEmail）
```

**总组件数**：约 60 个文件（vs 当前 25 个），但**总代码行数减少 ~30%**（消除重复样式 + 拆分大型 SFC）。具体计数实施时按需微调。

### 3.2 约束

- 13 个 page 文件每个 ≤ 100 行；任何超出即"还有 organism 没抽出来"。
- 每个组件**只导出自身 + 自身 props 的 TS 类型**；不再有共享的 `types/` 大锅菜。
- `web/src/components/index.ts` 是公开门面，pages 只从这里 import。
- Naive UI 仅保留 `App.vue` 的三个 Provider；agent 三页的 `NDropdown` / `NButton` 在 P7 替换为本项目 molecules。

### 3.3 内置组件预览页

新增仅 dev 模式可访问的路由 `/__dev/library`（生产环境不暴露），列出全部 atoms/molecules/organisms 在不同状态下的样子（hover / active / disabled / loading / error / empty）。这是为后续维护和回归测试服务的"活文档"。

---

## 4. 8 阶段构建顺序

每阶段都是一次独立可发布的增量，集成风险最小化：

| 阶段 | 内容 | 主要产出 |
|---|---|---|
| **P0** Foundation | Token 全套 + 旧 `style.css` 拆解 + 字体预加载 | `styles/tokens/*` + `theme.css` |
| **P1** Atoms + Molecules | 12 atoms + 13 molecules + dev library 路由 | `components/atoms/*` + `components/molecules/*` |
| **P2** Shell + Templates | MainLayout/AuthLayout/BareLayout/ShareLayout/AgentLayout + 6 个 shell organism + 路由层级调整 | shell 已 B 风，内容区暂留旧版 |
| **P3** Core File Path | MyFiles → 9 个 files organism | 9 organisms + 新 MyFiles.vue ≤ 100 行 |
| **P4** Other File Surfaces | Shared / Trash / ShareAccess（复用 FileTable） | 三页迁移完成 |
| **P5** Public Auth Flow | Login / Register / ForgotPassword / VerifyEmail（共享 AuthForm） | 四页迁移完成 |
| **P6** Account | Profile / Settings（含 ThemePicker / AccentPicker / MotionPicker） | 偏好持久化打通 |
| **P7** Admin & Agent | Dashboard / AgentWorkspace / AgentSkills，移除 Naive UI 依赖（保留 Provider） | 全部 13 页迁移完成 |
| **P8** Cleanup | 删 `Skills.vue` / `pages/files/components/` / `components/common/` / `components/layout/` / 空 `web/src/layouts/` | 旧目录清零 |

---

## 5. 路由与"切页像刷新"修复

### 5.1 根因

`web/src/App.vue:23-27` 在顶层包了 transition：

```vue
<router-view v-slot="{ Component }">
  <transition name="page" mode="out-in">
    <component :is="Component" />
  </transition>
</router-view>
```

但 `/files`、`/shared`、`/trash` 等路由**全部是 MainLayout 的 children**。Vue Router 复用 MainLayout 实例，但顶层 transition 把整个 MainLayout（header + sidebar + footer）一起淡出再淡入——所以"像刷新"。

### 5.2 修复

**App.vue** 删掉 transition：

```vue
<router-view />
```

**templates/MainLayout.vue** 内部包 transition，仅作用于内容区子 router-view：

```vue
<router-view v-slot="{ Component, route }">
  <transition name="page-fade" mode="out-in">
    <component :is="Component" :key="route.path" />
  </transition>
</router-view>
```

`AuthLayout` / `AgentLayout` / `ShareLayout` 同模式。

### 5.3 路由层级调整

```
公共：
  /login                  → AuthLayout > Login
  /register               → AuthLayout > Register
  /forgot-password        → AuthLayout > ForgotPassword
  /verify-email           → BareLayout > VerifyEmail
  /share/:shareLink       → ShareLayout > ShareAccess

私域（requiresAuth）：
  /                       → MainLayout (redirect /files)
    /files                → MyFiles
    /shared               → SharedWithMe
    /trash                → Trash
    /profile              → Profile
    /settings             → Settings
    /dashboard            → Dashboard (requiresAdmin)
    /agent                → AgentLayout
      /agent              → AgentWorkspace
      /agent/skills       → AgentSkills
```

`web/src/layouts/` 空目录删除；templates 统一在 `components/templates/`。

### 5.4 transition 与 motion token 联动

```css
[data-motion="spring"] .page-fade-enter-active,
[data-motion="spring"] .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing),
              transform var(--mo-duration-mid) var(--mo-easing);
}
[data-motion="spring"] .page-fade-enter-from { opacity: 0; transform: scale(0.98); }
[data-motion="spring"] .page-fade-leave-to   { opacity: 0; transform: scale(1.02); }

[data-motion="tight"] .page-fade-enter-from { opacity: 0; transform: translateX(-6px); }
[data-motion="tight"] .page-fade-leave-to   { opacity: 0; transform: translateX(6px); }

[data-motion="reduced"] .page-fade-enter-active,
[data-motion="reduced"] .page-fade-leave-active { transition: none; }
```

### 5.5 附带修复

- `App.vue:23` 的 `<Suspense>` fallback 当前显示 "Loading..." 文本——改为 `Spinner` atom，背景保持当前页面（不再 layout shift）。
- 路由切换时 sidebar 的 active 项用 `transition: color var(--mo-duration-mid) var(--mo-easing)` 平滑过渡到 accent，配合 M3 弹性曲线。

---

## 6. 用户偏好与三轴切换

### 6.1 三个独立轴

| 轴 | 取值 | 默认 | 持久化 |
|---|---|---|---|
| `theme` | `dark` / `light` / `system` | `system` | `localStorage` `ff.pref` |
| `accent` | `lime` / `amber` / `oxide` | `lime` | 同 |
| `motion` | `spring` / `tight` / `system` | `system` | 同 |

### 6.2 Pinia store

新建 `web/src/store/preferences.ts`，**替换并扩展** 现有 `store/theme.ts`（旧 store 删除）：

```ts
export const usePreferencesStore = defineStore('preferences', {
  state: () => ({ theme: 'system', accent: 'lime', motion: 'system' }),
  actions: {
    apply() {
      const html = document.documentElement;
      html.dataset.theme = this.resolvedTheme;
      html.dataset.accent = this.accent;
      html.dataset.motion = this.resolvedMotion;
    },
    setTheme(v) { this.theme = v; this.apply(); },
    setAccent(v) { this.accent = v; this.apply(); },
    setMotion(v) { this.motion = v; this.apply(); },
  },
  getters: {
    resolvedTheme: (s) => s.theme === 'system'
      ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : s.theme,
    resolvedMotion: (s) => {
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) return 'reduced';
      return s.motion === 'system' ? 'spring' : s.motion;
    },
  },
  persist: { storage: localStorage, key: 'ff.pref' },
});
```

### 6.3 Hydration（避免 FOUC）

`index.html` 的 `<head>` 嵌入同步 script，在 Vue 挂载前应用 data 属性：

```html
<script>
  (function() {
    var p; try { p = JSON.parse(localStorage.getItem('ff.pref') || '{}'); } catch(e) { p = {}; }
    var theme = p.theme === 'dark' || p.theme === 'light' ? p.theme :
      (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var motion = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'reduced' :
      (p.motion === 'tight' ? 'tight' : 'spring');
    var h = document.documentElement;
    h.dataset.theme = theme;
    h.dataset.accent = ['amber','oxide'].includes(p.accent) ? p.accent : 'lime';
    h.dataset.motion = motion;
  })();
</script>
```

### 6.4 系统偏好监听

store 初始化时绑定 `matchMedia('(prefers-color-scheme: dark)').addEventListener('change', ...)` 和 `prefers-reduced-motion`，系统切换自动 `apply()`。

### 6.5 Settings 页面 UI

```
偏好设置
├── 外观
│   ├── 主题：[ 浅色 | 深色 | 跟随系统 ]   <- ThemePicker (SegmentedControl)
│   └── 点缀色：[ ● Lime  ● Amber  ● Oxide ]  <- AccentPicker (色块)
└── 动效
    ├── 语言：[ 弹性 | 紧凑 | 跟随系统 ]   <- MotionPicker (SegmentedControl)
    └── 系统已开启减弱动效时此项无效（自动降级）
```

三个 picker 都是基于 `SegmentedControl` molecule 派生。

---

## 7. 作用域之外（明确不做）

- **不**新增产品功能（不加新页面、不改业务流程、不动后端 API）
- **不**改变 i18n 接入方式（保留 `localeStore.t()` + zh/en 两份语言文件）
- **不**引入 Tailwind / Storybook / CSS-in-JS / 其他设计系统库
- **不**做移动端原生适配（B 是桌面/平板优先，移动端只确保不破，不做触摸专属优化）
- **不**改 Electron 集成（CSS 驱动设计，Electron 自动继承）
- **不**做无障碍认证级（WCAG AA 是目标，AAA 不强制）

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| IBM Plex Sans SC 中文覆盖不全 | 少量生僻字 | `font-family: 'IBM Plex Sans', 'IBM Plex Sans SC', 'PingFang SC', sans-serif` 兜底 |
| 字体加载导致 FOUT | 首屏闪烁 | `<link rel="preload">` 预加载 woff2，`font-display: swap` |
| M3 Spring 偏快/弹 | 头晕用户 | 已有 M2 + reduced-motion 自动降级 |
| Lime 在浅色主题下对比度不足 | 文本可读性 | B-light 用更暗版本 `#5C9E00`，符合 WCAG AA |
| Naive UI 残留导致风格混搭 | P7 之前 | P1 完成 molecules 后立即替换 agent 三页的 Naive 用法 |
| 大型 SFC 拆分时丢失业务逻辑 | 功能回归 | 每阶段先重构 organism 时保留旧 SFC 作 reference，dev library 验证完才删旧 |
| 13 页全覆盖工作量大 | 周期长 | 8 阶段独立可发布，过渡期混搭可接受（产品未上线） |

---

## 9. 验收标准

每阶段以下条件全部满足才算完成：

1. **dev library** 里相关组件全部状态可见（hover/active/disabled/loading/error/empty）
2. 该阶段涉及页面在 **3 种点缀色 × 2 种主题 × 2 种动效**（共 12 组合）下视觉无明显错位
3. 页面文件 ≤ 100 行（pages 层），organism ≤ 400 行
4. 无 console 警告 / 错误
5. `prefers-reduced-motion: reduce` 下所有动效降为瞬时
6. WCAG AA 对比度通过（自动测试或人工抽样）

最终 P8 完成时：
- 旧 `components/common/` `components/layout/` `pages/files/components/` `pages/skills/Skills.vue` `web/src/layouts/` 全部不存在
- 全站 `grep -r "Manrope\|cubic-bezier(0.4, 0, 0.2, 1)\|translateY(-1px)" web/src/` 零命中
- 全站 `:root { ... }` 颜色/字体定义仅出现在 `web/src/styles/tokens/*.css` 与 `web/src/styles/theme.css` 中

---

## 10. 实施计划入口

本设计文档定稿并经用户审阅后，下一步使用 `superpowers:writing-plans` skill 产出详细实施计划，包含：

- 每阶段的任务分解（按 organism / atom 粒度）
- 每个文件的接口契约（props / events / slots）
- 每个 token 的精确取值
- 测试策略（dev library 视觉回归 + 关键交互手测清单）
- 提交策略（每阶段 1-N 个 commit，PR 划分建议）

实施计划完成后，进入 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development` 进行落地。
