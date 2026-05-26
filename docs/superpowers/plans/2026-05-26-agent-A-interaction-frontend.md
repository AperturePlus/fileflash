# Agent 子项目 A（交互/反馈层）— 前端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把前端从"单向 SSE + 整个 job 取消"升级为"双向交互 + step 级 pause/resume/skip/approve + agent 中途提问 + 实时进度/思考/工具增量输出"，匹配 A-backend 已落地的事件类型与 `POST /agent/jobs/{id}/messages` 上行通道。

**Architecture:** 在 `types/agent.d.ts` 扩展事件字面量与上行消息类型；`api/agent.ts` 用 `sendAgentMessage` + 6 个 control helper 取代 `cancelAgentJob`；`useAgentSession.ts` 引入 `waiting_for_user`/`paused` 状态、ask 缓存、`pauseTurn/resumeTurn/replyToAsk/...` 方法，cancel 改走 `control.cancel`；新增 `AskPrompt.vue` + `ControlBar.vue` 两个原子组件，TurnEntry 内嵌；TaskInputDock 在 waiting_for_user/paused 时切换主输入框 disable。

**Tech Stack:** Vue 3 + TypeScript + Vitest + bun（**不用 npm**）+ 既有 i18n 体系 + 既有 atomic 设计语言（Industrial Dashboard，参见 `frontend_aesthetic.md`）。

**Spec:** `docs/superpowers/specs/2026-05-26-agent-improvements-design.md` 子项目 A 部分（前端章节 A.7、A.8、A.10）

**前置条件:** A-backend plan 已落地（commit 包含 `AgentInboxMessage` 模型、`POST /agent/jobs/{id}/messages`、SSE event_bus 推送、新 14 种 `AgentJobEventType`）

---

## File Structure

**新建**

- `web/src/components/organisms/agent/AskPrompt.vue` — 渲染单条 agent.ask 的输入气泡（选择型 / 自由文本，含 timeout 倒计时）
- `web/src/components/organisms/agent/ControlBar.vue` — 渲染单 turn 的 pause/resume/skip/cancel 按钮组
- `web/src/composables/useAskTimeout.ts` — ask 倒计时小工具（含 i18n 友好的 mm:ss 格式化）

**修改**

- `web/src/types/agent.d.ts` — 扩展 `AgentJobEventType`；新增 `MsgStatus`-相关、`AgentInboxMessageKind` / `AgentInboxMessageRequest` / `AgentInboxMessageResponse`、`AgentAskPayload` / `AgentProgressPayload` / `AgentThinkingPayload` / `AgentToolPartialPayload`
- `web/src/api/agent.ts` — 删除 `cancelAgentJob`；新增 `sendAgentMessage` 与 6 个 helper：`sendAgentReply` / `pauseAgentJob` / `resumeAgentJob` / `approveAgentStep` / `denyAgentStep` / `skipAgentStep` / `cancelAgentTurn`
- `web/src/composables/useAgentSession.ts` — `MsgStatus` 加 `waiting_for_user` / `paused`；`ChatMessage` 加 `pendingAsk`、`pauseRequestedAt`、`progress`、`thinking`、`partials`；`applyAgentEvent` 覆盖新 6 种事件；`cancel(msg)` 改走 `control.cancel`；新增方法
- `web/src/composables/useAgentSession.spec.ts` — 覆盖新事件与新方法
- `web/src/components/organisms/agent/TurnEntry.vue` — 内嵌 `AskPrompt` / `ControlBar`；新增 progress 条与 thinking 折叠区；扩展 `activityEvents` 过滤规则
- `web/src/components/organisms/agent/TaskInputDock.vue` — `disabled` prop 范围扩大（waiting_for_user / paused 时锁主输入）
- `web/src/i18n/messages.ts` — 13 条新 key（ask/progress/thinking/控制按钮/状态文案）+ 中英文翻译

**测试**

- `web/src/composables/useAgentSession.spec.ts` — 既有文件追加
- (可选) `web/src/components/organisms/agent/AskPrompt.spec.ts` — 新（@vue/test-utils 风格如项目已用，否则跳过）

---

## Sequencing

```
Task 1 (types) ──► Task 2 (api helpers) ──► Task 3 (i18n keys)
                                                │
                          ┌─────────────────────┴──────────────────────┐
                          ▼                                            ▼
        Task 4 (useAgentSession state + cancel rewire)     Task 5 (useAskTimeout)
                          │                                            │
                          ▼                                            │
        Task 6 (useAgentSession ask handlers + control methods)        │
                          │                                            │
                          ▼                                            ▼
                          ▼─────────────► Task 7 (AskPrompt.vue) ◄─────┘
                          │
                          ▼
                  Task 8 (ControlBar.vue)
                          │
                          ▼
                  Task 9 (TurnEntry.vue 集成)
                          │
                          ▼
                  Task 10 (TaskInputDock.vue 锁定)
                          │
                          ▼
                  Task 11 (端到端 spec：ask → reply → resume → cancel)
                          │
                          ▼
                  Task 12 (手测脚本 + dev server 真跑一次)
```

---

## Task 1: 扩展 types/agent.d.ts

**Files:**

- Modify: `web/src/types/agent.d.ts`

- [ ] **Step 1: 扩展 `AgentJobEventType` 字面量与新增上行消息 / 事件 payload 类型**

把 `AgentJobEventType` 替换为：

```ts
export type AgentJobEventType =
  | 'job.queued'
  | 'job.running'
  | 'plan.ready'
  | 'tool.started'
  | 'tool.succeeded'
  | 'tool.failed'
  | 'tool.partial'
  | 'agent.thinking'
  | 'agent.progress'
  | 'agent.ask'
  | 'agent.paused'
  | 'agent.resumed'
  | 'job.succeeded'
  | 'job.failed'
  | 'job.canceled';
```

在文件末尾追加：

```ts
// ----------------- Inbox (upstream channel) -----------------

export type AgentInboxMessageKind =
  | 'reply'
  | 'control.pause'
  | 'control.resume'
  | 'control.approve'
  | 'control.deny'
  | 'control.skip'
  | 'control.cancel';

export interface AgentInboxMessageRequest {
  kind: AgentInboxMessageKind;
  replyTo?: string;            // ask 的 inboxMessageId（string-encoded）
  value?: unknown;             // reply 时为用户回答
  metadata?: Record<string, unknown>;
}

export interface AgentInboxMessageResponse {
  inboxMessageId: string;
  kind: AgentInboxMessageKind;
  acceptedAt: string;
}

// ----------------- New event payloads -----------------

export interface AgentAskPayload {
  messageId: string;
  prompt: string;
  schema: Record<string, unknown>;     // 自由形式；例如 {"choice":["A","B"]}
  timeoutSec: number;
}

export interface AgentProgressPayload {
  step: number;
  total: number;
  message?: string;
  percent?: number;
}

export interface AgentThinkingPayload {
  text: string;
}

export interface AgentToolPartialPayload {
  step: number;
  tool: string;
  chunk: unknown;
}
```

- [ ] **Step 2: 删除 `CancelAgentResponse` 接口**

后端已删除 `POST /agent/cancel`；前端 type 也清理。同步 `web/src/api/agent.ts` 的 import（Task 2 处理）。

- [ ] **Step 3: typecheck**

Run: `cd web && bun run typecheck`
Expected: 仅出现"`CancelAgentResponse` 仍被 import in api/agent.ts"的错误——Task 2 修复。

- [ ] **Step 4: Commit**

```bash
git add web/src/types/agent.d.ts
git commit -m "feat(agent): extend frontend types for inbox + new event payloads"
```

---

## Task 2: api/agent.ts 引入 sendAgentMessage + 6 个 helper

**Files:**

- Modify: `web/src/api/agent.ts`

- [ ] **Step 1: 删除 `cancelAgentJob` 与对应 import**

```ts
// 删除：
import type { ... CancelAgentResponse ... } from '../types/agent';
export const cancelAgentJob = (jobId: string) => { ... };
```

- [ ] **Step 2: 新增 `sendAgentMessage` 与 6 个 helper**

在 `streamAgentJobEvents` 之上插入：

```ts
import type {
  AgentBackgroundJob,
  AgentInboxMessageRequest,
  AgentInboxMessageResponse,
  AgentJobEvent,
  ExecuteAgentRequest,
  ExecuteAgentResponse,
  PlanAgentRequest,
  PlanAgentResponse,
} from '../types/agent';

// ----------------- inbox upstream -----------------

export const sendAgentMessage = (
  jobId: string,
  body: AgentInboxMessageRequest,
) => {
  return http.post<AgentInboxMessageResponse>(
    `/agent/jobs/${encodeURIComponent(jobId)}/messages`,
    body,
  );
};

export const sendAgentReply = (
  jobId: string,
  replyTo: string,
  value: unknown,
) => sendAgentMessage(jobId, { kind: 'reply', replyTo, value });

export const pauseAgentJob = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.pause' });

export const resumeAgentJob = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.resume' });

export const approveAgentStep = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.approve' });

export const denyAgentStep = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.deny' });

export const skipAgentStep = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.skip' });

export const cancelAgentTurn = (jobId: string) =>
  sendAgentMessage(jobId, { kind: 'control.cancel' });
```

> 注：`cancelAgentTurn` 命名故意区别于历史的 `cancelAgentJob`，提示这是"通过 inbox 取消当前 turn"。所有引用 `cancelAgentJob` 的地方在 Task 4 改成 `cancelAgentTurn`。

- [ ] **Step 3: 全仓搜索旧 import**

Run: `grep -rn "cancelAgentJob\|CancelAgentResponse" web/src/`
Expected: 仅 `web/src/composables/useAgentSession.ts` 几处需要 Task 4 处理。

- [ ] **Step 4: typecheck**

Run: `cd web && bun run typecheck`
Expected: 仅剩 useAgentSession.ts 的 import 错误（Task 4 修）。

- [ ] **Step 5: Commit**

```bash
git add web/src/api/agent.ts
git commit -m "feat(agent): add sendAgentMessage + 6 control helpers, drop cancelAgentJob"
```

---

## Task 3: 新增 i18n key（中英文）

**Files:**

- Modify: `web/src/i18n/messages.ts`

- [ ] **Step 1: 在 `LocaleKey` union（约 line 480-580）的 agent.v2 区块插入新 key**

按字母序插在 `agent.v2.turn.cancel` 附近：

```ts
  | 'agent.v2.turn.status.waiting_for_user'
  | 'agent.v2.turn.status.paused'
  | 'agent.v2.turn.controls.pause'
  | 'agent.v2.turn.controls.resume'
  | 'agent.v2.turn.controls.skip'
  | 'agent.v2.turn.controls.approve'
  | 'agent.v2.turn.controls.deny'
  | 'agent.v2.turn.ask.placeholder'
  | 'agent.v2.turn.ask.send'
  | 'agent.v2.turn.ask.timeout'
  | 'agent.v2.turn.progress.label'
  | 'agent.v2.turn.thinking.label'
  | 'agent.v2.turn.thinking.toggle'
```

- [ ] **Step 2: 在 zh-CN 翻译 map 中添加（约 line 1066-1160）**

```ts
    'agent.v2.turn.status.waiting_for_user': '等待你回复',
    'agent.v2.turn.status.paused': '已暂停',
    'agent.v2.turn.controls.pause': '暂停',
    'agent.v2.turn.controls.resume': '继续',
    'agent.v2.turn.controls.skip': '跳过此步',
    'agent.v2.turn.controls.approve': '批准',
    'agent.v2.turn.controls.deny': '拒绝',
    'agent.v2.turn.ask.placeholder': '输入回答…',
    'agent.v2.turn.ask.send': '发送',
    'agent.v2.turn.ask.timeout': '剩余 {value}',
    'agent.v2.turn.progress.label': '进度',
    'agent.v2.turn.thinking.label': '思考过程',
    'agent.v2.turn.thinking.toggle': '展开 / 收起',
```

- [ ] **Step 3: 在 en 翻译 map 中添加（约 line 1641-1730）**

```ts
    'agent.v2.turn.status.waiting_for_user': 'WAITING FOR YOU',
    'agent.v2.turn.status.paused': 'PAUSED',
    'agent.v2.turn.controls.pause': 'Pause',
    'agent.v2.turn.controls.resume': 'Resume',
    'agent.v2.turn.controls.skip': 'Skip step',
    'agent.v2.turn.controls.approve': 'Approve',
    'agent.v2.turn.controls.deny': 'Deny',
    'agent.v2.turn.ask.placeholder': 'Type your answer…',
    'agent.v2.turn.ask.send': 'Send',
    'agent.v2.turn.ask.timeout': '{value} left',
    'agent.v2.turn.progress.label': 'PROGRESS',
    'agent.v2.turn.thinking.label': 'THINKING',
    'agent.v2.turn.thinking.toggle': 'Expand / Collapse',
```

- [ ] **Step 4: typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS（LocaleKey union 与 map 一致）

- [ ] **Step 5: Commit**

```bash
git add web/src/i18n/messages.ts
git commit -m "feat(agent): add i18n keys for ask/pause/progress/controls"
```

---

## Task 4: useAgentSession.ts — 扩展状态 + 改 cancel 走 inbox

**Files:**

- Modify: `web/src/composables/useAgentSession.ts`

- [ ] **Step 1: 扩展 `MsgStatus` 与 `ChatMessage`**

把现有 `MsgStatus` 类型改为：

```ts
export type MsgStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'canceled'
  | 'waiting_for_user'
  | 'paused';
```

把 `ChatMessage` 接口扩展为：

```ts
export interface PendingAsk {
  messageId: string;
  prompt: string;
  schema: Record<string, unknown>;
  timeoutSec: number;
  askedAt: string;
}

export interface ToolPartial {
  step: number;
  tool: string;
  chunks: unknown[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  status: MsgStatus;
  planJobId?: string;
  planHash?: string;
  planResult?: AgentPlanResult;
  executeJobId?: string;
  executeResult?: AgentExecutionResult;
  events: AgentJobEvent[];
  errorMessage?: string;
  timestamp: string;
  // —— 新增（A 前端）——
  pendingAsk?: PendingAsk;
  pauseRequestedAt?: string;
  progress?: { step: number; total: number; message?: string; percent?: number };
  thinking?: string;                     // 累积的 thinking 文本
  partials?: Record<number, ToolPartial>;
}
```

- [ ] **Step 2: 调整 `applyAgentEvent` 覆盖新事件**

替换现有 `applyAgentEvent` 为：

```ts
const applyAgentEvent = (msg: ChatMessage, event: AgentJobEvent, kind: 'plan' | 'execute') => {
  appendAgentEvent(msg, event);

  // 终态 / 既有事件
  if (event.type === 'job.queued') {
    msg.status = 'pending';
  } else if (event.type === 'job.running' || event.type === 'tool.started') {
    if (msg.status !== 'waiting_for_user' && msg.status !== 'paused') {
      msg.status = 'running';
    }
  } else if (event.type === 'job.failed' || event.type === 'tool.failed') {
    msg.status = 'failed';
    const errorMessage = event.data?.errorMessage;
    msg.errorMessage = typeof errorMessage === 'string' ? errorMessage : event.message;
  } else if (event.type === 'job.canceled') {
    msg.status = 'canceled';
  } else if (event.type === 'job.succeeded') {
    msg.status = 'succeeded';
    msg.pendingAsk = undefined;
    msg.pauseRequestedAt = undefined;
  }

  // 新事件
  if (event.type === 'agent.ask') {
    const payload = event.data as AgentAskPayload;
    msg.pendingAsk = {
      messageId: payload.messageId,
      prompt: payload.prompt,
      schema: payload.schema,
      timeoutSec: payload.timeoutSec,
      askedAt: event.timestamp,
    };
    msg.status = 'waiting_for_user';
  } else if (event.type === 'agent.paused') {
    msg.status = 'paused';
    msg.pauseRequestedAt = event.timestamp;
  } else if (event.type === 'agent.resumed') {
    msg.status = 'running';
    msg.pauseRequestedAt = undefined;
  } else if (event.type === 'agent.progress') {
    const payload = event.data as AgentProgressPayload;
    msg.progress = {
      step: payload.step,
      total: payload.total,
      message: payload.message,
      percent: payload.percent,
    };
  } else if (event.type === 'agent.thinking') {
    const payload = event.data as AgentThinkingPayload;
    msg.thinking = (msg.thinking || '') + (payload.text || '');
  } else if (event.type === 'tool.partial') {
    const payload = event.data as AgentToolPartialPayload;
    msg.partials = msg.partials || {};
    const slot = msg.partials[payload.step] || { step: payload.step, tool: payload.tool, chunks: [] };
    slot.chunks = [...slot.chunks, payload.chunk];
    msg.partials[payload.step] = slot;
  }

  const result = event.data?.result;
  if (event.type === 'plan.ready' && result) {
    msg.planResult = result as AgentPlanResult;
    msg.planHash = msg.planResult.planHash;
  }
  if (event.type === 'job.succeeded' && result) {
    if (kind === 'plan') {
      msg.planResult = result as AgentPlanResult;
      msg.planHash = msg.planResult.planHash;
    } else {
      msg.executeResult = result as AgentExecutionResult;
    }
  }
};
```

在 imports 顶部追加：

```ts
import type {
  AgentAskPayload,
  AgentExecutionPolicy,
  AgentExecutionResult,
  AgentJobEvent,
  AgentPlanResult,
  AgentProgressPayload,
  AgentReasoningEffort,
  AgentThinkingPayload,
  AgentToolPartialPayload,
  PlanAgentRequest,
} from '../types/agent';
```

- [ ] **Step 3: 把 `cancel(msg)` 改走 `control.cancel`**

替换 `cancel` 函数 + 删除顶部 `cancelAgentJob` import：

```ts
import {
  cancelAgentTurn,
  executeAgentPlan,
  getAgentJob,
  planAgentTask,
  streamAgentJobEvents,
} from '../api/agent';

// ...

async function cancel(msg: ChatMessage): Promise<void> {
  markTurnCanceled(msg);
  msg.status = 'canceled';
  msg.pendingAsk = undefined;
  msg.pauseRequestedAt = undefined;
  stopPolling(`${msg.id}:plan`);
  stopPolling(`${msg.id}:execute`);
  stopStream(`${msg.id}:plan`);
  stopStream(`${msg.id}:execute`);
  const jobId = msg.executeJobId || msg.planJobId;
  if (!jobId) return;
  try {
    await cancelAgentTurn(jobId);
  } catch (error) {
    msg.errorMessage = extractErrorMessage(error, 'Cancel failed.');
  }
}
```

同时把 `sendMessage` / `runExecute` 内的旧 `cancelAgentJob(res.jobId)` 替换为 `cancelAgentTurn(res.jobId)`：

```ts
// sendMessage 内：
if (isTurnCanceled(reactiveAgent) || reactiveAgent.status === 'canceled') {
  try {
    await cancelAgentTurn(res.jobId);
  } catch { /* ignore */ }
  return;
}

// runExecute 内：
if (!ensureTurnNotCanceled(msg)) {
  try {
    await cancelAgentTurn(res.jobId);
  } catch { /* ignore */ }
  return;
}
```

- [ ] **Step 4: 全仓 grep**

Run: `grep -rn "cancelAgentJob" web/src/`
Expected: 无匹配。

- [ ] **Step 5: typecheck + 跑既有测试**

Run: `cd web && bun run typecheck && bun run test useAgentSession`
Expected: typecheck PASS；既有 spec 大多 PASS。如果某些用例断言"取消时调用 cancelAgentJob"，改断言为 `cancelAgentTurn`（即 `sendAgentMessage(..., {kind:'control.cancel'})`）。

- [ ] **Step 6: Commit**

```bash
git add web/src/composables/useAgentSession.ts
git commit -m "feat(agent): extend session state for ask/pause/progress, rewire cancel via inbox"
```

---

## Task 5: 新建 `useAskTimeout.ts`

**Files:**

- Create: `web/src/composables/useAskTimeout.ts`
- Create: `web/src/composables/useAskTimeout.spec.ts`

- [ ] **Step 1: 写测试**

```ts
// web/src/composables/useAskTimeout.spec.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ref } from 'vue';
import { useAskTimeout } from './useAskTimeout';

describe('useAskTimeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts down from askedAt + timeoutSec', () => {
    const askedAt = ref('2026-05-26T12:00:00.000Z');
    const timeoutSec = ref(120);
    vi.setSystemTime(new Date('2026-05-26T12:00:30.000Z'));
    const { remainingSec, formatted, expired } = useAskTimeout(askedAt, timeoutSec);
    expect(remainingSec.value).toBe(90);
    expect(formatted.value).toBe('01:30');
    expect(expired.value).toBe(false);

    vi.setSystemTime(new Date('2026-05-26T12:02:01.000Z'));
    vi.advanceTimersByTime(1000);
    expect(expired.value).toBe(true);
    expect(remainingSec.value).toBe(0);
    expect(formatted.value).toBe('00:00');
  });

  it('returns expired immediately when askedAt is missing', () => {
    const askedAt = ref<string | undefined>(undefined);
    const timeoutSec = ref(60);
    const { expired, formatted } = useAskTimeout(askedAt, timeoutSec);
    expect(expired.value).toBe(true);
    expect(formatted.value).toBe('00:00');
  });
});
```

- [ ] **Step 2: 运行测试，确认 fail**

Run: `cd web && bun run test useAskTimeout`
Expected: FAIL — module missing.

- [ ] **Step 3: 实现**

```ts
// web/src/composables/useAskTimeout.ts
import { computed, onScopeDispose, ref, watchEffect, type Ref } from 'vue';

export function useAskTimeout(
  askedAt: Ref<string | undefined | null>,
  timeoutSec: Ref<number>,
) {
  const now = ref<number>(Date.now());
  let timer: ReturnType<typeof setInterval> | null = null;

  watchEffect(() => {
    if (timer) clearInterval(timer);
    if (!askedAt.value || timeoutSec.value <= 0) return;
    timer = setInterval(() => {
      now.value = Date.now();
    }, 1000);
  });

  onScopeDispose(() => {
    if (timer) clearInterval(timer);
  });

  const deadline = computed(() => {
    if (!askedAt.value) return null;
    const base = Date.parse(askedAt.value);
    if (Number.isNaN(base)) return null;
    return base + timeoutSec.value * 1000;
  });

  const remainingSec = computed(() => {
    if (deadline.value === null) return 0;
    return Math.max(0, Math.ceil((deadline.value - now.value) / 1000));
  });

  const expired = computed(() => deadline.value === null || remainingSec.value <= 0);

  const formatted = computed(() => {
    const total = remainingSec.value;
    const mm = String(Math.floor(total / 60)).padStart(2, '0');
    const ss = String(total % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  });

  return { remainingSec, formatted, expired };
}
```

- [ ] **Step 4: 运行测试**

Run: `cd web && bun run test useAskTimeout`
Expected: PASS（2 个用例）

- [ ] **Step 5: Commit**

```bash
git add web/src/composables/useAskTimeout.ts web/src/composables/useAskTimeout.spec.ts
git commit -m "feat(agent): add useAskTimeout countdown composable"
```

---

## Task 6: useAgentSession.ts — ask reply 与控制方法

**Files:**

- Modify: `web/src/composables/useAgentSession.ts`
- Modify: `web/src/composables/useAgentSession.spec.ts`

- [ ] **Step 1: 更新 spec 顶部的 `vi.mock` 工厂，注册新 helper**

`useAgentSession.spec.ts` 顶部已有：

```ts
vi.mock('../api/agent', () => ({
  planAgentTask: vi.fn(),
  executeAgentPlan: vi.fn(),
  cancelAgentJob: vi.fn(),
  getAgentJob: vi.fn(),
  streamAgentJobEvents: vi.fn(),
}));
```

替换为：

```ts
vi.mock('../api/agent', () => ({
  planAgentTask: vi.fn(),
  executeAgentPlan: vi.fn(),
  cancelAgentTurn: vi.fn(),         // 替代旧 cancelAgentJob
  getAgentJob: vi.fn(),
  streamAgentJobEvents: vi.fn(),
  sendAgentMessage: vi.fn(),
  sendAgentReply: vi.fn(),
  pauseAgentJob: vi.fn(),
  resumeAgentJob: vi.fn(),
  approveAgentStep: vi.fn(),
  denyAgentStep: vi.fn(),
  skipAgentStep: vi.fn(),
}));
```

把既有用到 `agentApi.cancelAgentJob` 的断言全部改为 `agentApi.cancelAgentTurn`（Task 4 已经改了源；spec 这里同步）。

Run: `grep -n "cancelAgentJob" web/src/composables/useAgentSession.spec.ts`
Expected: 找到的每一处都要改成 `cancelAgentTurn`。

- [ ] **Step 2: 在 spec 末尾追加 inbox-controls 用例**

```ts
import * as agentApi from '../api/agent';

describe('useAgentSession — inbox controls', () => {
  beforeEach(() => {
    vi.mocked(agentApi.sendAgentReply).mockResolvedValue({
      inboxMessageId: '42', kind: 'reply', acceptedAt: '2026-05-26T00:00:00Z',
    });
    vi.mocked(agentApi.pauseAgentJob).mockResolvedValue({
      inboxMessageId: '50', kind: 'control.pause', acceptedAt: '2026-05-26T00:00:00Z',
    });
  });

  it('replyToAsk sends reply to backend and clears pendingAsk', async () => {
    const { default: useAgentSession } = await loadComposable();
    const { createSession, replyToAsk } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-1',
      role: 'agent',
      content: '',
      status: 'waiting_for_user',
      events: [],
      timestamp: new Date().toISOString(),
      executeJobId: '77',
      pendingAsk: {
        messageId: '101',
        prompt: 'choose',
        schema: { choice: ['A', 'B'] },
        timeoutSec: 60,
        askedAt: new Date().toISOString(),
      },
    };
    session.messages.push(msg);

    await replyToAsk(msg, 'A');

    expect(agentApi.sendAgentReply).toHaveBeenCalledWith('77', '101', 'A');
    expect(msg.pendingAsk).toBeUndefined();
    expect(msg.status).toBe('running');
  });

  it('pauseTurn sends control.pause and records pauseRequestedAt', async () => {
    const { default: useAgentSession } = await loadComposable();
    const { createSession, pauseTurn } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-2', role: 'agent', content: '', status: 'running',
      events: [], timestamp: new Date().toISOString(), executeJobId: '88',
    };
    session.messages.push(msg);

    await pauseTurn(msg);
    expect(agentApi.pauseAgentJob).toHaveBeenCalledWith('88');
    // 本地不立即翻 paused，等 agent.paused 事件
    expect(msg.pauseRequestedAt).toBeTruthy();
  });
});
```

> 注：上述用例用项目既有 `vi.mock + vi.mocked + loadComposable()` 风格（参见同文件其它用例），不引入 `vi.spyOn(await import(...))` 写法。`ChatMessage` 类型可能需要从 `'../composables/useAgentSession'` 导入（既有用例如何引用就跟随）。

- [ ] **Step 2: 实现 5 个新方法**

在 `useAgentSession.ts` 内（`cancel` 函数附近）新增：

```ts
import {
  approveAgentStep,
  cancelAgentTurn,
  denyAgentStep,
  executeAgentPlan,
  getAgentJob,
  pauseAgentJob,
  planAgentTask,
  resumeAgentJob,
  sendAgentReply,
  skipAgentStep,
  streamAgentJobEvents,
} from '../api/agent';

// ...

const activeJobId = (msg: ChatMessage): string | undefined =>
  msg.executeJobId || msg.planJobId;

async function replyToAsk(msg: ChatMessage, value: unknown): Promise<void> {
  const jobId = activeJobId(msg);
  if (!jobId || !msg.pendingAsk) return;
  const replyTo = msg.pendingAsk.messageId;
  msg.pendingAsk = undefined;
  msg.status = 'running';
  try {
    await sendAgentReply(jobId, replyTo, value);
  } catch (error) {
    msg.status = 'waiting_for_user';
    msg.pendingAsk = {
      messageId: replyTo,
      prompt: msg.pendingAsk?.prompt || '',
      schema: msg.pendingAsk?.schema || {},
      timeoutSec: msg.pendingAsk?.timeoutSec || 0,
      askedAt: msg.pendingAsk?.askedAt || new Date().toISOString(),
    };
    msg.errorMessage = extractErrorMessage(error, 'Reply failed.');
  }
}

async function pauseTurn(msg: ChatMessage): Promise<void> {
  const jobId = activeJobId(msg);
  if (!jobId) return;
  msg.pauseRequestedAt = new Date().toISOString();
  try {
    await pauseAgentJob(jobId);
  } catch (error) {
    msg.pauseRequestedAt = undefined;
    msg.errorMessage = extractErrorMessage(error, 'Pause failed.');
  }
}

async function resumeTurn(msg: ChatMessage): Promise<void> {
  const jobId = activeJobId(msg);
  if (!jobId) return;
  try {
    await resumeAgentJob(jobId);
  } catch (error) {
    msg.errorMessage = extractErrorMessage(error, 'Resume failed.');
  }
}

async function approveStep(msg: ChatMessage): Promise<void> {
  const jobId = activeJobId(msg);
  if (!jobId) return;
  try {
    await approveAgentStep(jobId);
  } catch (error) {
    msg.errorMessage = extractErrorMessage(error, 'Approve failed.');
  }
}

async function denyStep(msg: ChatMessage): Promise<void> {
  const jobId = activeJobId(msg);
  if (!jobId) return;
  try {
    await denyAgentStep(jobId);
  } catch (error) {
    msg.errorMessage = extractErrorMessage(error, 'Deny failed.');
  }
}

async function skipStep(msg: ChatMessage): Promise<void> {
  const jobId = activeJobId(msg);
  if (!jobId) return;
  try {
    await skipAgentStep(jobId);
  } catch (error) {
    msg.errorMessage = extractErrorMessage(error, 'Skip failed.');
  }
}
```

把 6 个方法加到 return 对象末尾：

```ts
  return {
    sessions: s.sessions,
    activeSessionId: s.activeSessionId,
    activeSession,
    activeTurns,
    policy: s.policy,
    reasoningEffort: s.reasoningEffort,
    taskInput: s.taskInput,
    isSending: s.isSending,
    createSession,
    switchSession,
    deleteSession,
    resetActiveSession,
    sendMessage,
    runExecute,
    cancel,
    // —— 新增 ——
    replyToAsk,
    pauseTurn,
    resumeTurn,
    approveStep,
    denyStep,
    skipStep,
  };
```

- [ ] **Step 3: 运行测试**

Run: `cd web && bun run test useAgentSession`
Expected: PASS（含新追加的两个用例）

- [ ] **Step 4: Commit**

```bash
git add web/src/composables/useAgentSession.ts web/src/composables/useAgentSession.spec.ts
git commit -m "feat(agent): add replyToAsk + pause/resume/skip/approve/deny composables"
```

---

## Task 7: `AskPrompt.vue`

**Files:**

- Create: `web/src/components/organisms/agent/AskPrompt.vue`

- [ ] **Step 1: 实现组件**

```vue
<!-- web/src/components/organisms/agent/AskPrompt.vue -->
<script setup lang="ts">
import { computed, ref, toRefs } from 'vue';
import Button from '../../molecules/Button.vue';
import { useLocaleStore } from '../../../store/locale';
import { useAskTimeout } from '../../../composables/useAskTimeout';
import type { PendingAsk } from '../../../composables/useAgentSession';

const props = defineProps<{
  ask: PendingAsk;
  disabled?: boolean;
}>();

const emit = defineEmits<{ reply: [value: unknown] }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const askedAt = computed(() => props.ask.askedAt);
const timeoutSec = computed(() => props.ask.timeoutSec);
const { formatted, expired } = useAskTimeout(askedAt, timeoutSec);

const text = ref('');

const choices = computed<string[]>(() => {
  const c = props.ask.schema?.choice;
  return Array.isArray(c) ? (c as unknown[]).map((v) => String(v)) : [];
});

const submit = () => {
  if (props.disabled || expired.value) return;
  if (text.value.trim()) {
    emit('reply', text.value.trim());
    text.value = '';
  }
};

const onKey = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submit();
  }
};
</script>

<template>
  <section class="ff-askp" :class="{ 'is-expired': expired }">
    <header class="ff-askp__head">
      <span class="ff-askp__label">{{ t('agent.v2.turn.status.waiting_for_user') }}</span>
      <span class="ff-askp__timer">{{ t('agent.v2.turn.ask.timeout', { value: formatted }) }}</span>
    </header>
    <p class="ff-askp__prompt">{{ ask.prompt }}</p>

    <div v-if="choices.length" class="ff-askp__choices">
      <Button
        v-for="choice in choices"
        :key="choice"
        variant="secondary"
        size="sm"
        :disabled="disabled || expired"
        @click="emit('reply', choice)"
      >{{ choice }}</Button>
    </div>

    <div v-else class="ff-askp__free">
      <textarea
        class="ff-askp__ta"
        :value="text"
        :disabled="disabled || expired"
        :placeholder="t('agent.v2.turn.ask.placeholder')"
        rows="2"
        @input="(e) => (text = (e.target as HTMLTextAreaElement).value)"
        @keydown="onKey"
      />
      <Button
        variant="primary"
        size="sm"
        :disabled="!text.trim() || disabled || expired"
        @click="submit"
      >{{ t('agent.v2.turn.ask.send') }}</Button>
    </div>
  </section>
</template>

<style scoped>
.ff-askp {
  display: flex; flex-direction: column; gap: var(--sp-sm);
  padding: var(--sp-md);
  border: 1px solid var(--ac);
  background: var(--surface-base);
}
.ff-askp.is-expired { border-color: var(--text-tertiary); opacity: 0.6; }
.ff-askp__head {
  display: flex; justify-content: space-between; align-items: center;
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
}
.ff-askp__label { color: var(--ac); }
.ff-askp__timer { color: var(--text-tertiary); }
.ff-askp__prompt { margin: 0; color: var(--text-primary); white-space: pre-wrap; }
.ff-askp__choices { display: flex; gap: var(--sp-sm); flex-wrap: wrap; }
.ff-askp__free { display: flex; gap: var(--sp-sm); align-items: flex-end; }
.ff-askp__ta {
  flex: 1; resize: vertical; min-height: 48px;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-raised); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 0;
  font-family: var(--font-sans); font-size: var(--text-body); outline: none;
}
.ff-askp__ta:focus { border-color: var(--ac); }
.ff-askp__ta:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
```

> 设计风格：沿用 Industrial Dashboard（参见 memory `frontend_aesthetic.md`）—— 直角硬边、`var(--ac)` 主色描边、等宽数字倒计时。

- [ ] **Step 2: 确认 PendingAsk 已被 useAgentSession 导出**

```ts
// web/src/composables/useAgentSession.ts —— 末尾 export 区：
export type { PendingAsk };
```

Run: `grep -n "export type.*PendingAsk\|export interface PendingAsk" web/src/composables/useAgentSession.ts`
Expected: 至少一行命中。

- [ ] **Step 3: typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/src/components/organisms/agent/AskPrompt.vue web/src/composables/useAgentSession.ts
git commit -m "feat(agent): AskPrompt component for inline ask UI"
```

---

## Task 8: `ControlBar.vue`

**Files:**

- Create: `web/src/components/organisms/agent/ControlBar.vue`

- [ ] **Step 1: 实现组件**

```vue
<!-- web/src/components/organisms/agent/ControlBar.vue -->
<script setup lang="ts">
import Button from '../../molecules/Button.vue';
import { useLocaleStore } from '../../../store/locale';
import type { MsgStatus } from '../../../composables/useAgentSession';

defineProps<{
  status: MsgStatus;
  hasPlanRiskStep?: boolean;        // plan 中含 high-risk 步骤时显示 approve/deny
}>();

defineEmits<{
  pause: [];
  resume: [];
  skip: [];
  approve: [];
  deny: [];
  cancel: [];
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;
</script>

<template>
  <div class="ff-ctrl">
    <Button
      v-if="status === 'running'"
      variant="ghost"
      size="sm"
      @click.stop="$emit('pause')"
    >{{ t('agent.v2.turn.controls.pause') }}</Button>

    <Button
      v-if="status === 'paused'"
      variant="primary"
      size="sm"
      @click.stop="$emit('resume')"
    >{{ t('agent.v2.turn.controls.resume') }}</Button>

    <Button
      v-if="status === 'running' || status === 'paused'"
      variant="ghost"
      size="sm"
      @click.stop="$emit('skip')"
    >{{ t('agent.v2.turn.controls.skip') }}</Button>

    <template v-if="hasPlanRiskStep && status === 'running'">
      <Button variant="primary" size="sm" @click.stop="$emit('approve')">
        {{ t('agent.v2.turn.controls.approve') }}
      </Button>
      <Button variant="ghost" size="sm" @click.stop="$emit('deny')">
        {{ t('agent.v2.turn.controls.deny') }}
      </Button>
    </template>

    <Button
      v-if="status === 'pending' || status === 'running' || status === 'paused' || status === 'waiting_for_user'"
      variant="ghost"
      size="sm"
      @click.stop="$emit('cancel')"
    >{{ t('agent.v2.turn.cancel') }}</Button>
  </div>
</template>

<style scoped>
.ff-ctrl { display: flex; gap: var(--sp-sm); justify-content: flex-end; flex-wrap: wrap; }
</style>
```

- [ ] **Step 2: typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/src/components/organisms/agent/ControlBar.vue
git commit -m "feat(agent): ControlBar component for pause/resume/skip/approve/deny/cancel"
```

---

## Task 9: 集成到 TurnEntry.vue

**Files:**

- Modify: `web/src/components/organisms/agent/TurnEntry.vue`

- [ ] **Step 1: 扩展 emits 与 props**

```ts
defineEmits<{
  execute: [];
  cancel: [];
  focus: [];
  reply: [value: unknown];
  pause: [];
  resume: [];
  skip: [];
  approve: [];
  deny: [];
}>();
```

`isActive` 计算更新覆盖新状态：

```ts
const isActive = computed(
  () =>
    props.turn.agent.status === 'pending' ||
    props.turn.agent.status === 'running' ||
    props.turn.agent.status === 'paused' ||
    props.turn.agent.status === 'waiting_for_user',
);
```

`activityEvents` 过滤新事件：

```ts
const activityEvents = computed(() =>
  (props.turn.agent.events || [])
    .filter((event) =>
      event.message &&
      !event.type.startsWith('job.succeeded') &&
      event.type !== 'agent.thinking' &&    // thinking 单独折叠区
      event.type !== 'agent.progress' &&    // progress 单独条
      event.type !== 'tool.partial',        // partial 不进活动列表
    )
    .slice(-4),
);

const hasPlanRiskStep = computed(() =>
  Boolean(
    props.turn.agent.planResult?.proposedActions?.some(
      (a) => a.riskLevel === 'high' || a.requiresConfirmation,
    ),
  ),
);

const thinkingExpanded = ref(false);
```

- [ ] **Step 2: 替换 template 中的"按钮行"为 `AskPrompt + ControlBar + 进度条 + thinking`**

把 line 78-138 之间的内容替换为：

```vue
<div v-if="turn.agent.status === 'running' || turn.agent.status === 'paused'" class="ff-te__progress" />

<div v-if="turn.agent.progress" class="ff-te__progress-meta">
  <span class="ff-te__progress-label">{{ t('agent.v2.turn.progress.label') }}</span>
  <span class="ff-te__progress-num">
    <MonoNumber :value="`${turn.agent.progress.step}/${turn.agent.progress.total}`" />
  </span>
  <span v-if="turn.agent.progress.message" class="ff-te__progress-msg">{{ turn.agent.progress.message }}</span>
</div>

<details v-if="turn.agent.thinking" class="ff-te__thinking" :open="thinkingExpanded" @toggle="(e) => (thinkingExpanded = (e.target as HTMLDetailsElement).open)">
  <summary>{{ t('agent.v2.turn.thinking.label') }}</summary>
  <pre class="ff-te__thinking-body">{{ turn.agent.thinking }}</pre>
</details>

<ol v-if="activityEvents.length" class="ff-te__events">
  <li v-for="event in activityEvents" :key="event.id" class="ff-te__event">
    <span class="ff-te__event-dot" />
    <span>{{ event.message }}</span>
  </li>
</ol>

<AskPrompt
  v-if="turn.agent.pendingAsk"
  :ask="turn.agent.pendingAsk"
  @reply="(value) => $emit('reply', value)"
/>

<p v-if="resultText" class="ff-te__sum ff-te__answer">
  {{ resultText }}
</p>

<p v-else-if="turn.agent.planResult?.summary" class="ff-te__sum">
  {{ turn.agent.planResult.summary }}
</p>

<section v-if="!resultText && turn.agent.planResult?.proposedActions?.length" class="ff-te__actions">
  <PlanActionRow
    v-for="a in turn.agent.planResult.proposedActions"
    :key="a.step"
    :action="a"
  />
</section>

<div v-if="turn.agent.planResult?.costEstimate" class="ff-te__cost">
  <!-- 既有 cost block 保持原样 -->
</div>

<div v-if="turn.agent.executeResult?.warnings?.length" class="ff-te__warn">
  <!-- 既有 warn block 保持原样 -->
</div>

<div v-if="turn.agent.errorMessage" class="ff-te__err">{{ turn.agent.errorMessage }}</div>

<div v-if="canExecute || isActive" class="ff-te__row">
  <Button
    v-if="canExecute"
    variant="primary"
    size="sm"
    @click.stop="$emit('execute')"
  >{{ t('agent.v2.turn.execute') }}</Button>
  <ControlBar
    v-if="isActive"
    :status="turn.agent.status"
    :has-plan-risk-step="hasPlanRiskStep"
    @pause="$emit('pause')"
    @resume="$emit('resume')"
    @skip="$emit('skip')"
    @approve="$emit('approve')"
    @deny="$emit('deny')"
    @cancel="$emit('cancel')"
  />
</div>
```

加入 imports：

```ts
import { computed, ref } from 'vue';
import AskPrompt from './AskPrompt.vue';
import ControlBar from './ControlBar.vue';
```

- [ ] **Step 3: 扩展 style，给新元素加样式**

```css
.ff-te__status--waiting_for_user { color: var(--ac); }
.ff-te__status--paused { color: var(--status-warning); }

.ff-te__progress-meta {
  display: flex; gap: var(--sp-md); align-items: baseline;
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-te__progress-label { color: var(--text-tertiary); }
.ff-te__progress-num { color: var(--text-secondary); }
.ff-te__progress-msg { color: var(--text-secondary); text-transform: none; letter-spacing: normal; }

.ff-te__thinking {
  border: 1px dashed var(--border-default);
  padding: var(--sp-sm) var(--sp-md);
  font-family: var(--font-mono); font-size: var(--text-small);
}
.ff-te__thinking summary {
  cursor: pointer; color: var(--text-tertiary);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
}
.ff-te__thinking-body {
  margin: var(--sp-sm) 0 0; white-space: pre-wrap; color: var(--text-secondary);
  max-height: 240px; overflow: auto;
}
```

- [ ] **Step 4: 同步 status i18n key 渲染**

`statusLabel` 已用 `agent.v2.turn.status.${status}` 模板拼接——新加的 `waiting_for_user` / `paused` i18n key 已在 Task 3 加入，因此 TypeScript 不会报错。

- [ ] **Step 5: typecheck**

Run: `cd web && bun run typecheck`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/src/components/organisms/agent/TurnEntry.vue
git commit -m "feat(agent): TurnEntry renders ask/progress/thinking/control bar"
```

---

## Task 10: TaskInputDock.vue — waiting/paused 时锁主输入

**Files:**

- Modify: `web/src/components/organisms/agent/TaskInputDock.vue`
- Modify: 父容器（找到使用 TaskInputDock 的页面，传新的 disabled）

- [ ] **Step 1: TaskInputDock 不改 props 定义（已有 disabled）；改用法**

`TaskInputDock` 的 `disabled` 已经接受 boolean——只需要在父容器传值时把 `waiting_for_user` / `paused` 也算上。

- [ ] **Step 2: 找到 TaskInputDock 的使用方**

Run: `grep -rn "TaskInputDock" web/src/`

预计在 `web/src/views/agent/` 或 `web/src/pages/agent/` 下；找出后修改 disabled 绑定：

```vue
<TaskInputDock
  :model-value="taskInput"
  :policy="policy"
  :reasoning-effort="reasoningEffort"
  :disabled="
    isSending ||
    activeSession?.messages.some(
      (m) => m.role === 'agent' && (m.status === 'waiting_for_user' || m.status === 'paused')
    )
  "
  @update:model-value="(v) => (taskInput = v)"
  @update:policy="(v) => (policy = v)"
  @update:reasoning-effort="(v) => (reasoningEffort = v)"
  @submit="sendMessage"
/>
```

> 注：如果父容器已有别的 disabled 来源，用 `||` 叠加；不要替换。

- [ ] **Step 3: typecheck + 跑既有 TaskInputDock 相关 spec（如有）**

Run: `cd web && bun run typecheck`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/src/components/organisms/agent/TaskInputDock.vue web/src/<父容器路径>
git commit -m "feat(agent): lock TaskInputDock while turn waits for user or paused"
```

---

## Task 11: 端到端 spec — ask 全链路 + pause/resume + cancel via inbox

**Files:**

- Modify: `web/src/composables/useAgentSession.spec.ts`

- [ ] **Step 1: 写测试**

在 `useAgentSession.spec.ts` 末尾追加。沿用 Task 6 已建立的 `vi.mock` + `vi.mocked` + `loadComposable()` 风格（**不**用 `vi.spyOn(await import(...))`）：

```ts
import type { AgentJobEvent } from '../types/agent';

describe('useAgentSession — A frontend end-to-end', () => {
  it('replyToAsk forwards reply via inbox and advances status to running', async () => {
    vi.mocked(agentApi.sendAgentReply).mockResolvedValue({
      inboxMessageId: '1', kind: 'reply', acceptedAt: '2026-05-26T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { createSession, replyToAsk } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-e2e', role: 'agent', content: '', status: 'waiting_for_user',
      events: [], timestamp: new Date().toISOString(), executeJobId: '99',
      pendingAsk: {
        messageId: '101', prompt: 'pick', schema: { choice: ['A', 'B'] },
        timeoutSec: 60, askedAt: new Date().toISOString(),
      },
    };
    session.messages.push(msg);

    await replyToAsk(msg, 'A');

    expect(agentApi.sendAgentReply).toHaveBeenCalledWith('99', '101', 'A');
    expect(msg.status).toBe('running');
    expect(msg.pendingAsk).toBeUndefined();
  });

  it('pause + resume sends control.pause then control.resume', async () => {
    vi.mocked(agentApi.pauseAgentJob).mockResolvedValue({
      inboxMessageId: '2', kind: 'control.pause', acceptedAt: '2026-05-26T00:00:00Z',
    });
    vi.mocked(agentApi.resumeAgentJob).mockResolvedValue({
      inboxMessageId: '3', kind: 'control.resume', acceptedAt: '2026-05-26T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { createSession, pauseTurn, resumeTurn } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-pp', role: 'agent', content: '', status: 'running',
      events: [], timestamp: new Date().toISOString(), executeJobId: '77',
    };
    session.messages.push(msg);

    await pauseTurn(msg);
    expect(agentApi.pauseAgentJob).toHaveBeenCalledWith('77');

    await resumeTurn(msg);
    expect(agentApi.resumeAgentJob).toHaveBeenCalledWith('77');
  });

  it('cancel goes through inbox helper (not legacy /cancel route)', async () => {
    vi.mocked(agentApi.cancelAgentTurn).mockResolvedValue({
      inboxMessageId: '4', kind: 'control.cancel', acceptedAt: '2026-05-26T00:00:00Z',
    });

    const { default: useAgentSession } = await loadComposable();
    const { createSession, cancel } = useAgentSession();
    const session = createSession();
    const msg: ChatMessage = {
      id: 'msg-c', role: 'agent', content: '', status: 'running',
      events: [], timestamp: new Date().toISOString(), executeJobId: '55',
    };
    session.messages.push(msg);

    await cancel(msg);
    expect(agentApi.cancelAgentTurn).toHaveBeenCalledWith('55');
    expect(msg.status).toBe('canceled');
  });
});
```

- [ ] **Step 2: 运行**

Run: `cd web && bun run test useAgentSession`
Expected: PASS（含新 3 个用例 + 全部既有用例）

- [ ] **Step 3: 运行全前端测试 smoke**

Run: `cd web && bun run test`
Expected: 全部 PASS（含 useAskTimeout、useAgentSession）

- [ ] **Step 4: Commit**

```bash
git add web/src/composables/useAgentSession.spec.ts
git commit -m "test(agent): end-to-end specs for ask/pause/resume/cancel via inbox"
```

---

## Task 12: 手动验证 + 截图

**Files:** N/A（dev server + 浏览器）

- [ ] **Step 1: 启动后端 + worker + 前端**

Run（三个终端）：

- `cd app && uv run uvicorn fileflash.main:app --reload`
- `cd app && uv run python -m fileflash.scripts.run_with_workers`
- `cd web && bun run dev`

- [ ] **Step 2: 在浏览器中跑 4 个场景**

1. **agent.progress 实时显示**：发一个会有多步的请求（例如"列出根目录"），观察 TurnEntry 出现 `PROGRESS step/total` 行
2. **手动暂停 + 恢复**：长任务中点 Pause → 等 3s → 点 Resume；UI 应在 `agent.paused` / `agent.resumed` 事件到达时切换状态
3. **取消走 inbox**：长任务中点 Cancel；Network 面板应只见到 `POST /agent/jobs/<id>/messages`（body `{kind:"control.cancel"}`），**不**应有任何 `POST /agent/cancel/<id>`
4. **ask 流程**：手动触发一个会调 `AskProtocol.ask()` 的场景（若 PlanRunner 暂未启用 ask，跳过此项并在 acceptance checklist 标注"待后续 prompt 模板启用"）

- [ ] **Step 3: 监控 console + Network**

Network 应无 404、500；console 应无报红错误；旧的 `agent/cancel/...` 调用应已不出现。

- [ ] **Step 4: 截图保留**

把 3-4 个场景截图保存到本地（PR 描述贴）。

> 注：本 Task 不写代码也不 commit；它是"验收门"。

---

## Acceptance Checklist

- [ ] `web/src/types/agent.d.ts` 含 14 种 `AgentJobEventType` 与 7 种 `AgentInboxMessageKind`
- [ ] `web/src/api/agent.ts` 删除 `cancelAgentJob`、新增 `sendAgentMessage` 与 6 个 control helper（pause/resume/approve/deny/skip/cancel）+ `sendAgentReply`
- [ ] `useAgentSession.ts` 的 `MsgStatus` 含 `waiting_for_user` / `paused`；`ChatMessage` 含 `pendingAsk` / `pauseRequestedAt` / `progress` / `thinking` / `partials`
- [ ] `useAgentSession` 暴露 `replyToAsk` / `pauseTurn` / `resumeTurn` / `approveStep` / `denyStep` / `skipStep`；`cancel` 走 `control.cancel`
- [ ] `AskPrompt.vue` 渲染 prompt + schema.choice 按钮组 / 自由文本 + 倒计时；`ControlBar.vue` 按状态渲染按钮
- [ ] `TurnEntry.vue` 显示 progress 条、thinking 折叠区、AskPrompt、ControlBar；状态行支持新状态
- [ ] `TaskInputDock.vue` 在 `waiting_for_user` / `paused` 时主输入框 disable
- [ ] 13 条新 i18n key 中英文齐全
- [ ] `useAgentSession.spec.ts` + `useAskTimeout.spec.ts` 全部 PASS
- [ ] Task 12 手测 3+ 场景通过，Network 中没有遗留的 `POST /agent/cancel/...` 调用

## 范围外（留给后续）

- prompt 模板里 LLM 触发 `ask` 的判断逻辑（A-backend Task 14 step 3 已注明）—— 触发后本前端 plan 的 AskPrompt 会自动渲染
- `tool.partial` 的 UI 渲染（本 plan 仅做数据缓存，UI 留给后续；TurnEntry 当前不渲染 partials 内容）
- 思考块的 token 级流式动画（spec 明确不做）
- 多 tab/多端同步（spec 明确不做）
