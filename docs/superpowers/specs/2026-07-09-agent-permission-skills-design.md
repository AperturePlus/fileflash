# Agent 权限层 + LLM 可选用 Skills 设计（2026-07-09）

## 背景与目标

FileFlash agent 子系统已完成三块地基（见 [2026-05-26-agent-improvements-design.md](2026-05-26-agent-improvements-design.md)）：

- **子项目 A** 交互/反馈层（Redis pub/sub event bus、inbox、ask 协议、pause/resume/step approve）——已落地
- **子项目 B** ChatSession 后端化 + 软删除 + 级联中断——当前 `feat/audit` 分支进行中
- **子项目 C** ToolRegistry + 14 个 `drive.*` 工具——已落地

但 [15-agent.md](../../design/modules/15-agent.md) 设计文档中规划的**权限管理**与 **Skills 可供 LLM 使用**两块尚未落地。当前现状（已核对代码）：

1. **权限层是 stub**：[policy.py:48](../../../app/src/fileflash/agents/harness/policy.py) `PolicyGuard.evaluate_tool_call` 只检查「工具是否注册」+「高危是否已确认」两条规则。没有 `executionPolicy`（planOnly/confirm/autopilot）的统一裁决，没有 `dataPolicy`（allow_file_content / max_read_bytes / allowed_mime_types）的执行——`AgentDataPolicy` schema 已定义（[schemas/agent.py:42](../../../app/src/fileflash/schemas/agent.py)）但**从未被读取**，是死 schema。
2. **Skills 不可被 LLM 选用**：[plan_runner.py:313](../../../app/src/fileflash/agents/runtime/plan_runner.py) `_choose_skill` 用 keyword 评分**硬选一个** skill 注入 prompt；LLM 看不到 skill 菜单、不能选/换/拒。`plan_template_json` / `inputs_schema_json` / `outputs_schema_json` 存了但不执行、不模板化。
3. **`AgentUserSetting` 默认值不生效**：表已有 `default_execution_policy` / `default_data_policy_json` / `default_budget_tokens` / `default_max_steps`，但运行时从不读取。
4. **没有 readFile 工具**：`dataPolicy`（「允不允许 LLM 分析文件」）目前没有落点——没有工具读文件内容，policy 也就无从管控。

本设计把这三件事收敛到**一个权限裁决点**上落地，复用现有 ToolRegistry / SkillService / AgentUserSetting，不引入新基础设施。

## 范围决策（已与用户确认）

1. **Skills 形态**：LLM 可选用——skill 作为 LLM 可调用的 meta-tool，模型能选/拒/换。
2. **文件内容工具**：新增 `drive.readFile`，受 `dataPolicy` 真管控（不含 writeFile / OCR / 二进制分析）。
3. **权限模型**：executionPolicy + dataPolicy + skill 白名单**三轴求交（取最严）**，复用 `AgentUserSetting` 作默认。不做 RBAC / per-user 工具粒度表 / per-skill 风险覆盖。

## 顶层架构

把 `PolicyGuard.evaluate_tool_call` 从「只接 `(tool_name, high_risk_confirmed)`」拓宽为「接完整 `PolicyContext`」，成为 plan 与 execute 两个循环中**唯一**的放行/拒绝点。

```
                    ┌─────────────────────────────────────────┐
   PlanAgentRequest │  AgentUserSetting (defaults, if omitted) │
   (policy/hints)   └───────────────────┬─────────────────────┘
                                       ▼
                          PermissionResolver.effective(request, setting, skill)
                          → EffectivePermission {
                              execution_policy,
                              data_policy,
                              allowed_tools,        # skill_whitelist ∩ registry
                              deny_read_content,    # precomputed
                              high_risk_confirmed
                            }
                                       │
              ┌────────────────────────┴───────────────────────┐
              ▼                                                ▼
   PlanRunner._planning_tool_executor              ExecuteRunner per-step loop
   (skill-bound, read-only, budget)               (replay actions)
              │                                                │
              └──────────────► PolicyGuard.evaluate(           ◄──────┘
                                   ctx: ToolContext,
                                   action: {tool, input},
                                   permission: EffectivePermission,
                                   phase: "planning"|"executing"
                                ) → PolicyDecision {allowed, reasons[]}
                                      │
                          ┌───────────┴────────────┐
                          ▼                         ▼
                  ToolRouter.dispatch        structured denial
                  (real run)                (ActionLog status="denied" +
                                             tool.failed 事件)
```

### 三个新增/改动的单元（每个单一职责）

| 单元 | 文件 | 职责 |
|---|---|---|
| `PermissionResolver` | `agents/harness/permission.py`（新） | 合并 request policy + `AgentUserSetting` 默认 + skill 白名单 + dataPolicy，产出单一 `EffectivePermission`（取最严）。纯计算，除读 skill 行外无 I/O。 |
| `PolicyGuard`（拓宽） | `agents/harness/policy.py`（现有，重写） | 唯一放行/拒绝点。接 `EffectivePermission` + action + phase，返回 `PolicyDecision{allowed, reasons[]}`。替换现有 2 规则 stub。 |
| `agent.useSkill` meta-tool | `agents/harness/skill_tool.py`（新）+ registry hook | LLM 可调用的 skill 绑定面。绑定后重跑 `PermissionResolver` 收窄 `allowed_tools`。 |

**关键性质**：工具 handler 里的 ownership scoping（`File.owner_id == ctx.user_id`，今天真正的安全网）**保持不动**。权限层是**叠加**的——它回答「LLM 是否被允许*尝试*这个操作」，handler 仍回答「这个用户是否*拥有*这个资源」。拒绝永远是结构化的（reasons 列表），不是裸 403。

## 权限模型：`EffectivePermission` 与 `PolicyGuard`

### 三轴求交（取最严）

1. **executionPolicy**（`planOnly` | `confirm` | `autopilot`）——控制「写操作是否需确认」，不收窄工具集。
   - `planOnly`：execute job 根本不允许入队（在 `ExecuteService` 强制，已部分存在）。
   - `confirm`（默认）：任何 `write` action 置 `requires_confirmation=True`；高危额外需 `high_risk_confirmed`。
   - `autopilot`：写操作无需逐步确认；**高危仍永远需显式 `high_risk_confirmed`**（删除永不自动执行）。

2. **dataPolicy**（`AgentDataPolicy`：`allow_file_content` / `max_read_bytes` / `allowed_mime_types`）——控制「文件内容访问」。仅对内容读取工具（本轮仅 `drive.readFile`）生效。这是「允不允许 LLM 分析文件」的杠杆。
   - `allow_file_content=false` → `readFile` 拒绝。
   - `allow_file_content=true` → 仍受 `max_read_bytes`（默认 1 MiB）与 `allowed_mime_types`（默认 `["*/*"]`）约束。

3. **skill 白名单**（`AgentSkill.tool_whitelist_json`）——收窄工具集。skill 无白名单时以全 registry 为基；skill 只能收窄，不能放宽。

**求交规则**：`allowed_tools = registry ∩ skill_whitelist`；剩余工具中「读内容」类工具在 dispatch 时再受 dataPolicy 约束（因为 mime/size 决策依赖 action input，即具体哪个文件，不能在集合计算阶段定）。

### `EffectivePermission`（dataclass）

```python
@dataclass(frozen=True, slots=True)
class EffectivePermission:
    execution_policy: AgentExecutionPolicy
    data_policy: AgentDataPolicy
    allowed_tools: frozenset[str]          # registry ∩ skill_whitelist
    skill_key: str | None                  # 已绑定 skill，若无则 None
    deny_read_content: bool                # 预计算：not data_policy.allow_file_content
    high_risk_confirmed: bool              # execute 期来自 AgentApproval；plan 期恒 False
```

`high_risk_confirmed` 的来源分阶段：**plan 期**恒为 `False`（planning 不执行高危动作，写工具本就被拦）；**execute 期**取自 `ExecuteAgentRequest.approval.high_risk_confirmed`（已在 `ExecuteService` 校验过）。故 `PermissionResolver.effective` 接一个 `high_risk_confirmed` 入参，由调用方按阶段传入。

### `PermissionResolver`（合并器）

```python
class PermissionResolver:
    async def effective(
        self, *, request: PlanAgentRequest, setting: AgentUserSetting | None, skill
    ) -> EffectivePermission:
        # 1. execution_policy: request 覆盖 setting.default_execution_policy
        # 2. data_policy: request.data_policy 与 setting.default_data_policy_json 合并（取最严）
        # 3. skill_whitelist: 复用现有 _skill_tool_whitelist(skill) 逻辑
        # 4. allowed_tools = frozenset(registry ∩ skill_whitelist)
        # 5. deny_read_content = not data_policy.allow_file_content
```

dataPolicy 取最严合并：`allow_file_content = a and b`；`max_read_bytes = min(a, b)`；`allowed_mime_types = 两个 glob 列表的交集`（交集为空 → 实质拒绝所有内容读，作为 reason 显式呈现）。

### `PolicyGuard.evaluate`（裁决点——重写）

```python
async def evaluate(
    self, *, ctx: ToolContext, action, permission: EffectivePermission, phase
) -> PolicyDecision:
    spec = _lookup(action.tool)                       # 注册？否则 deny "unknown tool"
    if action.tool not in permission.allowed_tools:
        return deny("tool not permitted by active skill/policy")
    if spec.side_effect == "read" and _is_content_read(action.tool):
        if permission.deny_read_content:
            return deny("file content access disabled by dataPolicy")
        if not _mime_allowed(action.input, permission.data_policy, ctx):
            return deny("file mime not in allowed_mime_types")
        if _byte_range(action.input) > permission.data_policy.max_read_bytes:
            return deny("requested bytes exceed max_read_bytes")
    if spec.risk_level == "high" and not permission.high_risk_confirmed:
        return deny("high-risk action requires explicit confirmation")
    if permission.execution_policy == "planOnly" and phase == "executing":
        return deny("planOnly policy forbids execution")
    return allow()
```

两个调用点改为传 `EffectivePermission`：

- **Planner**（[plan_runner.py:99](../../../app/src/fileflash/agents/runtime/plan_runner.py)）——其 `_planning_tool_executor` 现在内联 `if tool_name not in allowed_tool_set` 检查；改为委托 `PolicyGuard.evaluate(phase="planning")`。结果一致，路径单一。
- **Execute runner**（[execute_runner.py:118](../../../app/src/fileflash/agents/runtime/execute_runner.py)）——替换现有只传 `high_risk_confirmed` 的调用为 `evaluate(phase="executing")`。

**拒绝处理**：被拒 action 返回结构化 `PolicyDecision` → execute 中抛 `ApiError(409, reasons=[...])` 并写 `ActionLog` 行 `status="denied"` + 发 `tool.failed` 事件（前端可见「为何被拒」）。planning 中返回现有 `_blocked_planning_tool_result` 形态，LLM 可反应并换路径。

## `drive.readFile` 工具与 dataPolicy 执行

让 `AgentDataPolicy` 从死 schema 变成活契约。一个新工具 + `PolicyGuard` 调用的辅助函数。

### `drive.readFile` 工具

```python
REGISTRY.register(ToolSpec(
    name="drive.readFile",
    description="Read text content of a file the user owns. Returns up to maxBytes; "
                "binary files are not returned directly. Subject to dataPolicy.",
    input_schema=_schema({
        "fileId": _FILE_ID,
        "maxBytes": {"type": "integer", "minimum": 1, "maximum": 1048576, "default": 262144},
        "offset": {"type": "integer", "minimum": 0, "default": 0},
    }, required=["fileId"]),
    side_effect="read",
    risk_level="medium",                 # 内容离开 DB → 用户文件进入 LLM
    requires_confirmation=False,
    handler=_read_file,
))
```

**Handler 行为**（`_read_file` 在 `agents/tools/drive.py`）：

1. 按 `ctx.user_id` scope 加载 `File` 行（ownership，同其他工具）。未找到 → 404，不 403（不泄露存在性）。
2. 用现有 `resolve_file_mime_type` 解析 mime。
3. 取 `StorageObject` + 从 MinIO 流式读字节。`ToolContext` 增 `storage_reader: MinioObjectStorageClient`（[s3/minio_client.py](../../../app/src/fileflash/s3/minio_client.py) 已存在，无需新存储代码）。用其 `iter_object_range(object_key, start=offset, end=offset+maxBytes-1)` 做有界范围读，`stat_object` 取 size。读 `offset..offset+maxBytes`。
4. **二进制守卫**：mime 不在文本类白名单（`text/*`、`application/json`、`application/pdf`、`application/xml` 等显式白名单）时，**不**返回原始字节，而返回 `{truncated: true, mime, size, note: "binary content not sent to model"}`。遵循设计文档「二进制永不直送 LLM」。
5. 文本类 mime 返回 `{fileId, name, mime, size, content, truncated, bytesReturned}`，`content` 截断到 `maxBytes`。

### 为何 `risk_level="medium"`（非 low）

对文件系统只读，但**把用户文件内容外发到 LLM provider**——这是隐私相关的副作用。medium 意味着默认 `confirm` 策略下它不会不出现在 plan 里就自动跑，且进入 cost/审计链。非高危（不删除），故不需 `high_risk_confirmed`。

### PolicyGuard 辅助函数（§2 引用）

```python
_CONTENT_READ_TOOLS = frozenset({"drive.readFile"})

def _is_content_read(tool_name: str) -> bool:
    return tool_name in _CONTENT_READ_TOOLS

def _mime_allowed(action_input, data_policy, ctx) -> bool:
    mime = _resolve_target_mime(action_input, ctx)   # 懒加载 File.mime，缓存
    return _glob_any(data_policy.allowed_mime_types, mime)

def _byte_range(action_input) -> int:
    return int(action_input.get("maxBytes", 262144)) + int(action_input.get("offset", 0))
```

`_resolve_target_mime` 需 DB 访问——故 `PolicyGuard.evaluate` 变 `async` 并接 `ctx: ToolContext`（已含 `db` + `user_id`）。它加载一次 `File` 行；handler 再复用同一解析（少量重复，可接受——或把解析出的 mime 经 `ToolContext` 传递，保持 guard 无状态倾向）。本设计 guard 做轻量 mime 查询，handler 做实际字节拉取。

### dataPolicy 合并边界情况

- `allowed_mime_types=[]`（空）→ 拒绝所有内容读（显式「完全不允许内容」）。
- `allowed_mime_types=["*/*"]`（默认）→ mime 检查通过，仅 `max_read_bytes` 约束。
- `max_read_bytes=0` → 实质等价 `allow_file_content` 关闭（任何非空读都拒）。

### 不做（YAGNI）

- 不做 `writeFile`（本轮只 readFile）。
- 不做 OCR / 图片 / 音频内容分析。
- 不做按文件「逐个确认」prompt——request 上的 `dataPolicy`（与 user setting 合并后）*即*确认。
- 不做分块流式送模型（单次有界读）。

## LLM 可选用 Skills（`agent.useSkill`）

「要有 skills 可供 LLM 使用」的核心。把 runner 从「硬选一个 skill 注入」改为「runner 提议 top-K，LLM 经 meta-tool 选用（或拒绝），选择即时收窄 `allowed_tools`」。

### Skill 发现 → 注入

`_choose_skill` 替换为 `_candidate_skills`（复用现有 keyword 评分，但返回 **top-K** 而非一个）：

```python
async def _candidate_skills(db, *, user_id, task_input, prefer_skill_id, k=3):
    # prefer_skill_id 仍优先（显式 hint）→ 返回 [该 skill]
    # 否则：list_visible → 评分 → top-K；若全 0 分，返回 []（不强制 skill）
```

选中的候选注入 **system prompt** 作为菜单（非 user prompt）：

```
You may use one of these skills if it fits the task. Each skill restricts which
tools you may use. To adopt a skill, call agent.useSkill with its key. You may
also proceed without a skill (free planning), but then only read-only
exploration tools are available during planning.

Available skills:
- organizeByType (按类型整理): 按文件类型整理指定文件夹. tools: listFolder, getFileMeta, createFolder, moveFile
- dedupScan (去重扫描): 找出重复文件. tools: listFolder, getFileInfo, findDuplicates, deleteFile
- listAndSummarize (列出并摘要): 列出某文件夹内容. tools: listFolder, countFiles, getFileInfo
```

### `agent.useSkill` meta-tool

```python
REGISTRY.register(ToolSpec(
    name="agent.useSkill",
    description="Adopt a skill to constrain your tool set to that skill's whitelist. "
                "Call once during planning if a skill fits; optional. Returns the bound "
                "tool list. Cannot be used during execution.",
    input_schema=_schema({
        "skillKey": {"type": "string", "description": "One of the offered skill keys, or 'none' to decline."},
    }, required=["skillKey"]),
    side_effect="read",          # 无文件系统副作用，仅收窄权限
    risk_level="low",
    requires_confirmation=False,
    handler=_use_skill,
))
```

**Handler 行为**——这是关键点。`useSkill` 是 *meta-tool*：不碰文件系统，它变更 planner 的 `EffectivePermission`。故不能干净地走 `ToolRouter.dispatch` → `spec.handler(ctx, args)` 路径，因为它需要写回 runner 状态。两个选项：

**选项 4a（推荐）：在 planner 的 tool-executor 拦截。** `_planning_tool_executor` 已包裹每次工具调用。对 `agent.useSkill` 特殊处理：校验 key 是否在注入的候选列表中，重跑 `PermissionResolver.effective(..., skill=chosen)` 产出新 `EffectivePermission`，换入闭包（`nonlocal permission`），返回 `{bound: true, skillKey, allowedTools: [...]}` 给 LLM。LLM 随即知道收窄后的工具集。这把 `useSkill` 排除在通用 dispatch 路径外（它不是真正的 drive 工具），且变更局部于 planner。

**选项 4b：作为普通工具注册，handler 有副作用。** registry 故事更干净，但 handler 需要反向引用 runner 的可变 permission 状态——耦合丑陋，且 `useSkill` 会出现在 `REGISTRY.all()` 并泄漏进 execute 侧 schema。**否决**。

故：`agent.useSkill` **仅为 prompt/schema 生成注册**（让 LLM 看见），但其执行在 planner 拦截，**永不**到达 `ToolRouter`。它被**排除**出 `allowed_tools` 求交逻辑与 execute 侧 dispatch（execute 重放固定 plan；skill 已绑定并烤进 plan 的 `chosen_skill`）。

### Planning 期间流程

```
1. _candidate_skills → top-K（或 [preferred]）
2. permission = PermissionResolver.effective(request, setting, skill=None)  # 全 registry，只读探索
3. system prompt 含 skill 菜单 + useSkill 工具定义
4. LLM 二选一：
   a. 调 agent.useSkill("organizeByType")
      → planner 拦截 → permission := effective(..., skill=organizeByType)
      → 返回 {bound:true, allowedTools:[...]} 给 LLM
      → 后续工具调用受收窄后的 permission 约束
   b. 调 agent.useSkill("none") 或从不调
      → permission 保持全 registry（仅只读探索）
5. LLM 产出 proposedActions（仅限当前 allowed_tools 内工具）
6. plan 归一化：任何 action tool ∉ permission.allowed_tools → 422（纵深防御）
7. chosen_skill 记入 AgentPlan（现有字段）
```

### 向后兼容

- `hints.prefer_skill_id` 仍生效——若设置，候选 = `[该 skill]` 且自动绑定（无需 LLM 选择）。现有调用方/测试不受影响。
- 无 skill 匹配且 LLM 拒绝 → 自由规划 + 只读探索，同今天 `skill=None` 路径。
- `plan_template_json` / `inputs_schema_json` / `outputs_schema_json` 本轮**存而不执行**（模板执行是 Approach B，已否决）。仅作为 skill 描述的一部分给 LLM 作指引。

### 预置 builtin skills

预置 3 个（非设计文档全部 6 个——本轮 YAGNI）：`organizeByType`、`dedupScan`、`listAndSummarize`。以 DB 行预置（migration 或幂等启动 seed），`visibility=global`、`owner_user_id=NULL`。对应工具均已存在。

## 数据模型、设置与默认值接线

最小新 schema。关键变更是把 `AgentUserSetting` 默认值**接入** request 路径——表已有正确列，只是运行时从不读。

### 无新表

全部复用现有表：

- `AgentUserSetting`——已有 `default_execution_policy`、`default_data_policy_json`、`default_budget_tokens`、`default_max_steps`。**无 schema 变更**。
- `AgentSkill`——已有 `tool_whitelist_json`、`triggers_text` 等。**无 schema 变更**。
- `AgentPlan`——已有 `chosen_skill_id`。**无 schema 变更**。
- `AgentActionLog`——`status` 列为 `String(20)` 自由文本（已核对 [tables_agent.py:296](../../../app/src/fileflash/models/tables_agent.py)），新增 `"denied"` 状态值**无需 migration**。

### `AgentUserSetting` 默认值接线

今天 `PlanService.enqueue_plan` 校验 request 但从不加载 user setting。在 `PlanRunner._run` 早期（计算 permission 之前）加**默认值合并步骤**：

```python
setting = await SettingsService(db).get_for_user(user_id)   # 现有 service
request = _apply_setting_defaults(request, setting)

def _apply_setting_defaults(request, setting):
    # execution_policy: request 发默认哨兵值时用 setting 默认
    #   （但今天 request 总发值，主要为未来「省略」场景）
    # data_policy: request.data_policy 与 setting.default_data_policy_json 合并（取最严）
    # hints.budget_tokens: 若 == 默认(8000) 用 setting.default_budget_tokens
    # hints.max_steps: 同模式
    return request
```

**取最严合并**（同 §2）：`allow_file_content = req and setting`；`max_read_bytes = min`；`allowed_mime_types = 交集`。

即用户可在设置里设全局「永不允许读文件内容」，即便 request 说 `allow_file_content=true`，setting 仍胜（交集）。这是「完善的权限管理」——policy 在用户级执行，非仅 per-request。

### 新设置（env）

| Env | 默认 | 用途 |
|---|---|---|
| `AGENT_READ_FILE_MAX_BYTES` | `1048576`（1 MiB） | `readFile` 硬上限，无视 request `maxBytes`/`max_read_bytes` |
| `AGENT_SKILL_CANDIDATE_K` | `3` | 注入 prompt 的 top-K skill 数 |

无其他新配置。现有 `agent_job_max_tool_calls` 已约束 planning 工具调用。

### `EffectivePermission` 不持久化

每次运行从 (request, setting, skill) 计算并持有于 runner 内存。*结果*经 `AgentPlan.chosen_skill_id`（已有）与 `AgentActionLog.status="denied"` 行（新拒绝审计）持久化。permission 对象本身不新增持久化。

### `denied` 在 `AgentActionLog` 中的形态

execute 中 `PolicyGuard.evaluate` 拒绝时：

- `status = "denied"`
- `error_message = "; ".join(reasons)`
- `inputs_json = action.input`（尝试的 input，供审计）
- `outputs_json = {}`
- 发 `tool.failed` 事件，`data={reasons, denied: true}`，前端可区分「被 policy 拒」与「运行时错误」。

## 测试策略

遵循项目惯例：真 DB + 真 services，不 mock 业务逻辑。

**`PermissionResolver`（单元）**

- request policy 单独 → effective = request。
- request + setting → 取最严合并（setting `allow_file_content=false` 胜过 request `true`；`max_read_bytes` = min；mime 交集）。
- skill 白名单收窄 `allowed_tools`；无白名单 skill → 全 registry。
- mime 交集为空 → `deny_read_content` 实质 true，reason 记录。

**`PolicyGuard.evaluate`（单元）**

- 未知工具 → denied "unknown tool"。
- tool ∉ allowed_tools → denied "not permitted by skill"。
- `readFile` + `allow_file_content=false` → denied。
- `readFile` + mime ∉ allowed_mime_types → denied。
- `readFile` + `maxBytes > max_read_bytes` → denied。
- 高危无 `high_risk_confirmed` → denied。
- `planOnly` + phase=executing → denied。
- happy path：read 工具、白名单内、policy 允许 → allowed。

**`drive.readFile` handler（集成，真 DB + MinIO）**

- 文本文件 → 返回 content，truncated 标志正确。
- 二进制文件（图片）→ 返回 `{truncated:true, note}`，无原始字节。
- 他用户文件 → 404（不泄露存在性）。
- `offset`/`maxBytes` 切片正确。

**`agent.useSkill` 拦截（集成）**

- LLM 调 `useSkill("organizeByType")` → 后续 `moveFile` 允许，`deleteFile` 仅白名单含才允许。
- LLM 调 `useSkill("none")` → 全只读探索。
- `useSkill` 未知 key → 结构化错误给 LLM，planning 继续。
- execute 期间 `useSkill` → 不可达（不在 execute 工具集）；断言其被排除。
- `prefer_skill_id` 设置 → 自动绑定，无需 `useSkill`；现有测试通过。

**端到端（扩展现有测试套件）**

- `test_agent_plan_execute_runtime.py`：`allow_file_content=true` 下用 `readFile` 的 plan 成功；`false` 下 action 在 execute 被拒，job 报告之。
- `test_agent_routes.py`：`data_policy.allow_file_content=true` 的 plan request 流通；setting 默认 `false` 覆盖之。
- 有候选时 plan 输出含 skill 菜单；`chosen_skill` 反映 LLM 的 `useSkill` 选择。

**回归**

- 所有现有 agent 测试不变通过（`prefer_skill_id` 路径与无 skill 路径保留）。
- `policy.py` 重写：现有风险分类测试仍通过，因 `classify_tool_risk`/`classify_tool_side_effect` 保留（现支撑 `EffectivePermission` 计算）。

## 滚动出场

单 PR，**零 schema migration**（`AgentActionLog.status` 已核对为 `String(20)` 自由文本，加 `"denied"` 值无需 migration；见「数据模型」节）。可能附一个 seed migration 预置 3 个 builtin skill 行（或改用幂等启动 seed，二选一，实现期定）。无 feature flag——agent 子系统无第三方 API 消费者（见前序 spec 兼容性说明），且 request 级向后兼容（新 `dataPolicy` 字段已安全默认；`useSkill` 是叠加）。

PR 内顺序：

1. `PermissionResolver` + 拓宽的 `PolicyGuard`（暂无行为变更——planner 仍可经薄 adapter 调旧签名，或一步切两个调用点）。
2. `drive.readFile` 工具 + 内容门控。
3. `agent.useSkill` 拦截 + skill 菜单注入。
4. `AgentUserSetting` 默认值接线。
5. 各自测试。

## 非目标（本轮）

- **不做 `writeFile`**——仅 readFile。
- **不做 OCR / 图片 / 音频内容分析**——二进制守卫仅返回元数据。
- **不做 skill `plan_template_json` 执行**——模板保持信息性；LLM 得之作指引，runner 不模板化执行。
- **不做 per-user 工具允许/拒绝表 / RBAC / 角色驱动策略**——选了三轴求交模型；per-user 粒度仅经 `AgentUserSetting` dataPolicy 默认。
- **不做 per-skill 风险覆盖。**
- **不做 MCP 工具注册进 runtime**——`AgentMcpServer` 保持仅 CRUD（同今天）。
- **不做 memory 注入 prompt**——`harness/memory.py` 保持 scaffold。
- **不做 subagent runner**——`subagent_runner.py` 保持 scaffold。
- **不做 staging/commit/rollback**——写仍直接打真实 folder（现有行为）。
- **不做 budget/cost/checkpoint**——那些 harness scaffold 保持未建。
- **不做 BM25→embedding skill 检索**——保留现有 keyword 评分，仅返回 top-K。

## 风险

- **`useSkill` 循环中变更**：LLM 看过完整菜单后收窄 `allowed_tools` 是安全的（交集只缩不放），但 LLM 可能在绑定前调用它*以为*允许的工具。planner 的逐调用 `PolicyGuard.evaluate(phase="planning")` 捕获之并返回结构化 blocked 结果——LLM 反应。显式测试。
- **`readFile` 成本/延迟**：1 MiB 读进 LLM context 昂贵。由 `max_read_bytes` 默认 1 MiB、per-call `maxBytes` 默认 256 KiB、二进制守卫缓解。无流式。
- **`AgentActionLog.status` enum**：已核对为 `String(20)` 自由文本，加 `denied` 无需 migration。

## 跨文件影响矩阵

| 文件 / 模块 | 改动 |
|---|---|
| `agents/harness/permission.py` | 新：`PermissionResolver` + `EffectivePermission` |
| `agents/harness/policy.py` | 重写：`PolicyGuard.evaluate` 拓宽为接 `EffectivePermission` + phase；保留 `classify_tool_*` |
| `agents/harness/skill_tool.py` | 新：`agent.useSkill` meta-tool 注册 + 拦截逻辑 |
| `agents/tools/drive.py` | + `drive.readFile` 工具 + handler；`ToolContext` 增 `storage_reader` |
| `agents/harness/tool_registry.py` | `ToolContext` 增 `storage_reader: MinioObjectStorageClient` 字段 |
| `agents/runtime/plan_runner.py` | `_choose_skill` → `_candidate_skills`(top-K)；`_planning_tool_executor` 委托 `PolicyGuard` + 拦截 `useSkill`；接 `AgentUserSetting` 默认 |
| `agents/runtime/execute_runner.py` | per-step `PolicyGuard.evaluate(phase="executing")`；denied 写 `ActionLog` + `tool.failed` |
| `services/agent/plan_service.py` | （可选）早期加载 `AgentUserSetting` 传 runner |
| `core/settings.py` | + `AGENT_READ_FILE_MAX_BYTES`、`AGENT_SKILL_CANDIDATE_K` |
| `docker/flyway/migrations/` | 预置 3 个 builtin skill 的 seed migration（若不用启动 seed） |
| `app/tests/test_agent_plan_execute_runtime.py` | 扩展 readFile/dataPolicy/useSkill 用例 |
| `app/tests/test_agent_routes.py` | 扩展 dataPolicy 流通 + setting 覆盖用例 |

## 兼容与迁移

- **后端 API**：不要求向后兼容——agent 子系统无公开第三方 API 消费者。`dataPolicy` 字段已存在且安全默认；`useSkill` 是叠加。
- **数据库迁移**：**零 schema migration**（`AgentActionLog.status` 为 `String(20)`）。仅可能一个 seed migration 预置 3 个 builtin skill 行。
- **配置项**：新增 `AGENT_READ_FILE_MAX_BYTES`（默认 1048576）、`AGENT_SKILL_CANDIDATE_K`（默认 3）。
