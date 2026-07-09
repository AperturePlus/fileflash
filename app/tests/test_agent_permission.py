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
