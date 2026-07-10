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
    # bind_skill_in_planner lives in skill_tool.py and constructs AgentSkillRepository(db)
    # there, so the patch target must be that module — not plan_runner.
    import fileflash.agents.harness.skill_tool as skill_tool_module
    monkeypatch.setattr(skill_tool_module, "AgentSkillRepository", lambda d: repo)

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
async def test_bind_skill_unknown_key_returns_error(monkeypatch):
    repo = MagicMock()
    repo.get_by_key = AsyncMock(return_value=None)
    db = AsyncMock()
    import fileflash.agents.harness.skill_tool as skill_tool_module
    monkeypatch.setattr(skill_tool_module, "AgentSkillRepository", lambda d: repo)
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
