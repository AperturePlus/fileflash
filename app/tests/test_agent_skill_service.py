from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.errors import ApiError
from src.models import AgentSkill
from src.models.enums import AgentSkillVisibility
from src.repositories import AgentSkillRepository
from src.schemas.agent_skill import CreateAgentSkillRequest, ImportAgentSkillItem, ImportAgentSkillsRequest, UpdateAgentSkillRequest
from src.services.agent.skill_service import SkillService


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.flush = AsyncMock()
        self.delete = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()


@pytest.mark.asyncio
async def test_create_custom_skill_generates_private_key_and_commits():
    session = DummySession()
    session.scalar.return_value = None
    now = datetime.now(UTC)

    async def _refresh(entity: AgentSkill):
        entity.created_at = now
        entity.updated_at = now

    session.refresh.side_effect = _refresh

    repo = AgentSkillRepository(session)
    service = SkillService(db=session, skills=repo)

    payload = CreateAgentSkillRequest(
        name="My Cleanup",
        description="Private cleanup helper",
    )
    item = await service.create_custom_skill(user_id=7, payload=payload)

    assert item.visibility == "private"
    assert item.owner_user_id == "7"
    assert item.skill_key.startswith("user:7:")
    assert "my-cleanup" in item.skill_key
    assert len(item.skill_key) <= 120

    session.commit.assert_awaited_once()
    session.add.assert_called_once()
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_update_custom_skill_requires_owner_private():
    session = DummySession()
    session.scalar.return_value = None

    repo = AgentSkillRepository(session)
    service = SkillService(db=session, skills=repo)

    with pytest.raises(ApiError) as exc:
        await service.update_custom_skill(
            user_id=7,
            skill_key="user:7:missing-abc123",
            payload=UpdateAgentSkillRequest(description="updated"),
        )

    assert exc.value.status_code == 404
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_custom_skill_requires_owner_private():
    session = DummySession()
    session.scalar.return_value = None

    repo = AgentSkillRepository(session)
    service = SkillService(db=session, skills=repo)

    with pytest.raises(ApiError) as exc:
        await service.delete_custom_skill(user_id=7, skill_key="user:7:missing-abc123")

    assert exc.value.status_code == 404
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_insert_only_conflict_raises_409():
    session = DummySession()
    existing = AgentSkill(
        skill_key="builtin:test",
        name="test",
        description="old",
        triggers_text=None,
        tool_whitelist_json=[],
        plan_template_json={},
        inputs_schema_json={},
        outputs_schema_json={},
        visibility=AgentSkillVisibility.GLOBAL,
        owner_user_id=None,
    )
    session.scalars.return_value = [existing]

    repo = AgentSkillRepository(session)
    service = SkillService(db=session, skills=repo)

    payload = ImportAgentSkillsRequest(
        mode="insertOnly",
        items=[
            ImportAgentSkillItem(
                skill_key="builtin:test",
                name="test2",
                description="new",
            )
        ],
    )

    with pytest.raises(ApiError) as exc:
        await service.import_global_skills(payload=payload)

    assert exc.value.status_code == 409
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_upsert_updates_existing_global():
    session = DummySession()
    existing = AgentSkill(
        skill_key="builtin:test",
        name="old",
        description="old",
        triggers_text="old",
        tool_whitelist_json=["a"],
        plan_template_json={"x": 1},
        inputs_schema_json={},
        outputs_schema_json={},
        visibility=AgentSkillVisibility.GLOBAL,
        owner_user_id=None,
    )
    session.scalars.return_value = [existing]

    repo = AgentSkillRepository(session)
    service = SkillService(db=session, skills=repo)

    payload = ImportAgentSkillsRequest(
        mode="upsert",
        items=[
            ImportAgentSkillItem(
                skill_key="builtin:test",
                name="new",
                description="new desc",
                triggers_text=None,
                tool_whitelist=["drive.listFolder"],
                plan_template={"steps": []},
                inputs_schema={"type": "object"},
                outputs_schema={"type": "object"},
            )
        ],
    )

    result = await service.import_global_skills(payload=payload)
    assert result.results[0].action == "updated"
    assert existing.name == "new"
    assert existing.description == "new desc"
    assert existing.triggers_text is None
    assert existing.tool_whitelist_json == ["drive.listFolder"]

    session.commit.assert_awaited_once()
    session.flush.assert_awaited()

