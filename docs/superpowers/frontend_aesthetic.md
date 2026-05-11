---
name: Frontend aesthetic direction
description: FileFlash web frontend visual identity — Industrial Dashboard direction, single identity (no multi-theme); chosen 2026-05-10 to replace the AI-generated default look
type: project
originSessionId: 19f3a1e2-b428-4855-87de-e6c9ca410525
---
FileFlash 前端的视觉身份方向是 **"Industrial Dashboard"（工业仪表盘）**，**单一身份**（不做 A/B/C/D 多主题切换）。

**核心特征**：
- 深色为主体 + 一个明亮点缀色
- **主点缀色：Electric Lime `#B6FF3D` (rgb 182, 255, 61)**
- **可切换子主题（用户偏好）**：Amber `#FFB400` / Oxide Red `#FF4F2C`。这三色不动字体、几何、密度，仅 `--ac` / `--ac-rgb` / `--ac-fg` 之类的 CSS 变量切换。视为同一 B 身份内的"个性化"，不是独立 theme。
- **字体**：
  - 主 Sans：**IBM Plex Sans** (拉丁) + **IBM Plex Sans SC** (中文)，权重 400/500/600/700
  - 等宽：**JetBrains Mono**，用于所有数据列（尺寸、时间戳、计数、百分比、文件名 mono 模式）
  - 二者同属"工程文档/代码"字体家族，混排无缝
  - 用 `font-feature-settings: "tnum"` 确保数字等宽对齐
- 直角硬边 / 极小圆角，强烈的网格分隔线
- 小写大字距标签（uppercase tracking 0.18em）作为分区标记
- **默认密度：舒适**（行高 32px / 字号 13.5px / 表单间距 16px），与 Spring & Bloom 动效协调
- 对标参考：Linear 暗色、Datadog、Vercel CLI、Bloomberg Terminal 现代化版本
- 排除方向：A 编辑部式衬线、C 苹果式柔和彩色、D 暖橙现代

**配套范围**：包含明/暗变体（B-dark + B-light），但都属同一身份语言；不做"切换到完全不同设计风格"的主题。

**动效语言（Motion）**：
- 默认 **Spring & Bloom**：200-280ms + `cubic-bezier(0.34, 1.56, 0.64, 1)` 微反弹；按钮 hover 发光、选中行位移、视图切换缩放呼吸。最有"性格"，但偏离纯工程基调。
- 可切换 **Tight Ease-Out**：120-180ms + `cubic-bezier(0.2, 0.8, 0.2, 1)`；按钮按下缩到 96%、选中行 2px 绿条左侧滑出。Linear/Cron 风。
- `prefers-reduced-motion: reduce` 时自动降级为瞬时（无 transition）。
- 全部用 CSS 变量化：`--mo-duration-fast/mid/slow`、`--mo-easing`、`--mo-press-scale`。两套预设通过切换变量值实现。

**Why**：用户认为去年 AI 写的 UI（Manrope 字体 + 通用 SaaS 蓝 + 玻璃/blur + transform-translateY hover lift）"无人类审美质感、字体过轻、组件互相牵动、切页像刷新"。选择 B 是为了让产品有明确"工程感的声音"，而非可配置的中间值。多主题被否决因为会稀释这个声音。

**How to apply**：
- 任何关于 FileFlash 前端字体、配色、组件造型、动效的决策，都以"工业仪表盘"为锚点。不要默认推荐 Inter/Manrope、不要默认推荐圆角 pill 按钮、不要默认推荐 cubic-bezier(0.4,0,0.2,1) Material 曲线。
- 决策候选时，优先选"密度高、信息明确、几何硬朗、动效短促"的方案。
- 若用户后续推翻或扩展（比如"加一个柔和模式"），更新本条记忆而非新建。
