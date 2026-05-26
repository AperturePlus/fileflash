# Agent 子系统改进设计（2026-05-26）

## 背景与目标

FileFlash 当前 agent 子系统存在三个互相牵连的问题：

1. **交互、反馈机制不完善**——只有单向 SSE，事件由后端 0.6s 轮询 DB 产出；事件类型贫乏；用户在 plan 之后不能与 agent 中途对话；只能 cancel 整个 job，无 pause/resume/step 审批。
2. **删除 session 没有级联**——前端 `deleteSession()` 仅清 localStorage；后端无 DELETE 接口；BackgroundJob 与"对话级 session"之间没有归属关系。
3. **内置工具太少**——硬编码 9 个 `drive.*`，扩展一个工具要改 3 处（`DEFAULT_AGENT_TOOLS` / `_tool_schemas` / `router.dispatch`）。

本设计把以上三件事拆成三个互相独立、可分别落地的子项目，从架构层把"双向交互通道、对话级 session、工具表"这三块地基补齐。

## 顶层路线图

| 子项目 | 内容 | 体量 |
|---|---|---|
| **A. 交互/反馈层重构** | Redis pub/sub 替换 DB 轮询；POST 上行 inbox；新事件类型；ask/pause/resume/step approve | 大 |
| **B. ChatSession 上升到后端 + 软删除 + 级联中断** | 新建 `AgentChatSession` 表；BackgroundJob 归属到 session；DELETE 接口；前端 localStorage 迁服务端 | 中 |
| **C. ToolRegistry 注册架构 + 5 个查询工具** | `ToolSpec` 对象替代 if/elif；schema/dispatch/risk 三合一；新增 search/getInfo/listRecent/statsByCategory/findDuplicates | 中 |

依赖关系：

```
A ──► B   （B 的 worker 中断与 session 级 control 复用 A 的 inbox 通道）
   │
   └──► C  独立可并行
```

推荐顺序：**A → 并行(B,C) → 收尾**。

## 统一非目标（三个子项目共同）

- 不引入 WebSocket（双向通道用 SSE 推送 + POST inbox）
- 不引入新的存储引擎（Redis 已在用、PostgreSQL 已在用）
- 不重写 prompt 模板
- 不动 skill 体系（`AgentSkill` / `tool_whitelist_json` 语义保留）
- 不做 MCP server 接入
- 不做工具运行时配额（`harness/budget.py` 仍是 scaffold）
- 不做内容理解类工具（OCR、摘要等）

---

## 子项目 A：交互/反馈层重构

### A.1 架构组件

```
                  ┌────────────────┐
worker (agent) ──►│  AgentEventBus │──► Redis pub/sub channel
                  └────────────────┘     agent:job:{job_id}:events
                          ▲
                          │ subscribe
                  ┌───────┴──────────┐
       web ──────►│  SSE endpoint    │────► browser
                  └──────────────────┘
                                                     ┌────────────────┐
       browser ──POST messages──► web ──► AgentInbox │ → Redis channel│
                                          (写 DB +)  │   agent:job:..:│
                                                     │   inbox        │
                                                     └────────────────┘
                                                              ▲
                                                              │ subscribe
                                                          worker (await)
```

四个新单元，每个职责单一：

| 单元 | 文件 | 职责 |
|---|---|---|
| `AgentEventBus` | `agents/harness/event_bus.py`（替换现有空 scaffold） | 把事件 publish 到 Redis；提供异步订阅器 |
| `AgentInbox` | `agents/harness/inbox.py`（新） | 接收用户上行消息，写 DB + publish 到 inbox channel |
| `AskProtocol` | `agents/harness/ask.py`（新） | runner 调用 `await ask(...)` 暂停等回答；底层订阅 inbox channel |
| 新 schema | `schemas/agent.py` 扩展 | 新事件类型 + 上行 message 类型 |

### A.2 数据流（以 agent 中途提问为例）

1. `plan_runner` 决定需要澄清 → `await AskProtocol.ask(job_id, prompt, schema, timeout)`
2. `AskProtocol`：① 写一行 `AgentInboxMessage(role=agent, kind=ask, status=waiting)`；② `event_bus.publish(agent.ask)`；③ 在 `asyncio.Event` 上等待 inbox 订阅器唤醒
3. 前端收到 `agent.ask` SSE → 渲染选择气泡 → 用户选择 → `POST /agent/jobs/{id}/messages` body `{kind:"reply", reply_to:<message_id>, value:...}`
4. `AgentInbox.handle`：① 写 `AgentInboxMessage(role=user, kind=reply, reply_to=...)`；② publish 到 `agent:job:{id}:inbox`
5. worker 端 `AskProtocol` 订阅器收到消息 → set `asyncio.Event` → 调用方 `await` 返回回答 → runner 继续

### A.3 新事件类型（`schemas/agent.py`）

**下行**（worker → 前端，沿 SSE）：

- `agent.thinking` — `{text}` 阶段性 reasoning 块（不做 token 级流）
- `agent.progress` — `{step, total, message, percent?}` 长任务进度
- `agent.ask` — `{message_id, prompt, schema, timeout_sec}` 请用户回答
- `agent.paused` / `agent.resumed` — 状态变化广播
- `tool.partial` — `{tool_name, step_no, chunk}` 大输出分段
- 保留：`job.*` / `plan.ready` / `tool.started/succeeded/failed`

**上行**（前端 → worker，沿 POST `/agent/jobs/{id}/messages`，body 区分 `kind`）：

- `kind:"reply"` — 回答 `agent.ask`
- `kind:"control.pause"` / `kind:"control.resume"`
- `kind:"control.approve"` / `kind:"control.deny"` — 单工具实时审批
- `kind:"control.skip"` — 跳过当前步
- `kind:"control.cancel"` — 取消（与既有 `POST /agent/cancel/{job_id}` 等价，新接口归一化）

### A.4 新表

```sql
AgentInboxMessage
  inbox_message_id   PK   BigInt Identity
  job_id             FK   BackgroundJob CASCADE   NOT NULL
  role               enum ('agent', 'user')
  kind               enum ('ask', 'reply',
                          'control.pause', 'control.resume',
                          'control.approve', 'control.deny',
                          'control.skip', 'control.cancel')
  payload_json       JSONB                         NOT NULL
  reply_to_id        FK   self                     NULL
  status             enum ('waiting','answered','timed_out','dropped')
                                                   NULL  -- 仅 kind=ask 用
  created_at         DateTime                      NOT NULL
  answered_at        DateTime                      NULL

INDEX (job_id, created_at)
INDEX (job_id, status)
```

事件本身不入库（已经在 Redis pub/sub）。审计如需要再加 `agent_event_log`，本轮不做。

### A.5 SSE 推送实现替换

`routers/agent.py` 的 `_event_stream`（agent.py:84）从 DB 轮询改为：

```python
async with event_bus.subscribe(job_id) as stream:
    async for event in stream:
        yield sse_format(event)
```

`AGENT_EVENT_POLL_INTERVAL_SEC` 配置项**直接删除**——agent 子系统当前没有第三方 API 消费者，不必保留 deprecation 期。DB 轮询逻辑彻底删除。

### A.6 worker 中断/暂停实现

`ExecuteRunner` 每步开始前：

```python
await inbox.consume_controls(job_id)   # 处理所有 pending control
if state.is_paused:
    await inbox.wait_for_resume(job_id)  # 阻塞直到 control.resume
if state.is_canceled:
    raise JobCancelled()
```

pause/resume/skip 不杀 worker——仅在 step 边界检查 inbox。意味着如果一个 LLM 调用正在进行（≤30s），pause 会在它返回后才生效。**真中断（HTTP 任务取消）不在本轮范围内**。

### A.7 前端状态机变化

`useAgentSession.ts` 增两个状态：

- `waiting_for_user`（收到 `agent.ask`）
- `paused`（收到 `agent.paused`）

新组件/改动：

- `TaskInputDock.vue`：`waiting_for_user` 时渲染 ask 选项/输入框；`paused` 时渲染恢复按钮
- `TurnEntry.vue`：渲染 `agent.thinking` / `agent.progress` / `tool.partial`
- 新增 `web/src/api/agent.ts:sendAgentMessage()` 调 POST `/agent/jobs/{id}/messages`

### A.8 路由层变化

新增：

- `POST /agent/jobs/{job_id}/messages` — 上行通道（body 含 `kind`）

删除：

- `POST /agent/cancel/{job_id}` — 直接删除；取消改走 `POST /agent/jobs/{id}/messages` body `{kind:"control.cancel"}`

保留不变：

- `POST /agent/plan` / `POST /agent/execute` / `GET /agent/jobs/{id}/events`

### A.9 测试策略

- `AgentEventBus`：单元测试 publish/subscribe；fake Redis（既有项目已有的 fakeredis 复用，如无则 mock）
- `AgentInbox`：集成测试 happy path + 重复 reply + 不存在的 reply_to
- `AskProtocol`：测试超时；测试在 worker 重启后仍能从 DB 重建状态（recovery 不做，但 status=waiting 的 ask 重启后 fail-fast）
- SSE 端到端：mock worker publish 一串事件，前端断言收到顺序

### A.10 非目标（A 特有）

- 不做 token 级流式 thinking
- 不做多 tab/多端同步（同账号多开浏览器不保证一致）
- 不做 ask 超时后的自动 fallback（超时直接 fail job）
- 不做 worker 端真中断 LLM 调用（只在 step 边界检查）

---

## 子项目 B：ChatSession 上升到后端 + 软删除 + 级联中断

### B.1 关键事实

- 后端 `AgentWorkSession` ≠ 前端 "Session"：前者是**单 job 的 checkpoint**（`job_id UNIQUE`）；后者是**前端 localStorage 对象**，含多个 ChatMessage、每条可关联多个 BackgroundJob。
- 后端目前**没有"对话级 session"实体**，无法回答"这个 session 下有哪些 plan/job"。
- 本子项目把对话级 session 实体化到后端，并基于它做软删除 + 级联中断。

### B.2 新表

```sql
AgentChatSession
  chat_session_id    PK   BigInt Identity
  user_id            FK   User CASCADE        NOT NULL
  title              String(255)              NOT NULL
  archived           Boolean DEFAULT FALSE
  deleted_at         DateTime                 NULL   -- 软删除标记
  created_at         DateTime                 NOT NULL
  updated_at         DateTime                 NOT NULL

INDEX (user_id, deleted_at, updated_at DESC)
```

### B.3 BackgroundJob 改动

- 新增 `chat_session_id FK AgentChatSession ON DELETE CASCADE NULLABLE`
- 新增 `deleted_at DateTime NULL`（job 级软删除，跟随 session 软删除标记）
- 旧 job（无 chat_session_id）保留 NULL，列表查询 default 隐藏；提供"未归属"过滤
- FK 选 CASCADE 的原因：硬删 session 时 BackgroundJob 同步消失，再通过既有 `job_id CASCADE` 把 Plan/ActionLog/WorkSession/InboxMessage 一并清掉。NULLABLE 是为了兼容历史 job 与"显式归属未来某 session"两种情况。

### B.4 API

| Method | Path | 行为 |
|---|---|---|
| `POST /agent/chat-sessions` | 创建新 session（body: title?） | 返回 `{chat_session_id, ...}` |
| `GET /agent/chat-sessions` | 当前用户未删除 session 列表（分页） | `deleted_at IS NULL` |
| `GET /agent/chat-sessions/{id}` | 单 session + 该 session 下的 turn 概览 | 404 if 不属于当前用户或已软删 |
| `PATCH /agent/chat-sessions/{id}` | 改 title / archived | 仅限自己 |
| `DELETE /agent/chat-sessions/{id}` | **软删除**（流程见 B.5） | 200 |

`POST /agent/plan` 和 `POST /agent/execute` 入参**强制**新增 `chat_session_id`（必填）；缺省直接返回 422。前端在迁移后所有调用点都传值。

### B.5 DELETE 流程

```
1. SELECT ... FOR UPDATE 该 session（防并发）
2. set chat_session.deleted_at = now()
3. 找出该 session 下所有未完成 BackgroundJob（status in ('queued','running','planning','awaiting_confirm','executing','paused')）
4. 对每个未完成 job：
   - mark job.deleted_at = now()
   - 调既有 cancel_job 逻辑 set cancel_requested_at
   - 通过 A 的 inbox 写 AgentInboxMessage(kind='control.cancel') 唤醒 worker
5. 已完成 job：仅 mark deleted_at，不回滚业务操作
6. 关联 Plan / ActionLog / WorkSession / InboxMessage 保留（FK 是 job_id CASCADE，硬删时才级联）
7. event_bus.publish('session.deleted', {chat_session_id})
```

> 注：drive 业务操作（move/delete 文件）一旦执行就不可逆。"取消" 仅停止后续步骤，不撤销已生效结果。

### B.6 GC 任务

- 新建 cron：每天扫 `chat_session.deleted_at < now() - INTERVAL '30 days'` 的记录，**硬删**
- 硬删 chat_session 时关联表通过 FK CASCADE 自动清理：
  - `BackgroundJob`（FK `chat_session_id ON DELETE CASCADE`）→ 触发 job 删除
  - 进而 `AgentPlan` / `AgentActionLog` / `AgentWorkSession` / `AgentInboxMessage` 通过既有 `job_id CASCADE` 自动清
- `AgentMemory` 走 `user_id`，不受影响
- 未归属 session 的旧 job（`chat_session_id IS NULL`）不在 GC 范围内
- GC 写入既有 cron 体系（参考 `services/admin/storage.py` 模式）

### B.7 前端迁移

- `useAgentSession.ts`：
  - 删除 `STORAGE_KEY = 'fileflash.agent.sessions.v1'` 持久化（保留 in-memory cache）
  - 初始化：调 `GET /agent/chat-sessions` 拉列表
  - `createSession()` → `POST /agent/chat-sessions`，拿服务端 id
  - `deleteSession()` → `DELETE /agent/chat-sessions/{id}`
  - 旧 localStorage 数据：首次启动检测到旧 key 时，**逐条迁移**（POST 创建 session、把 ChatMessage 内 job_id 通过新接口 `POST /agent/chat-sessions/{id}/attach-jobs` 挂上），迁移完成后删除旧 key
- `web/src/api/agent.ts`：新增 chat-session CRUD 方法
- 单元测试 `useAgentSession.spec.ts` 改为对 mock API 断言而非对 localStorage 断言

### B.8 worker 中断协议

复用 A.6 的协议：B 不引入新的中断机制，只是确保 DELETE 流程发出的 `control.cancel` 能被 ExecuteRunner / PlanRunner 在 step 边界识别并抛 `JobCancelled`。

### B.9 测试策略

- API：测 CRUD + 权限隔离（A 用户不能删 B 的 session）+ 软删后 GET 返 404
- DELETE 级联：建 session 含 2 个 running job、1 个 succeeded job → DELETE → 断言两个 running job `cancel_requested_at` 已设、inbox 收到 `control.cancel`、succeeded job 不变、所有 job `deleted_at` 已设
- 前端迁移：mock 旧 localStorage 数据 + mock API，断言迁移后旧 key 已删、API 调用顺序正确
- GC：插入 31 天前已软删的 session 跑 GC，断言记录消失

### B.10 非目标（B 特有）

- 不做"恢复已删 session" UI（数据 30 天内还在 DB，但本轮不出 UI）
- 不做 session 跨用户共享
- 不做 session 收藏/标签
- 不做管理员强制硬删入口

---

## 子项目 C：ToolRegistry 注册架构 + 查询工具

### C.1 现状痛点

- `router.py:38-130` 一大串 if/elif；新加工具改 3 处
- `policy.py:classify_tool_risk()` / `classify_tool_side_effect()` 又是一组 if/elif
- `AgentSkill.tool_whitelist_json` 是字符串名单，无 registry 校验

### C.2 ToolRegistry 结构

```python
# agents/harness/tool_registry.py（新）

@dataclass(frozen=True)
class ToolSpec:
    name: str                              # "drive.listFolder"
    description: str                       # 给 LLM 看
    schema: dict[str, Any]                 # JSON Schema input
    side_effect: Literal["read", "write"]
    risk: Literal["low", "medium", "high"]
    requires_confirmation: bool
    handler: Callable[[ToolContext, dict], Awaitable[dict]]

class ToolRegistry:
    def register(self, spec: ToolSpec) -> None: ...
    def get(self, name: str) -> ToolSpec: ...
    def all(self) -> list[ToolSpec]: ...
    def schemas_for(self, names: list[str]) -> list[dict]: ...

REGISTRY = ToolRegistry()
```

`ToolContext` 保留现有 router.py 内传 ctx 的形态（携带 db session、user、job 等）。

### C.3 文件布局

```
agents/
  harness/
    tool_registry.py        ← 新：Spec + Registry
  tools/                    ← 新目录
    __init__.py             ← import 所有工具触发注册
    drive_list_folder.py
    drive_count_files.py
    drive_create_folder.py
    drive_move_file.py
    drive_move_folder.py
    drive_rename_file.py
    drive_rename_folder.py
    drive_delete_file.py
    drive_delete_folder.py
    # —— 本轮新增 5 个查询工具 ——
    drive_search_files.py
    drive_get_file_info.py
    drive_list_recent.py
    drive_stats_by_category.py
    drive_find_duplicates.py
```

每个工具文件结构：

```python
# agents/tools/drive_list_folder.py
from ..harness.tool_registry import REGISTRY, ToolSpec
from ..harness.context import ToolContext

async def _handle(ctx: ToolContext, args: dict) -> dict:
    ...  # 业务逻辑（从 router.py 搬过来）

REGISTRY.register(ToolSpec(
    name="drive.listFolder",
    description="List entries inside a folder.",
    schema={...},                      # 从 plan_runner._tool_schemas 搬
    side_effect="read",
    risk="low",
    requires_confirmation=False,
    handler=_handle,
))
```

### C.4 拆掉的旧代码

- `router.py:dispatch` 的 if/elif 全部删除 → 改为 `spec = REGISTRY.get(name); return await spec.handler(ctx, args)` + 通用错误包装
- `plan_runner.py:_tool_schemas` → `REGISTRY.schemas_for(whitelist or REGISTRY.all_names())`
- `plan_runner.py:DEFAULT_AGENT_TOOLS` → 不再硬编码；改从 `REGISTRY.all_names()` 计算（或保留作为"默认启用名单"配置项）
- `policy.py:classify_tool_risk / classify_tool_side_effect` → 从 `REGISTRY.get(name).risk / side_effect` 读取；删除 if/elif 表
- `AgentSkill` 保存时调 `REGISTRY.validate(whitelist)`：未知工具名直接 422

### C.5 新增 5 个查询工具

| name | 入参 | 出参 | 实现说明 |
|---|---|---|---|
| `drive.searchFiles` | `query` / `folder_id?` / `category?` / `mime_prefix?` / `modified_after?` / `limit≤200` | `[{file_id,name,path,size,mime,modified_at}]` | 复用 `services/files` 既有查询能力；不做全文 |
| `drive.getFileInfo` | `file_id` | 单条详情 + 路径 + size + mime + tags | 复用现有 getFile |
| `drive.listRecent` | `limit≤50` / `since?` | 最近修改的文件列表 | 走既有最近活动查询 |
| `drive.statsByCategory` | `folder_id?` | `{image:N, video:N, document:N, other:N, total_size}` | 利用 mime/category 分桶 |
| `drive.findDuplicates` | `folder_id?` / `by="hash"\|"name+size"` | 重复文件组列表 | 用既有 hash 字段 |

全部 `side_effect=read`、`risk=low`、`requires_confirmation=false`，不进审批流。

### C.6 plan_runner / prompt 影响

- `DEFAULT_AGENT_TOOLS` 从 9 个变 14 个
- prompt 模板**不动**——schema 自动从 registry 取
- `_skill_tool_whitelist()` 行为不变（仍读 `AgentSkill.tool_whitelist_json`），但加 registry 校验

### C.7 测试策略

- `ToolRegistry`：单元测试（注册/查找/重复名字报错/未知名字报错/schemas_for 顺序）
- 每个新工具：集成测试调 handler → 期望输出。**用真 DB + 真 services**（不 mock，遵循项目原则）
- `policy.py` 改用 registry 后：保留原有风险/副作用的回归测试，断言读 registry 与旧 if/elif 给出同结果
- 端到端：plan 一个含 `drive.searchFiles` 的请求 → confirm LLM 拿到 schema → execute → action_log 有正确记录

### C.8 非目标（C 特有）

- 不做 MCP server 接入（`AgentMcpServer` 表保留，本轮不动）
- 不做工具版本/弃用机制
- 不做工具运行时配额
- 不做内容理解工具（OCR/摘要/缩略图）
- 不动 `AgentSkill.tool_whitelist_json` 数据形态（仍是字符串名单）

---

## 跨子项目影响矩阵

| 文件 / 模块 | A 改动 | B 改动 | C 改动 |
|---|---|---|---|
| `models/tables_agent.py` | + `AgentInboxMessage` | + `AgentChatSession`；`BackgroundJob` 加列 | — |
| `schemas/agent.py` | + 新事件类型、上行 message 类型 | + ChatSession schema | — |
| `routers/agent.py` | + POST `/agent/jobs/{id}/messages`；SSE 改 event_bus | + chat-sessions CRUD；plan/execute 入参 | — |
| `agents/harness/events.py` | 替换为 `event_bus.py` | — | — |
| `agents/harness/inbox.py` | 新 | — | — |
| `agents/harness/ask.py` | 新 | — | — |
| `agents/harness/policy.py` | — | — | 读 registry 替代 if/elif |
| `agents/harness/router.py` | — | — | dispatch 改为 registry lookup |
| `agents/runtime/plan_runner.py` | 接 ask | 接 chat_session_id | schema 改读 registry |
| `agents/runtime/execute_runner.py` | step 边界检查 inbox / pause | 同 A | dispatch 简化 |
| `agents/tools/` | — | — | 新目录，14 个工具文件 |
| `services/admin/storage.py`（GC） | — | + chat-session GC 任务 | — |
| `web/src/composables/useAgentSession.ts` | + waiting_for_user / paused 状态 | localStorage → API | — |
| `web/src/components/organisms/agent/` | TurnEntry / TaskInputDock 渲染新事件 | SessionList 调 API | — |
| `web/src/api/agent.ts` | + sendAgentMessage | + chat-session CRUD | — |

## 兼容与迁移

- **后端 API**：本设计**不要求向后兼容**——agent 子系统目前没有公开第三方 API 消费者；旧的 `POST /agent/cancel/{job_id}` 直接删除，前端同 PR 切换到 `control.cancel`
- **前端 localStorage**：`fileflash.agent.sessions.v1` 数据**一次性迁移**到服务端；迁移完成清 key
- **数据库迁移**：3 张表层面的改动（新增 `AgentInboxMessage` / `AgentChatSession`、`BackgroundJob` 加列），用 Alembic 一次迁移完成；旧 BackgroundJob `chat_session_id` 留 NULL（视作未归属）
- **配置项**：`AGENT_EVENT_POLL_INTERVAL_SEC` 删除；新增 `AGENT_INBOX_ASK_TIMEOUT_SEC`（默认 1800s）、`AGENT_CHAT_SESSION_GC_DAYS`（默认 30）

## 滚动出场顺序

1. **A 全量上线**：A 是基础设施，B/C 都依赖它；A 不上线则 B 的中断协议无处发、C 的 step approval 也没通道
2. **B 与 C 可并行**：互不依赖
3. **每个子项目独立 PR / 独立 plan**：在写 implementation plan 时，按子项目各自拆 phase

## 风险与开放问题

- **Redis pub/sub 可靠性**：消息丢失风险存在（订阅者未连上时 publish 的消息会丢）。缓解：① 关键状态（ask、控制信号）持久化到 `AgentInboxMessage` 表；② SSE 重连时前端从 inbox/action_log 增量拉一次 catch-up。**event_bus 的事件本身不持久化是 acceptable 的**（属于实时通知）。
- **worker 多副本**：当前 `AgentWorkerConsumer` 可能多副本运行（`agent-{uuid}` 命名）。`AskProtocol` 等待的 `asyncio.Event` 是进程内的——如果用户回复到来时该 worker 已挂，`status=waiting` 的 ask 永远不会被消费。**缓解**：worker 启动时扫一次 owned-by-self 的 waiting ask、超过 timeout 直接 fail；同时 `AGENT_INBOX_ASK_TIMEOUT_SEC` 默认 30 分钟限制阻塞时间。
- **真中断 LLM 调用**：不在本轮范围。若用户对"pause 后 30s 才生效"反馈强烈，下一轮加 httpx 任务取消。
- **前端迁移失败**：localStorage 迁移过程中网络失败可能丢数据。缓解：迁移**幂等**——同步前不删 localStorage；服务端创建成功后再删。
