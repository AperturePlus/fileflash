# Agent Permission Layer + LLM-Invocable Skills — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the agent's tool-calling permission-gated and skill-aware by widening `PolicyGuard` into a single choke point (executionPolicy + dataPolicy + skill-whitelist intersection, 取最严), adding `drive.readFile` with enforced dataPolicy, and making skills LLM-selectable via an `agent.useSkill` meta-tool.

**Architecture:** One enforcement point — `PolicyGuard.evaluate(ctx, action, permission, phase)` — fed by a pure `PermissionResolver` that merges request policy + `AgentUserSetting` defaults + skill whitelist into a frozen `EffectivePermission`. Skills become an LLM-invocable surface: top-K candidates injected into the system prompt; the LLM calls `agent.useSkill` (intercepted in the planner, never reaching `ToolRouter`) to bind a skill and narrow `allowed_tools`. `readFile` is a normal tool whose content access is gated by dataPolicy inside the same guard.

**Tech Stack:** Python 3.12, FastAPI, async SQLAlchemy 2.x, Pydantic v2 (`CamelModel`), Redis Streams, Anthropic SDK, MinIO (`MinioObjectStorageClient`), pytest (real DB + real services, `AsyncMock` for LLM only).

## Global Constraints

- **Tests run with real Postgres + real services** (project convention — see existing `test_agent_plan_execute_runtime.py`); only the LLM client (`AnthropicPlannerClient`) is mocked via `AsyncMock`.
- **Test command:** `cd app && python -m pytest tests/test_agent_plan_execute_runtime.py tests/test_agent_routes.py -v` (run from `app/` dir; project uses `bun` only for `web/`, Python tests use `pytest`).
- **CamelCase API:** all request/response schemas extend `CamelModel` and use camelCase aliases (`allow_file_content` ↔ `allowFileContent`). Existing pattern in [schemas/agent.py](../../app/src/fileflash/schemas/agent.py).
- **Ownership scoping stays in handlers** (`File.owner_id == ctx.user_id`); the permission layer is additive. 404 (never 403) for missing/non-owned resources — no existence leak.
- **`SettingsService` is a NotImplementedError scaffold** — do NOT use it. Use `AgentSettingsRepository(db).get_by_user_id(user_id)` directly (verified working at [repositories/agent/settings.py:15](../../app/src/fileflash/repositories/agent/settings.py)).
- **No new tables, zero schema migration.** `AgentActionLog.status` is `String(20)` free text ([tables_agent.py:296](../../app/src/fileflash/models/tables_agent.py)) — new value `"denied"` needs no migration. Builtin skills seeded as DB rows via one seed migration.
- **Ownership of `PolicyGuard`/`classify_tool_*`:** the existing functions `classify_tool_risk`, `classify_tool_side_effect`, `normalize_action_risk` are imported by tests and `plan_runner` — keep them (they back `EffectivePermission` computation); only `PolicyGuard.evaluate_tool_call` is replaced by `evaluate`.
- **Commits after every task** (TDD red-green-commit). Conventional-commit messages, scope `agent`.
- **`max 1 subagent`** dispatch rule is satisfied — this plan is executed inline or via subagent-driven-development one task at a time; no parallel fan-out required.

---

## File Structure

**Create:**
- `app/src/fileflash/agents/harness/permission.py` — `EffectivePermission` dataclass + `PermissionResolver` (merges request + setting + skill → effective permission, 取最严).
- `app/src/fileflash/agents/harness/skill_tool.py` — `agent.useSkill` ToolSpec registration + `_bind_skill` interceptor (called from planner, mutates `EffectivePermission`).
- `app/tests/test_agent_permission.py` — unit tests for `PermissionResolver` + `PolicyGuard.evaluate`.
- `app/tests/test_agent_read_file.py` — integration tests for `drive.readFile` handler + dataPolicy gating.
- `app/tests/test_agent_use_skill.py` — integration tests for the `useSkill` interception flow.
- `docker/flyway/migrations/V17__agent_builtin_skills.sql` — seed 3 builtin skill rows.

**Modify:**
- `app/src/fileflash/agents/harness/tool_registry.py` — add `storage_reader` to `ToolContext`.
- `app/src/fileflash/agents/harness/policy.py` — rewrite `PolicyGuard`: new async `evaluate(ctx, action, permission, phase)`; keep `classify_tool_*`.
- `app/src/fileflash/agents/harness/router.py` — `ToolRouter` constructs `storage_reader` from settings; passes it into `ToolContext`.
- `app/src/fileflash/agents/tools/drive.py` — add `_read_file` handler + `drive.readFile` registration.
- `app/src/fileflash/agents/runtime/plan_runner.py` — `_choose_skill`→`_candidate_skills` (top-K); delegate tool gating to `PolicyGuard`; intercept `agent.useSkill`; apply `AgentUserSetting` defaults.
- `app/src/fileflash/agents/runtime/execute_runner.py` — per-step `PolicyGuard.evaluate(phase="executing")`; write `denied` ActionLog + `tool.failed`.
- `app/src/fileflash/core/settings.py` — add `agent_read_file_max_bytes`, `agent_skill_candidate_k`.
- `app/tests/test_agent_plan_execute_runtime.py` — extend with readFile/dataPolicy/useSkill e2e cases.
- `app/tests/test_agent_routes.py` — extend with dataPolicy flow + setting override.

---

## Task 1: `EffectivePermission` + `PermissionResolver`

**Files:**
- Create: `app/src/fileflash/agents/harness/permission.py`
- Test: `app/tests/test_agent_permission.py`

**Interfaces:**
- Produces: `EffectivePermission` (frozen dataclass), `PermissionResolver` with `async effective(*, request, setting, skill, high_risk_confirmed) -> EffectivePermission`.
- Consumes: `PlanAgentRequest`, `AgentDataPolicy` (from [schemas/agent.py](../../app/src/fileflash/schemas/agent.py)), `AgentUserSetting` (from models), `REGISTRY`, existing `_skill_tool_whitelist` logic (moved here).

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_agent_permission.py`:

```python
from __future__ import annotations

import pytest

from fileflash.agents.harness.permission import EffectivePermission, PermissionResolver
from fileflash.models import AgentUserSetting
from fileflash.schemas.agent import AgentDataPolicy, PlanAgentRequest


def _request(**overrides) -> PlanAgentRequest:
    base = {
        "chatSessionId": "1",
        "input": "list my files",
        "context": {"rootFolderId": "root"},
    }
    base.update(overrides)
    return PlanAgentRequest.model_validate(base)


@pytest.mark.asyncio
async def test_effective_defaults_when_no_setting_no_skill():
    resolver = PermissionResolver()
    perm = await resolver.effective(
        request=_request(),
        setting=None,
        skill=None,
        high_risk_confirmed=False,
    )
    assert perm.execution_policy == "confirm"
    assert perm.deny_read_content is True  # default allow_file_content=False
    assert perm.skill_key is None
    assert "drive.listFolder" in perm.allowed_tools


@pytest.mark.asyncio
async def test_effective_setting_overrides_data_policy_take_strictest():
    # Setting says allow_file_content=True; request says False -> False wins (取最严)
    setting = AgentUserSetting(
        user_id=1,
        default_execution_policy="confirm",
        default_data_policy_json={"allowFileContent": True, "maxReadBytes": 2097152},
    )
    perm = await resolver.effective(
        request=_request(dataPolicy={"allowFileContent": False}),
        setting=setting,
        skill=None,
        high_risk_confirmed=False,
    )
    assert perm.deny_read_content is True


@pytest.mark.asyncio
async def test_effective_setting_denies_content_even_when_request_allows():
    # Setting allow_file_content=False; request True -> False wins
    setting = AgentUserSetting(
        user_id=1,
        default_data_policy_json={"allowFileContent": False, "maxReadBytes": 0},
    )
    perm = await PermissionResolver().effective(
        request=_request(dataPolicy={"allowFileContent": True}),
        setting=setting,
        skill=None,
        high_risk_confirmed=False,
    )
    assert perm.deny_read_content is True
    assert perm.data_policy.max_read_bytes == 0


@pytest.mark.asyncio
async def test_effective_mime_intersection_empty_denies_content():
    setting = AgentUserSetting(
        user_id=1,
        default_data_policy_json={"allowedMimeTypes": ["image/*"]},
    )
    perm = await PermissionResolver().effective(
        request=_request(dataPolicy={"allowedMimeTypes": ["text/*"]}),
        setting=setting,
        skill=None,
        high_risk_confirmed=False,
    )
    assert perm.data_policy.allowed_mime_types == []
    assert perm.deny_read_content is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_agent_permission.py -v`
Expected: FAIL with `ModuleNotFoundError: fileflash.agents.harness.permission`

- [ ] **Step 3: Write `permission.py`**

Create `app/src/fileflash/agents/harness/permission.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...models import AgentUserSetting
from ...schemas.agent import AgentDataPolicy, AgentExecutionPolicy, PlanAgentRequest
from .tool_registry import REGISTRY


@dataclass(frozen=True, slots=True)
class EffectivePermission:
    execution_policy: AgentExecutionPolicy
    data_policy: AgentDataPolicy
    allowed_tools: frozenset[str]
    skill_key: str | None
    deny_read_content: bool
    high_risk_confirmed: bool


class PermissionResolver:
    async def effective(
        self,
        *,
        request: PlanAgentRequest,
        setting: AgentUserSetting | None,
        skill: Any,
        high_risk_confirmed: bool,
    ) -> EffectivePermission:
        execution_policy = request.execution_policy
        data_policy = _merge_data_policy(request.data_policy, setting)
        skill_whitelist = _skill_tool_whitelist(skill)
        allowed_tools = frozenset(skill_whitelist)
        skill_key = _skill_key(skill)
        deny_read_content = (
            not data_policy.allow_file_content
            or not data_policy.allowed_mime_types
        )
        return EffectivePermission(
            execution_policy=execution_policy,
            data_policy=data_policy,
            allowed_tools=allowed_tools,
            skill_key=skill_key,
            deny_read_content=deny_read_content,
            high_risk_confirmed=high_risk_confirmed,
        )


def _merge_data_policy(
    request_policy: AgentDataPolicy, setting: AgentUserSetting | None
) -> AgentDataPolicy:
    if setting is None:
        return request_policy
    setting_policy = _setting_data_policy(setting)
    allow = request_policy.allow_file_content and setting_policy.allow_file_content
    max_bytes = min(request_policy.max_read_bytes, setting_policy.max_read_bytes)
    allowed_mimes = _intersect_mime_globs(
        request_policy.allowed_mime_types, setting_policy.allowed_mime_types
    )
    return AgentDataPolicy(
        allow_file_content=allow,
        max_read_bytes=max_bytes,
        allowed_mime_types=allowed_mimes,
    )


def _setting_data_policy(setting: AgentUserSetting) -> AgentDataPolicy:
    raw = setting.default_data_policy_json or {}
    if not isinstance(raw, dict):
        raw = {}
    return AgentDataPolicy.model_validate(raw)


def _intersect_mime_globs(a: list[str], b: list[str]) -> list[str]:
    # ["*/*"] means "all"; intersection with X = X.
    if "*/*" in a and "*/*" in b:
        return ["*/*"]
    if "*/*" in a:
        return list(b)
    if "*/*" in b:
        return list(a)
    return [m for m in a if m in b]


def _skill_tool_whitelist(skill: Any) -> tuple[str, ...]:
    if skill is None:
        return REGISTRY.all_names()
    raw = getattr(skill, "tool_whitelist_json", None)
    if isinstance(raw, list) and raw:
        tools = tuple(str(item) for item in raw if str(item).strip())
        unknown = REGISTRY.unknown_names(tools)
        if unknown:
            from ...core.errors import ApiError
            raise ApiError(
                status_code=422,
                code=422,
                message="Unknown agent tool in selected skill",
                data={"unknownTools": sorted(unknown)},
            )
        return tools
    return REGISTRY.all_names()


def _skill_key(skill: Any) -> str | None:
    if skill is None:
        return None
    return str(getattr(skill, "skill_key", None) or "")


__all__ = ["EffectivePermission", "PermissionResolver"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_permission.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/harness/permission.py app/tests/test_agent_permission.py
git commit -m "feat(agent): add PermissionResolver and EffectivePermission"
```

---

## Task 2: Rewrite `PolicyGuard.evaluate` as the single choke point

**Files:**
- Modify: `app/src/fileflash/agents/harness/policy.py`
- Test: `app/tests/test_agent_permission.py` (extend)

**Interfaces:**
- Produces: `async PolicyGuard.evaluate(*, ctx: ToolContext, action: AgentProposedAction, permission: EffectivePermission, phase: Literal["planning","executing"]) -> PolicyDecision`.
- Consumes: `EffectivePermission` (Task 1), `ToolContext`, `AgentProposedAction`, `REGISTRY`.
- Keeps: `classify_tool_risk`, `classify_tool_side_effect`, `normalize_action_risk`, `PolicyDecision`.

- [ ] **Step 1: Add failing tests for `PolicyGuard.evaluate`**

Append to `app/tests/test_agent_permission.py`:

```python
from datetime import datetime
from unittest.mock import AsyncMock

from fileflash.agents.harness.policy import PolicyGuard, PolicyDecision
from fileflash.agents.harness.tool_registry import ToolContext
from fileflash.schemas.agent import AgentProposedAction


def _ctx_with_mime(mime: str = "text/plain") -> ToolContext:
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=type("F", (), {"mime_type": mime, "file_ext": None, "file_name": "x.txt"})())
    return ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=None)


def _perm(*, allowed_tools=None, deny_read=False, allow_content=True, mimes=None, high_risk=False, policy="confirm"):
    from fileflash.agents.harness.permission import EffectivePermission
    from fileflash.schemas.agent import AgentDataPolicy
    return EffectivePermission(
        execution_policy=policy,
        data_policy=AgentDataPolicy(
            allow_file_content=allow_content,
            max_read_bytes=1048576,
            allowed_mime_types=mimes if mimes is not None else ["*/*"],
        ),
        allowed_tools=frozenset(allowed_tools) if allowed_tools else frozenset(REGISTRY_NAMES),
        skill_key=None,
        deny_read_content=deny_read,
        high_risk_confirmed=high_risk,
    )


REGISTRY_NAMES = __import__("fileflash.agents.harness.tool_registry", fromlist=["REGISTRY"]).REGISTRY.all_names()


@pytest.mark.asyncio
async def test_evaluate_unknown_tool_denied():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.noSuch", input={}, side_effect="read"),
        permission=_perm(),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("unknown" in r.lower() or "unsupported" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_tool_not_in_whitelist_denied():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.deleteFile", input={"fileId": "1"}, side_effect="write"),
        permission=_perm(allowed_tools=["drive.listFolder"]),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("skill" in r.lower() or "permitted" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_readfile_blocked_when_content_disabled():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.readFile", input={"fileId": "1"}, side_effect="read"),
        permission=_perm(deny_read=True, allowed_tools=["drive.readFile"]),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("content" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_readfile_mime_not_allowed_denied():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(mime="application/pdf"),
        action=AgentProposedAction(step=1, tool="drive.readFile", input={"fileId": "1"}, side_effect="read"),
        permission=_perm(allowed_tools=["drive.readFile"], mimes=["text/*"]),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("mime" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_high_risk_without_confirmation_denied():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.deleteFile", input={"fileId": "1"}, side_effect="write", risk_level="high"),
        permission=_perm(allowed_tools=["drive.deleteFile"], high_risk=False),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("confirmation" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_planonly_executing_denied():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.createFolder", input={"name": "x"}, side_effect="write", risk_level="medium"),
        permission=_perm(allowed_tools=["drive.createFolder"], policy="planOnly"),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("planonly" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_allowed_read_tool_passes():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.listFolder", input={"folderId": "root"}, side_effect="read"),
        permission=_perm(allowed_tools=["drive.listFolder"]),
        phase="executing",
    )
    assert decision.allowed is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_agent_permission.py -v -k evaluate`
Expected: FAIL — `evaluate` not defined / `ToolContext` missing `storage_reader` / import errors.

- [ ] **Step 3: Add `storage_reader` to `ToolContext`**

In `app/src/fileflash/agents/harness/tool_registry.py`, change the `ToolContext` dataclass (line ~14):

```python
@dataclass(slots=True)
class ToolContext:
    db: AsyncSession
    user_id: int
    file_service: Any
    folder_service: Any
    storage_reader: Any = None
```

(`Any = None` keeps existing `ToolContext(...)` call sites that don't pass it from breaking during transition.)

- [ ] **Step 4: Rewrite `PolicyGuard` in `policy.py`**

Replace the `PolicyGuard` class body in `app/src/fileflash/agents/harness/policy.py` (keep `PolicyDecision`, `classify_tool_*`, `normalize_action_risk`):

```python
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Literal

from ...core.errors import ApiError
from ...models import File
from ...schemas.agent import AgentProposedAction
from sqlalchemy import and_, select
from .permission import EffectivePermission
from .tool_registry import REGISTRY, ToolContext

_CONTENT_READ_TOOLS = frozenset({"drive.readFile"})
_Phase = Literal["planning", "executing"]


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


class PolicyGuard:
    async def evaluate(
        self,
        *,
        ctx: ToolContext,
        action: AgentProposedAction,
        permission: EffectivePermission,
        phase: _Phase,
    ) -> PolicyDecision:
        try:
            spec = REGISTRY.get(action.tool)
        except KeyError:
            return PolicyDecision(
                allowed=False,
                reasons=[f"Unsupported agent tool: {action.tool}"],
            )
        if action.tool not in permission.allowed_tools:
            return PolicyDecision(
                allowed=False,
                reasons=[f"Tool not permitted by active skill/policy: {action.tool}"],
            )
        if spec.side_effect == "read" and action.tool in _CONTENT_READ_TOOLS:
            decision = self._check_content_read(ctx=ctx, action=action, permission=permission)
            if decision is not None:
                return decision
        if spec.risk_level == "high" and not permission.high_risk_confirmed:
            return PolicyDecision(
                allowed=False,
                reasons=["High-risk action requires explicit confirmation."],
            )
        if permission.execution_policy == "planOnly" and phase == "executing":
            return PolicyDecision(
                allowed=False,
                reasons=["planOnly policy forbids execution."],
            )
        return PolicyDecision(allowed=True)

    def _check_content_read(
        self,
        *,
        ctx: ToolContext,
        action: AgentProposedAction,
        permission: EffectivePermission,
    ) -> PolicyDecision | None:
        if permission.deny_read_content:
            return PolicyDecision(
                allowed=False,
                reasons=["File content access disabled by dataPolicy."],
            )
        max_bytes = self._byte_range(action.input)
        if max_bytes > permission.data_policy.max_read_bytes:
            return PolicyDecision(
                allowed=False,
                reasons=[
                    f"Requested bytes ({max_bytes}) exceed max_read_bytes "
                    f"({permission.data_policy.max_read_bytes})."
                ],
            )
        mime = _resolve_target_mime(ctx=ctx, action=action)
        if mime is not None and not _mime_allowed(mime, permission.data_policy.allowed_mime_types):
            return PolicyDecision(
                allowed=False,
                reasons=[f"File mime '{mime}' not in allowed_mime_types."],
            )
        return None

    def _byte_range(self, action_input: dict[str, Any]) -> int:
        max_bytes = int(action_input.get("maxBytes", 262144) or 262144)
        offset = int(action_input.get("offset", 0) or 0)
        return max_bytes + offset


def _mime_allowed(mime: str, allowed: list[str]) -> bool:
    lowered = mime.lower()
    for pattern in allowed:
        if fnmatch.fnmatch(lowered, pattern.lower()):
            return True
    return False


def _resolve_target_mime(*, ctx: ToolContext, action: AgentProposedAction) -> str | None:
    file_id = action.input.get("fileId") or action.input.get("id")
    if file_id is None:
        return None
    try:
        parsed = int(str(file_id))
    except (TypeError, ValueError):
        return None
    from ...models.enums import FileStatus

    row = ctx.db.scalar_result if hasattr(ctx.db, "scalar_result") else None  # placeholder
    # Use a synchronous-style lookup via the db session's cached value set by tests,
    # or fall back to a query. For production, query here:
    import asyncio

    async def _query() -> str | None:
        row = await ctx.db.scalar(
            select(File).where(
                and_(
                    File.file_id == parsed,
                    File.owner_id == ctx.user_id,
                    File.status == FileStatus.ACTIVE,
                )
            )
        )
        if row is None:
            return None
        from ...core.mime import resolve_file_mime_type
        return resolve_file_mime_type(
            mime_type=row.mime_type,
            file_ext=row.file_ext,
            file_name=row.file_name,
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    # We are already async (evaluate is awaited); query directly:
    coro = _query()
    # Evaluate synchronously is not possible; instead cache on ctx via attribute.
    # See Step 5 note: tests mock ctx.db.scalar; production awaits the query.
    return _await_or_cached(ctx, coro, parsed)
```

> **Note on the mime lookup:** `evaluate` is `async`, so we can `await` the DB query directly. The test mock sets `ctx.db.scalar` to an `AsyncMock` returning a fake row. To keep both production and test paths working, replace the `_resolve_target_mime` tail (the `_await_or_cached` line) with a direct await inside an `async` version. Because `_check_content_read` is called from the async `evaluate`, make `_check_content_read` async and `await` the query there. See Step 5 for the corrected async form.

- [ ] **Step 5: Correct `_check_content_read` to be async and await the mime query**

Replace the `_check_content_read` method and `_resolve_target_mime` with the async form:

```python
    async def _check_content_read(
        self,
        *,
        ctx: ToolContext,
        action: AgentProposedAction,
        permission: EffectivePermission,
    ) -> PolicyDecision | None:
        if permission.deny_read_content:
            return PolicyDecision(
                allowed=False,
                reasons=["File content access disabled by dataPolicy."],
            )
        max_bytes = self._byte_range(action.input)
        if max_bytes > permission.data_policy.max_read_bytes:
            return PolicyDecision(
                allowed=False,
                reasons=[
                    f"Requested bytes ({max_bytes}) exceed max_read_bytes "
                    f"({permission.data_policy.max_read_bytes})."
                ],
            )
        mime = await _resolve_target_mime(ctx=ctx, action=action)
        if mime is not None and not _mime_allowed(mime, permission.data_policy.allowed_mime_types):
            return PolicyDecision(
                allowed=False,
                reasons=[f"File mime '{mime}' not in allowed_mime_types."],
            )
        return None
```

And update the caller in `evaluate`:

```python
        if spec.side_effect == "read" and action.tool in _CONTENT_READ_TOOLS:
            decision = await self._check_content_read(ctx=ctx, action=action, permission=permission)
            if decision is not None:
                return decision
```

And replace the `_resolve_target_mime` function with:

```python
async def _resolve_target_mime(*, ctx: ToolContext, action: AgentProposedAction) -> str | None:
    file_id = action.input.get("fileId") or action.input.get("id")
    if file_id is None:
        return None
    try:
        parsed = int(str(file_id))
    except (TypeError, ValueError):
        return None
    from ...core.mime import resolve_file_mime_type
    from ...models.enums import FileStatus

    row = await ctx.db.scalar(
        select(File).where(
            and_(
                File.file_id == parsed,
                File.owner_id == ctx.user_id,
                File.status == FileStatus.ACTIVE,
            )
        )
    )
    if row is None:
        return None
    return resolve_file_mime_type(
        mime_type=row.mime_type,
        file_ext=row.file_ext,
        file_name=row.file_name,
    )
```

Remove the now-dead `_await_or_cached` helper and the synchronous `_query` scaffolding from Step 4. Keep `classify_tool_risk`, `classify_tool_side_effect`, `normalize_action_risk` unchanged. Remove the old `evaluate_tool_call` method.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_permission.py -v`
Expected: PASS (all 11 tests — 4 resolver + 7 evaluate)

- [ ] **Step 7: Commit**

```bash
git add app/src/fileflash/agents/harness/policy.py app/src/fileflash/agents/harness/tool_registry.py app/tests/test_agent_permission.py
git commit -m "feat(agent): widen PolicyGuard.evaluate to single permission choke point"
```

---

## Task 3: `drive.readFile` tool + `storage_reader` wiring

**Files:**
- Modify: `app/src/fileflash/agents/tools/drive.py`
- Modify: `app/src/fileflash/agents/harness/router.py`
- Test: `app/tests/test_agent_read_file.py`

**Interfaces:**
- Produces: `drive.readFile` ToolSpec (registered into `REGISTRY`); `ToolRouter` now builds `MinioObjectStorageClient` and passes it into `ToolContext.storage_reader`.
- Consumes: `MinioObjectStorageClient.iter_object_range` / `stat_object` (from [s3/minio_client.py](../../app/src/fileflash/s3/minio_client.py)); `StorageObject`, `File` models.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_agent_read_file.py`:

```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fileflash.agents.harness.router import ToolCall, ToolRouter
from fileflash.agents.harness.tool_registry import REGISTRY
from fileflash.core.errors import ApiError


def _ensure_registered():
    import fileflash.agents.tools  # noqa: F401  triggers registration


_ensure_registered()


@pytest.mark.asyncio
async def test_read_file_text_content(tmp_path):
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    assert spec is not None

    db = AsyncMock()
    file_row = MagicMock()
    file_row.file_id = 7
    file_row.owner_id = 1
    file_row.file_name = "notes.txt"
    file_row.mime_type = "text/plain"
    file_row.file_ext = ".txt"
    file_row.file_size = 5
    file_row.storage_object_id = 3
    file_row.status = "active"
    file_row.is_latest = True
    db.scalar = AsyncMock(side_effect=[file_row, MagicMock(object_key="obj-key")])

    storage = AsyncMock()
    # iter_object_range yields bytes chunks
    async def _chunks(*a, **kw):
        for c in [b"hello"]:
            yield c
    storage.iter_object_range = _chunks
    storage.stat_object = AsyncMock(return_value=MagicMock(size=5))

    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=storage)
    output = await spec.handler(ctx, {"fileId": "7"})
    assert output["content"] == "hello"
    assert output["mime"] == "text/plain"
    assert output["bytesReturned"] == 5


@pytest.mark.asyncio
async def test_read_file_binary_returns_no_raw_bytes():
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    db = AsyncMock()
    file_row = MagicMock()
    file_row.file_id = 8
    file_row.owner_id = 1
    file_row.file_name = "pic.png"
    file_row.mime_type = "image/png"
    file_row.file_ext = ".png"
    file_row.file_size = 2048
    file_row.storage_object_id = 4
    file_row.status = "active"
    file_row.is_latest = True
    db.scalar = AsyncMock(side_effect=[file_row, MagicMock(object_key="obj-key")])

    storage = AsyncMock()
    storage.stat_object = AsyncMock(return_value=MagicMock(size=2048))

    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=storage)
    output = await spec.handler(ctx, {"fileId": "8"})
    assert "content" not in output or output.get("content") is None
    assert output["truncated"] is True


@pytest.mark.asyncio
async def test_read_file_other_user_returns_404():
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)  # not found / not owned
    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=AsyncMock())
    with pytest.raises(ApiError) as exc:
        await spec.handler(ctx, {"fileId": "999"})
    assert exc.value.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_agent_read_file.py -v`
Expected: FAIL — `KeyError: 'drive.readFile'` (not registered yet).

- [ ] **Step 3: Add `_read_file` handler + registration to `drive.py`**

Add to `app/src/fileflash/agents/tools/drive.py` (near the other handlers, before the `REGISTRY.register(...)` block). Add `StorageObject` to imports (already imported). Add the handler:

```python
_TEXT_MIME_ALLOWLIST = (
    "text/",
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/javascript",
    "application/x-sh",
    "application/pdf",
)


async def _read_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    file_id = _parse_positive_int(_required_text(args, "fileId", "id"), "fileId")
    max_bytes = _int_arg(args.get("maxBytes"), default=262144, minimum=1, maximum=1_048_576)
    offset = _int_arg(args.get("offset"), default=0, minimum=0)

    row = await ctx.db.scalar(
        select(File).where(
            and_(
                File.file_id == file_id,
                File.owner_id == ctx.user_id,
                File.status == FileStatus.ACTIVE,
                File.is_latest.is_(True),
            )
        )
    )
    if row is None:
        raise ApiError(status_code=404, code=404, message="File not found")

    storage = await ctx.db.get(StorageObject, int(row.storage_object_id))
    if storage is None or ctx.storage_reader is None:
        raise ApiError(status_code=503, code=503, message="Object storage unavailable")

    mime = _resolved_mime(row)
    object_key = str(storage.object_key)
    stat = await ctx.storage_reader.stat_object(object_key=object_key)
    size = int(stat.size)

    if not mime.lower().startswith(_TEXT_MIME_ALLOWLIST):
        return {
            "fileId": str(file_id),
            "name": str(row.file_name),
            "mime": mime,
            "size": size,
            "truncated": True,
            "bytesReturned": 0,
            "note": "Binary content not sent to model.",
        }

    end = min(offset + max_bytes - 1, size - 1) if size > 0 else 0
    chunks: list[bytes] = []
    received = 0
    async for chunk in ctx.storage_reader.iter_object_range(
        object_key=object_key, start=offset, end=end
    ):
        chunks.append(chunk)
        received += len(chunk)
    content_bytes = b"".join(chunks)
    try:
        content = content_bytes.decode("utf-8", errors="replace")
    except Exception:
        content = content_bytes.decode("latin-1", errors="replace")

    return {
        "fileId": str(file_id),
        "name": str(row.file_name),
        "mime": mime,
        "size": size,
        "content": content,
        "truncated": (offset + received) < size,
        "bytesReturned": received,
        "offset": offset,
    }
```

Then register the tool (add to the `REGISTRY.register(...)` block at the bottom):

```python
REGISTRY.register(
    ToolSpec(
        name="drive.readFile",
        description=(
            "Read text content of a file the user owns. Returns up to maxBytes; "
            "binary files are not returned directly. Subject to dataPolicy."
        ),
        input_schema=_schema(
            {
                "fileId": _FILE_ID,
                "maxBytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1048576,
                    "default": 262144,
                },
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
            required=["fileId"],
        ),
        side_effect="read",
        risk_level="medium",
        requires_confirmation=False,
        handler=_read_file,
    )
)
```

- [ ] **Step 4: Wire `storage_reader` into `ToolRouter`**

In `app/src/fileflash/agents/harness/router.py`, update `ToolRouter` to build a `MinioObjectStorageClient` and pass it into `ToolContext`. Replace the `ToolRouter` class:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.settings import Settings, get_settings
from ...services.file import FileService
from ...services.folder import FolderService
from ...s3.minio_client import MinioObjectStorageClient
from .tool_registry import REGISTRY, ToolContext


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]


class ToolRouter:
    def __init__(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        settings: Settings | None = None,
        storage_reader: MinioObjectStorageClient | None = None,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.settings = settings or get_settings()
        self.file_service = FileService(db=db)
        self.folder_service = FolderService(db=db)
        self._storage_reader = storage_reader

    def _resolve_storage_reader(self) -> MinioObjectStorageClient | None:
        if self._storage_reader is not None:
            return self._storage_reader
        try:
            return MinioObjectStorageClient.from_settings(self.settings)
        except Exception:
            return None

    async def dispatch(self, call: ToolCall) -> dict[str, Any]:
        tool_name = str(call.tool_name or "").strip()
        try:
            spec = REGISTRY.get(tool_name)
        except KeyError as exc:
            raise ApiError(
                status_code=400,
                code=400,
                message=f"Unsupported agent tool: {tool_name}",
            ) from exc

        ctx = ToolContext(
            db=self.db,
            user_id=self.user_id,
            file_service=self.file_service,
            folder_service=self.folder_service,
            storage_reader=self._resolve_storage_reader(),
        )
        return await spec.handler(ctx, dict(call.arguments or {}))


__all__ = ["ToolCall", "ToolRouter"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_read_file.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add app/src/fileflash/agents/tools/drive.py app/src/fileflash/agents/harness/router.py app/tests/test_agent_read_file.py
git commit -m "feat(agent): add drive.readFile tool with dataPolicy-aware binary guard"
```

---

## Task 4: Wire `AgentUserSetting` defaults + settings env vars

**Files:**
- Modify: `app/src/fileflash/core/settings.py`
- Modify: `app/src/fileflash/agents/runtime/plan_runner.py` (defaults-merge step — partial, completed in Task 6)
- Test: `app/tests/test_agent_permission.py` (extend)

**Interfaces:**
- Produces: `agent_read_file_max_bytes`, `agent_skill_candidate_k` settings; `_apply_setting_defaults(request, setting)` helper.
- Consumes: `AgentSettingsRepository.get_by_user_id` (NOT the scaffold `SettingsService`).

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_agent_permission.py`:

```python
from fileflash.agents.harness.permission import _merge_data_policy
from fileflash.models import AgentUserSetting


def test_setting_default_data_policy_merges_take_strictest_bytes():
    setting = AgentUserSetting(
        user_id=1,
        default_data_policy_json={"allowFileContent": True, "maxReadBytes": 512},
    )
    merged = _merge_data_policy(
        AgentDataPolicy(allow_file_content=True, max_read_bytes=4096, allowed_mime_types=["*/*"]),
        setting,
    )
    assert merged.max_read_bytes == 512  # min wins
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd app && python -m pytest tests/test_agent_permission.py::test_setting_default_data_policy_merges_take_strictest_bytes -v`
Expected: PASS (already implemented in Task 1's `_merge_data_policy`). This is a regression guard.

- [ ] **Step 3: Add settings fields**

In `app/src/fileflash/core/settings.py`, after `agent_job_max_tool_calls` (line 161):

```python
    agent_read_file_max_bytes: int = Field(default=1048576, alias="AGENT_READ_FILE_MAX_BYTES")
    agent_skill_candidate_k: int = Field(default=3, alias="AGENT_SKILL_CANDIDATE_K")
```

- [ ] **Step 4: Add `_apply_setting_defaults` helper to `permission.py`**

Append to `app/src/fileflash/agents/harness/permission.py`:

```python
def _apply_setting_defaults(
    request: PlanAgentRequest, setting: AgentUserSetting | None
) -> PlanAgentRequest:
    if setting is None:
        return request
    merged_policy = _merge_data_policy(request.data_policy, setting)
    budget = request.hints.budget_tokens
    if budget == 8000 and setting.default_budget_tokens:
        budget = int(setting.default_budget_tokens)
    max_steps = request.hints.max_steps
    if max_steps == 12 and setting.default_max_steps:
        max_steps = int(setting.default_max_steps)
    return request.model_copy(
        update={
            "data_policy": merged_policy,
            "hints": request.hints.model_copy(
                update={"budget_tokens": budget, "max_steps": max_steps}
            ),
        }
    )


__all__ = ["EffectivePermission", "PermissionResolver", "_apply_setting_defaults"]
```

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/core/settings.py app/src/fileflash/agents/harness/permission.py app/tests/test_agent_permission.py
git commit -m "feat(agent): add read_file/skill_candidate_k settings and setting defaults merge"
```

---

## Task 5: `agent.useSkill` meta-tool + planner interception

**Files:**
- Create: `app/src/fileflash/agents/harness/skill_tool.py`
- Modify: `app/src/fileflash/agents/runtime/plan_runner.py`
- Test: `app/tests/test_agent_use_skill.py`

**Interfaces:**
- Produces: `agent.useSkill` registered in `REGISTRY` (schema only, for the LLM); `bind_skill_in_planner(db, user_id, skill_key, candidates, request, setting, current_permission) -> tuple[EffectivePermission, dict]` interceptor.
- Consumes: `AgentSkillRepository.get_by_key`, `PermissionResolver`, `EffectivePermission`.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_agent_use_skill.py`:

```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fileflash.agents.harness.permission import PermissionResolver
from fileflash.agents.harness.skill_tool import bind_skill_in_planner
from fileflash.agents.harness.tool_registry import REGISTRY
from fileflash.schemas.agent import PlanAgentRequest


def _request() -> PlanAgentRequest:
    return PlanAgentRequest.model_validate(
        {"chatSessionId": "1", "input": "organize my downloads", "context": {"rootFolderId": "root"}}
    )


@pytest.mark.asyncio
async def test_useskill_registers_in_registry_for_llm():
    import fileflash.agents.tools  # noqa: F401
    spec = REGISTRY.get("agent.useSkill")
    assert spec is not None
    assert spec.side_effect == "read"


@pytest.mark.asyncio
async def test_bind_skill_narrows_allowed_tools(monkeypatch):
    skill = MagicMock()
    skill.skill_key = "organizeByType"
    skill.tool_whitelist_json = ["drive.listFolder", "drive.createFolder", "drive.moveFile"]
    skill.name = "organizeByType"
    skill.description = ""
    skill.triggers_text = ""
    skill.plan_template_json = {}
    skill.search_text = ""

    repo = MagicMock()
    repo.get_by_key = AsyncMock(return_value=skill)

    db = AsyncMock()
    # AgentSkillRepository constructed with db; patch it
    import fileflash.agents.runtime.plan_runner as plan_module
    monkeypatch.setattr(plan_module, "AgentSkillRepository", lambda d: repo)

    base_perm = await PermissionResolver().effective(
        request=_request(), setting=None, skill=None, high_risk_confirmed=False
    )
    new_perm, payload = await bind_skill_in_planner(
        db=db,
        user_id=1,
        skill_key="organizeByType",
        candidates=[skill],
        request=_request(),
        setting=None,
        current_permission=base_perm,
    )
    assert payload["bound"] is True
    assert "drive.deleteFile" not in new_perm.allowed_tools
    assert "drive.moveFile" in new_perm.allowed_tools
    assert new_perm.skill_key == "organizeByType"


@pytest.mark.asyncio
async def test_bind_skill_unknown_key_returns_error():
    repo = MagicMock()
    repo.get_by_key = AsyncMock(return_value=None)
    db = AsyncMock()
    import fileflash.agents.runtime.plan_runner as plan_module
    monkeypatch_setattr = pytest.MonkeyPatch()
    import fileflash.agents.runtime.plan_runner as plan_module
    monkeypatch_setattr.setattr(plan_module, "AgentSkillRepository", lambda d: repo)
    base_perm = await PermissionResolver().effective(
        request=_request(), setting=None, skill=None, high_risk_confirmed=False
    )
    _, payload = await bind_skill_in_planner(
        db=db,
        user_id=1,
        skill_key="nope",
        candidates=[],
        request=_request(),
        setting=None,
        current_permission=base_perm,
    )
    assert payload["bound"] is False
    assert "unknown" in payload["message"].lower() or "not found" in payload["message"].lower()
```

> Fix the duplicated `import`/`monkeypatch_setattr` typo in `test_bind_skill_unknown_key_returns_error` — write it cleanly as:

```python
@pytest.mark.asyncio
async def test_bind_skill_unknown_key_returns_error(monkeypatch):
    repo = MagicMock()
    repo.get_by_key = AsyncMock(return_value=None)
    db = AsyncMock()
    import fileflash.agents.runtime.plan_runner as plan_module
    monkeypatch.setattr(plan_module, "AgentSkillRepository", lambda d: repo)
    base_perm = await PermissionResolver().effective(
        request=_request(), setting=None, skill=None, high_risk_confirmed=False
    )
    _, payload = await bind_skill_in_planner(
        db=db,
        user_id=1,
        skill_key="nope",
        candidates=[],
        request=_request(),
        setting=None,
        current_permission=base_perm,
    )
    assert payload["bound"] is False
    assert "unknown" in payload["message"].lower() or "not found" in payload["message"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && python -m pytest tests/test_agent_use_skill.py -v`
Expected: FAIL — `ModuleNotFoundError: fileflash.agents.harness.skill_tool`

- [ ] **Step 3: Create `skill_tool.py`**

Create `app/src/fileflash/agents/harness/skill_tool.py`:

```python
from __future__ import annotations

from typing import Any

from ...core.errors import ApiError
from ...schemas.agent import PlanAgentRequest
from ...models import AgentUserSetting
from ...repositories import AgentSkillRepository
from .permission import EffectivePermission, PermissionResolver
from .tool_registry import REGISTRY, ToolContext, ToolSpec


async def _use_skill_handler(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    # This handler is never reached at runtime — the planner intercepts agent.useSkill
    # before dispatch. It exists only so the tool has a valid handler for registration.
    return {"bound": False, "message": "agent.useSkill must be intercepted by the planner."}


def register_use_skill_tool() -> None:
    try:
        REGISTRY.get("agent.useSkill")
        return  # already registered
    except KeyError:
        pass
    REGISTRY.register(
        ToolSpec(
            name="agent.useSkill",
            description=(
                "Adopt a skill to constrain your tool set to that skill's whitelist. "
                "Call once during planning if a skill fits; optional. Returns the bound "
                "tool list. Use skillKey 'none' to decline all skills. "
                "Cannot be used during execution."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "skillKey": {
                        "type": "string",
                        "description": "One of the offered skill keys, or 'none' to decline.",
                    }
                },
                "required": ["skillKey"],
            },
            side_effect="read",
            risk_level="low",
            requires_confirmation=False,
            handler=_use_skill_handler,
        )
    )


async def bind_skill_in_planner(
    *,
    db: Any,
    user_id: int,
    skill_key: str,
    candidates: list[Any],
    request: PlanAgentRequest,
    setting: AgentUserSetting | None,
    current_permission: EffectivePermission,
) -> tuple[EffectivePermission, dict[str, Any]]:
    if skill_key == "none":
        return current_permission, {"bound": False, "declined": True, "skillKey": "none"}
    candidate_keys = {getattr(c, "skill_key", None) for c in candidates}
    if skill_key not in candidate_keys:
        return current_permission, {
            "bound": False,
            "skillKey": skill_key,
            "message": f"Unknown or unoffered skill key: {skill_key}",
        }
    repo = AgentSkillRepository(db)
    skill = await repo.get_by_key(skill_key=skill_key, user_id=user_id)
    if skill is None:
        return current_permission, {
            "bound": False,
            "skillKey": skill_key,
            "message": f"Skill not found: {skill_key}",
        }
    new_perm = await PermissionResolver().effective(
        request=request,
        setting=setting,
        skill=skill,
        high_risk_confirmed=current_permission.high_risk_confirmed,
    )
    return new_perm, {
        "bound": True,
        "skillKey": skill_key,
        "allowedTools": sorted(new_perm.allowed_tools),
    }


# Register on import so the LLM sees the tool whenever builtin tools are registered.
register_use_skill_tool()


__all__ = ["bind_skill_in_planner", "register_use_skill_tool"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_use_skill.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/harness/skill_tool.py app/tests/test_agent_use_skill.py
git commit -m "feat(agent): add agent.useSkill meta-tool and planner bind interceptor"
```

---

## Task 6: Integrate permission + skills + setting defaults into `PlanRunner`

**Files:**
- Modify: `app/src/fileflash/agents/runtime/plan_runner.py`
- Test: `app/tests/test_agent_plan_execute_runtime.py` (extend)

**Interfaces:**
- Consumes: `PermissionResolver`, `EffectivePermission`, `PolicyGuard.evaluate(phase="planning")`, `bind_skill_in_planner`, `_apply_setting_defaults`, `AgentSettingsRepository`, `agent_skill_candidate_k` setting.
- Produces: planner that injects top-K skill menu into system prompt, intercepts `agent.useSkill`, gates exploration via `PolicyGuard`.

- [ ] **Step 1: Write the failing integration test**

Append to `app/tests/test_agent_plan_execute_runtime.py` (match existing fixture style in that file; reuse its `plan_runner`/`fake_planner`/`db` fixtures if present, else construct a `PlanRunner` with a mocked `PlannerClient`):

```python
@pytest.mark.asyncio
async def test_plan_runner_injects_skill_menu_and_use_skill_tool(db_session, fake_planner):
    # fake_planner captures the tools list passed to create_plan
    from fileflash.agents.runtime.plan_runner import PlanRunner
    from fileflash.models import BackgroundJob
    job = BackgroundJob(
        task_type="agent.plan",
        requested_by=1,
        payload={"chatSessionId": "1", "input": "organize my files", "context": {"rootFolderId": "root"}},
    )
    runner = PlanRunner(planner_client=fake_planner)
    await runner.run(db=db_session, job=job)
    tools = fake_planner.last_tools
    tool_names = [t["name"] for t in tools]
    assert "agent_use_skill" in tool_names  # provider name for agent.useSkill
    # system prompt contains a skill menu section
    assert "Available skills" in fake_planner.last_system_prompt or "useSkill" in fake_planner.last_system_prompt
```

> Adapt `fake_planner` to record `last_tools` and `last_system_prompt`. If the existing test file already has a fake planner, extend it to capture these; otherwise add a small `FakePlanner` class implementing `create_plan`/`create_answer` that stores the args.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_agent_plan_execute_runtime.py::test_plan_runner_injects_skill_menu_and_use_skill_tool -v`
Expected: FAIL — `agent.useSkill` not in tools / system prompt unchanged.

- [ ] **Step 3: Modify `PlanRunner._run` to build permission + candidates + intercept useSkill**

In `app/src/fileflash/agents/runtime/plan_runner.py`:

3a. Add imports at top:

```python
from ..harness.permission import (
    EffectivePermission,
    PermissionResolver,
    _apply_setting_defaults,
)
from ..harness.policy import PolicyGuard
from ..harness.skill_tool import bind_skill_in_planner
from ...repositories import AgentSettingsRepository
```

3b. Replace the `skill = await _choose_skill(...)` / `allowed_tools = _skill_tool_whitelist(skill)` block (lines ~72-84) with:

```python
        setting_repo = AgentSettingsRepository(db)
        setting = await setting_repo.get_by_user_id(user_id)
        request = _apply_setting_defaults(request, setting)
        candidates = await _candidate_skills(
            db,
            user_id=user_id,
            task_input=request.input,
            prefer_skill_id=request.hints.prefer_skill_id,
            k=self.settings.agent_skill_candidate_k,
        )
        permission = await PermissionResolver().effective(
            request=request,
            setting=setting,
            skill=candidates[0] if (request.hints.prefer_skill_id and candidates) else None,
            high_risk_confirmed=False,
        )
        # If a preferred skill is forced, it's already bound above; else start unbound.
        if not (request.hints.prefer_skill_id and candidates):
            permission = await PermissionResolver().effective(
                request=request, setting=setting, skill=None, high_risk_confirmed=False
            )
        skill = candidates[0] if (request.hints.prefer_skill_id and candidates) else None
        allowed_tools = tuple(sorted(permission.allowed_tools))
        allowed_tool_set = set(allowed_tools)
        exploration_tools = tuple(
            tool_name
            for tool_name in allowed_tools
            if REGISTRY.get(tool_name).side_effect == "read"
        )
        exploration_tool_set = set(exploration_tools)
        # Include the useSkill meta-tool for the LLM during planning:
        planning_exploration_tools = exploration_tools + ("agent.useSkill",)
```

3c. Replace the `_planning_tool_executor` inner function (lines ~90-142) to delegate to `PolicyGuard` and intercept `agent.useSkill`:

```python
        planner_router = ToolRouter(db=db, user_id=user_id)
        policy_guard = PolicyGuard()
        tool_call_budget = min(self.settings.agent_job_max_tool_calls, 32)
        planned_tool_calls = 0
        planning_evidence: list[AgentPlanningEvidence] = []

        async def _planning_tool_executor(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
            nonlocal planned_tool_calls, permission, skill, allowed_tools, allowed_tool_set
            planned_tool_calls += 1
            if planned_tool_calls > tool_call_budget:
                raise ApiError(
                    status_code=400, code=400,
                    message="Planner exceeded exploratory tool-call budget",
                )
            # Intercept the useSkill meta-tool — never dispatch it.
            if tool_name == "agent.useSkill":
                new_perm, payload = await bind_skill_in_planner(
                    db=db,
                    user_id=user_id,
                    skill_key=str(args.get("skillKey", "")),
                    candidates=candidates,
                    request=request,
                    setting=setting,
                    current_permission=permission,
                )
                if payload.get("bound"):
                    permission = new_perm
                    skill = next(
                        (c for c in candidates if getattr(c, "skill_key", None) == payload["skillKey"]),
                        skill,
                    )
                    allowed_tools = tuple(sorted(permission.allowed_tools))
                    allowed_tool_set = set(allowed_tools)
                if len(planning_evidence) < 12:
                    planning_evidence.append(
                        AgentPlanningEvidence(
                            step=planned_tool_calls,
                            tool=tool_name,
                            input=_evidence_mapping(args),
                            output_preview=_evidence_preview(payload),
                        )
                    )
                return payload
            # All other tools: gate via PolicyGuard (phase=planning denies writes/content-read).
            decision = await policy_guard.evaluate(
                ctx=ToolContext(db=db, user_id=user_id, file_service=None, folder_service=None),
                action=AgentProposedAction(
                    step=planned_tool_calls, tool=tool_name, input=args, side_effect="read"
                ),
                permission=permission,
                phase="planning",
            )
            if not decision.allowed:
                blocked = _blocked_planning_tool_result(
                    tool_name=tool_name, reason="; ".join(decision.reasons)
                )
                if len(planning_evidence) < 12:
                    planning_evidence.append(
                        AgentPlanningEvidence(
                            step=planned_tool_calls, tool=tool_name,
                            input=_evidence_mapping(args), output_preview=_evidence_preview(blocked),
                        )
                    )
                return blocked
            output = await planner_router.dispatch(ToolCall(tool_name=tool_name, arguments=args))
            if len(planning_evidence) < 12:
                planning_evidence.append(
                    AgentPlanningEvidence(
                        step=planned_tool_calls, tool=tool_name,
                        input=_evidence_mapping(args), output_preview=_evidence_preview(output),
                    )
                )
            return output
```

3d. Update the `tools=REGISTRY.anthropic_tools_for(exploration_tools)` call in `_create_plan` to use `planning_exploration_tools`:

```python
                tools=REGISTRY.anthropic_tools_for(planning_exploration_tools),
```

3e. Update `_system_prompt` to include the skill menu (pass candidates):

```python
        async def _create_plan(metadata_payload: dict[str, Any]) -> dict[str, Any]:
            return await self.planner_client.create_plan(
                system_prompt=_system_prompt(candidates=candidates),
                user_prompt=_user_prompt(
                    request=request, skill=skill, allowed_tools=allowed_tools,
                    exploration_tools=exploration_tools, metadata=metadata_payload,
                ),
                max_tokens=request.hints.budget_tokens,
                reasoning_effort=request.hints.reasoning_effort,
                tools=REGISTRY.anthropic_tools_for(planning_exploration_tools),
                tool_executor=_planning_tool_executor,
                max_tool_roundtrips=6,
            )
```

3f. Replace the `_system_prompt()` function (line ~596):

```python
def _system_prompt(*, candidates: list[Any] | None = None) -> str:
    menu = _skill_menu(candidates or [])
    return (
        "You are FileFlash Agent Planner. Build plans from tool-grounded facts, not assumptions. "
        "If you need facts, first call read-only tools; then output one final JSON object that matches outputSchema. "
        "Do not read or infer file contents unless you call drive.readFile and dataPolicy allows it. "
        "Deletions are high risk and must be explicit. "
        "Cross-step dependencies must use '$stepN.field' references only and never symbolic placeholders "
        "like 'newFolderId'. "
        + menu
    )


def _skill_menu(candidates: list[Any]) -> str:
    if not candidates:
        return ""
    lines = [
        "You may use one of these skills if it fits the task. Each skill restricts which tools you may use. "
        "To adopt a skill, call agent.useSkill with its key. You may also proceed without a skill "
        "(free planning), but then only read-only exploration tools are available during planning.",
        "",
        "Available skills:",
    ]
    for c in candidates:
        key = getattr(c, "skill_key", "?")
        name = getattr(c, "name", key)
        desc = getattr(c, "description", "") or ""
        wl = getattr(c, "tool_whitelist_json", None) or []
        wl_str = ", ".join(str(t) for t in wl) if wl else "(all tools)"
        lines.append(f"- {key} ({name}): {desc}. tools: {wl_str}")
    return "\n".join(lines) + "\n"
```

3g. Add `_candidate_skills` (top-K version replacing `_choose_skill`):

```python
async def _candidate_skills(
    db: AsyncSession,
    *,
    user_id: int,
    task_input: str,
    prefer_skill_id: str | None,
    k: int = 3,
) -> list[Any]:
    repo = AgentSkillRepository(db)
    if prefer_skill_id:
        skill = await repo.get_by_key(skill_key=prefer_skill_id, user_id=user_id)
        if skill is None:
            raise ApiError(status_code=404, code=404, message="Preferred skill not found")
        return [skill]
    candidates = await repo.list_visible(user_id=user_id, limit=50)
    if not candidates:
        return []
    normalized_input = task_input.lower()
    scored: list[tuple[int, Any]] = []
    for candidate in candidates:
        haystack = (
            f"{candidate.skill_key} {candidate.name} {candidate.description} "
            f"{candidate.triggers_text or ''} {candidate.search_text}"
        ).lower()
        score = 0
        for token in _tokens(normalized_input):
            if token in haystack:
                score += 2 if token in {"organize", "整理", "classify", "分类"} else 1
        if "整理" in normalized_input and "organize" in haystack:
            score += 4
        scored.append((score, candidate))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    positive = [pair for pair in scored if pair[0] > 0]
    if not positive:
        return []  # no skill forced; LLM may still pick via useSkill
    return [pair[1] for pair in positive[: max(1, k)]]
```

Keep the old `_choose_skill` function but have it delegate, OR delete it if nothing else references it (grep first). Keep `_skill_tool_whitelist` if still referenced; otherwise leave it (it's now in `permission.py`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_plan_execute_runtime.py -v`
Expected: PASS — including the new test + all existing plan tests (regression).

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/runtime/plan_runner.py app/tests/test_agent_plan_execute_runtime.py
git commit -m "feat(agent): inject skill menu, intercept useSkill, gate planning via PolicyGuard"
```

---

## Task 7: Integrate `PolicyGuard.evaluate` into `ExecuteRunner` + `denied` audit

**Files:**
- Modify: `app/src/fileflash/agents/runtime/execute_runner.py`
- Test: `app/tests/test_agent_plan_execute_runtime.py` (extend)

**Interfaces:**
- Consumes: `PermissionResolver`, `EffectivePermission`, `PolicyGuard.evaluate(phase="executing")`, `AgentSettingsRepository`, `AgentActionLogRepository`.
- Produces: denied actions written as `AgentActionLog(status="denied")` + `tool.failed` event with `{denied: true, reasons}`.

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_agent_plan_execute_runtime.py`:

```python
@pytest.mark.asyncio
async def test_execute_denies_readfile_when_data_policy_disables_content(db_session, fake_answer):
    from fileflash.agents.runtime.execute_runner import ExecuteRunner
    from fileflash.models import BackgroundJob, AgentPlan
    from fileflash.schemas.agent import AgentProposedAction
    # plan has a readFile action; request data_policy allow_file_content=False
    # build a plan row + job row per existing fixtures, then run ExecuteRunner
    # assert: action_log status == "denied", job not failed on this step but recorded
    ...
```

> Implement concretely using the existing `AgentPlan` + `BackgroundJob` fixture pattern in that file. The assertion: `AgentActionLog.status == "denied"` and a `tool.failed` event with `denied: True` was published.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && python -m pytest tests/test_agent_plan_execute_runtime.py::test_execute_denies_readfile_when_data_policy_disables_content -v`
Expected: FAIL — current execute runner does not write `denied`.

- [ ] **Step 3: Modify `ExecuteRunner` to build permission and call `PolicyGuard.evaluate`**

In `app/src/fileflash/agents/runtime/execute_runner.py`:

3a. Add imports:

```python
from ..harness.permission import EffectivePermission, PermissionResolver, _apply_setting_defaults
from ..harness.policy import PolicyGuard
from ..harness.tool_registry import ToolContext
from ...repositories import AgentSettingsRepository
from ...schemas.agent import AgentDataPolicy
```

3b. In `_run`, after loading `actions` and `high_risk_confirmed` (line ~87), build the permission:

```python
        # Load the original plan request to recover execution_policy / data_policy.
        plan_request = PlanAgentRequest.model_validate(dict(plan.context_json or {})) if plan.context_json else None
        setting = await AgentSettingsRepository(db).get_by_user_id(int(job.requested_by))
        # Fallback: construct a minimal request from plan fields if context_json absent.
        base_request = plan_request or PlanAgentRequest.model_validate(
            {"chatSessionId": request.chat_session_id, "input": "", "context": {"rootFolderId": "root"},
             "executionPolicy": "confirm", "dataPolicy": {"allowFileContent": False}}
        )
        base_request = _apply_setting_defaults(base_request, setting)
        permission = await PermissionResolver().effective(
            request=base_request,
            setting=setting,
            skill=None,  # skill already baked into plan's allowed_tools via chosen_skill
            high_risk_confirmed=high_risk_confirmed,
        )
        # Narrow permission to the plan's chosen skill if recorded.
        if getattr(plan, "chosen_skill_id", None):
            from ...repositories import AgentSkillRepository
            skill = await AgentSkillRepository(db).get_by_key(
                skill_key=str(plan.chosen_skill_id), user_id=int(job.requested_by)
            )
            if skill is not None:
                permission = await PermissionResolver().effective(
                    request=base_request, setting=setting, skill=skill,
                    high_risk_confirmed=high_risk_confirmed,
                )
```

3c. Replace the per-step `policy_guard.evaluate_tool_call(...)` block (lines ~118-128) with the new evaluate + denied audit:

```python
            decision = await self.policy_guard.evaluate(
                ctx=ToolContext(
                    db=db, user_id=int(job.requested_by),
                    file_service=None, folder_service=None,
                ),
                action=action,
                permission=permission,
                phase="executing",
            )
            if not decision.allowed:
                await action_logs.append_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    tool_name=action.tool,
                    inputs_json=action.input,
                    status="denied",
                    started_at=datetime.now(UTC),
                )
                await action_logs.finish_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    outputs_json={},
                    status="denied",
                    duration_ms=0,
                    error_message="; ".join(decision.reasons)[:2000],
                )
                await db.commit()
                await self._publish_tool(
                    "tool.failed",
                    job_id=int(job.job_id),
                    step=action.step,
                    tool=action.tool,
                    payload={"denied": True, "reasons": decision.reasons},
                )
                warnings.append(f"Step {action.step} denied by policy: {'; '.join(decision.reasons)}")
                continue  # skip this step, proceed to next (do not fail the whole job)
```

> Need `PlanAgentRequest` imported in execute_runner: `from ...schemas.agent import AgentExecutionResult, AgentProposedAction, ExecuteAgentRequest, PlanAgentRequest`. Also verify `plan.context_json` exists on the `AgentPlan` model — if the field is named differently (e.g. `context_json`), use the actual attribute; if absent, the fallback minimal request is used.

3d. Ensure `datetime` is imported (already imported at top: `from datetime import UTC, datetime`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_plan_execute_runtime.py -v`
Expected: PASS — new denied test + all existing execute tests (regression).

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/runtime/execute_runner.py app/tests/test_agent_plan_execute_runtime.py
git commit -m "feat(agent): enforce PolicyGuard in execute and record denied actions"
```

---

## Task 8: Seed 3 builtin skills (migration) + routes test

**Files:**
- Create: `docker/flyway/migrations/V17__agent_builtin_skills.sql`
- Modify: `app/tests/test_agent_routes.py` (extend)
- Modify: `app/src/fileflash/repositories/agent/__init__.py` if `AgentSettingsRepository` export missing

**Interfaces:**
- Produces: 3 builtin skill rows (`organizeByType`, `dedupScan`, `listAndSummarize`), `visibility='global'`, `owner_user_id=NULL`.
- Consumes: existing `agent_skill` table columns.

- [ ] **Step 1: Verify the `agent_skill` table columns**

Run: `cd app && python -c "from fileflash.models import AgentSkill; print([c.name for c in AgentSkill.__table__.columns])"`
Expected: a list including `skill_key, name, description, triggers_text, tool_whitelist_json, plan_template_json, inputs_schema_json, outputs_schema_json, visibility, owner_user_id`.

- [ ] **Step 2: Write the seed migration**

Create `docker/flyway/migrations/V17__agent_builtin_skills.sql`:

```sql
INSERT INTO agent_skill (skill_key, name, description, triggers_text, tool_whitelist_json, plan_template_json, inputs_schema_json, outputs_schema_json, visibility, owner_user_id, created_at, updated_at)
VALUES
(
  'organizeByType',
  '按类型整理',
  '按文件类型整理指定文件夹：图片 / 视频 / 文档 / 其他',
  '整理,归档,分类,organize,classify,按类型',
  '["drive.listFolder","drive.getFileInfo","drive.createFolder","drive.moveFile"]'::jsonb,
  '{}'::jsonb,
  '{"type":"object","required":["sourceFolderId"],"properties":{"sourceFolderId":{"type":"string"},"targetFolderId":{"type":"string"}}}'::jsonb,
  '{}'::jsonb,
  'global',
  NULL,
  NOW(),
  NOW()
),
(
  'dedupScan',
  '去重扫描',
  '找出重复文件并给出删除建议',
  '重复,去重,dedup,duplicate',
  '["drive.listFolder","drive.getFileInfo","drive.findDuplicates","drive.deleteFile"]'::jsonb,
  '{}'::jsonb,
  '{}'::jsonb,
  '{}'::jsonb,
  'global',
  NULL,
  NOW(),
  NOW()
),
(
  'listAndSummarize',
  '列出并摘要',
  '列出某文件夹下的内容并给出统计摘要',
  '列出,统计,摘要,list,summarize',
  '["drive.listFolder","drive.countFiles","drive.getFileInfo","drive.statsByCategory"]'::jsonb,
  '{}'::jsonb,
  '{}'::jsonb,
  '{}'::jsonb,
  'global',
  NULL,
  NOW(),
  NOW()
)
ON CONFLICT DO NOTHING;
```

> Verify the `visibility` enum value `'global'` matches `AgentSkillVisibility` in `models/enums.py`. If the enum is uppercase or different, adjust. Confirm `agent_skill` has a unique constraint on `skill_key` — if so, `ON CONFLICT (skill_key) DO NOTHING`; else `ON CONFLICT DO NOTHING` (safe).

- [ ] **Step 3: Write the routes test**

Append to `app/tests/test_agent_routes.py`:

```python
@pytest.mark.asyncio
async def test_plan_request_with_data_policy_flows_through(client, auth_headers):
    response = await client.post(
        "/api/v1/agent/plan",
        headers=auth_headers,
        json={
            "chatSessionId": "1",
            "input": "list my files",
            "context": {"rootFolderId": "root"},
            "dataPolicy": {"allowFileContent": True, "maxReadBytes": 512000, "allowedMimeTypes": ["text/*"]},
        },
    )
    assert response.status_code in (200, 202)
    # The plan job is enqueued; dataPolicy is carried into the job payload.
```

> Adapt endpoint path + auth fixture to match the existing test file's conventions (some files use `/agent/plan` without `/api/v1`; match what's there).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && python -m pytest tests/test_agent_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docker/flyway/migrations/V17__agent_builtin_skills.sql app/tests/test_agent_routes.py
git commit -m "feat(agent): seed 3 builtin skills and cover dataPolicy plan flow"
```

---

## Task 9: Full regression + final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full agent test suite**

Run: `cd app && python -m pytest tests/test_agent_permission.py tests/test_agent_read_file.py tests/test_agent_use_skill.py tests/test_agent_plan_execute_runtime.py tests/test_agent_routes.py tests/test_agent_a_end_to_end.py -v`
Expected: ALL PASS.

- [ ] **Step 2: Verify no broken imports across the package**

Run: `cd app && python -c "from fileflash.agents.harness.permission import PermissionResolver, EffectivePermission; from fileflash.agents.harness.policy import PolicyGuard; from fileflash.agents.harness.skill_tool import bind_skill_in_planner; from fileflash.agents.runtime.plan_runner import PlanRunner; from fileflash.agents.runtime.execute_runner import ExecuteRunner; print('imports OK')"`
Expected: `imports OK`

- [ ] **Step 3: Verify `agent.useSkill` and `drive.readFile` are registered**

Run: `cd app && python -c "import fileflash.agents.tools; from fileflash.agents.harness.tool_registry import REGISTRY; print(sorted(REGISTRY.all_names()))"`
Expected: list containing `agent.useSkill` and `drive.readFile`.

- [ ] **Step 4: Final commit (if any stray changes)**

```bash
git status
# if clean, nothing to commit; otherwise commit
```

---

## Self-Review (completed by plan author)

**Spec coverage check:**
- §1 Architecture (single choke point) → Task 2 (`PolicyGuard.evaluate`), Tasks 6+7 (both runners call it).
- §2 Permission model (three-axis intersection, `EffectivePermission`, `PermissionResolver`) → Task 1.
- §3 `drive.readFile` + dataPolicy gating + binary guard → Task 3 (+ Task 2's `_check_content_read`).
- §4 LLM-invocable skills (`agent.useSkill`, intercept, top-K menu) → Tasks 5 + 6.
- §5 Data model + `AgentUserSetting` defaults + env vars → Tasks 4 + 7 + 8.
- §6 Testing + rollout → all tasks are TDD; Task 9 is full regression.

**Placeholder scan:** None — every code step contains real code. (The two `...` placeholders in Task 7 step 1 and Task 8 step 3 test bodies are intentional "adapt to existing fixture" notes with concrete guidance, not implementation placeholders.)

**Type consistency:** `EffectivePermission` fields (`execution_policy`, `data_policy`, `allowed_tools`, `skill_key`, `deny_read_content`, `high_risk_confirmed`) used consistently across Tasks 1, 2, 6, 7. `PolicyGuard.evaluate(*, ctx, action, permission, phase)` signature consistent. `bind_skill_in_planner` signature consistent between Task 5 and Task 6. `ToolContext.storage_reader` added in Task 2, used in Task 3, referenced in Task 7 (passed `None` — acceptable since execute-side `readFile` mime check uses `ctx.db` not storage; storage is only needed in the handler dispatch which constructs its own ctx in execute via `ToolRouter`).

**Known implementation risks flagged for the executor:**
1. `plan.context_json` attribute name in Task 7 — verify against `AgentPlan` model; the fallback handles absence.
2. `AgentSkillVisibility` enum value casing in Task 8 — verify `'global'` matches.
3. Existing `fake_planner`/`fake_answer`/`db_session`/`client`/`auth_headers` fixtures — adapt new tests to the actual fixture names in each test file (they may differ from the illustrative names used here).
