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
    perm = await PermissionResolver().effective(
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


# ---------------------------------------------------------------------------
# Task 2: PolicyGuard.evaluate — single permission choke point
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock  # noqa: E402

from fileflash.agents.harness.policy import PolicyGuard  # noqa: E402
from fileflash.agents.harness.tool_registry import ToolContext  # noqa: E402
from fileflash.schemas.agent import AgentProposedAction  # noqa: E402

REGISTRY_NAMES = __import__(
    "fileflash.agents.harness.tool_registry", fromlist=["REGISTRY"]
).REGISTRY.all_names()


def _ctx_with_mime(mime: str = "text/plain") -> ToolContext:
    db = AsyncMock()
    db.scalar = AsyncMock(
        return_value=type(
            "F",
            (),
            {"mime_type": mime, "file_ext": None, "file_name": "x.txt"},
        )()
    )
    return ToolContext(
        db=db, user_id=1, file_service=None, folder_service=None, storage_reader=None
    )


def _perm(
    *,
    allowed_tools=None,
    deny_read=False,
    allow_content=True,
    mimes=None,
    high_risk=False,
    policy="confirm",
):
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


@pytest.mark.asyncio
async def test_evaluate_readfile_max_read_bytes_exceeded_denied():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(
            step=1,
            tool="drive.readFile",
            input={"fileId": "1", "maxBytes": 2097152},
            side_effect="read",
        ),
        permission=_perm(allowed_tools=["drive.readFile"]),
        phase="executing",
    )
    assert decision.allowed is False
    assert any("max_read_bytes" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_evaluate_readfile_small_read_at_large_offset_allowed():
    # Regression guard for the old `+ offset` logic: reading 1 byte at offset
    # 1MB with max_read_bytes=1MB must be ALLOWED (bytes read, not position).
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(
            step=1,
            tool="drive.readFile",
            input={"fileId": "1", "maxBytes": 1, "offset": 1048576},
            side_effect="read",
        ),
        permission=_perm(allowed_tools=["drive.readFile"]),
        phase="executing",
    )
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_evaluate_planonly_planning_allowed():
    decision = await PolicyGuard().evaluate(
        ctx=_ctx_with_mime(),
        action=AgentProposedAction(step=1, tool="drive.listFolder", input={"folderId": "root"}, side_effect="read"),
        permission=_perm(allowed_tools=["drive.listFolder"], policy="planOnly"),
        phase="planning",
    )
    assert decision.allowed is True


# ---------------------------------------------------------------------------
# Task 4: regression guard for _merge_data_policy take-strictest bytes
# ---------------------------------------------------------------------------

from fileflash.agents.harness.permission import _merge_data_policy  # noqa: E402


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
