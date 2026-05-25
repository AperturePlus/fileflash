from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.agents import PlanRunner, PromptBuilder
from fileflash.models import AgentWorkSession, BackgroundJob
from fileflash.repositories import (
    AgentActionLogRepository,
    AgentMcpRepository,
    AgentMemoryRepository,
    AgentPlanRepository,
    AgentSettingsRepository,
    AgentSkillRepository,
    AgentWorkSessionRepository,
)
from fileflash.schemas.job import to_background_job_response


class FakeMappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return list(self._rows)


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.flush = AsyncMock()
        self.delete = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()


def test_background_job_response_includes_agent_fields():
    now = datetime.now(UTC)
    job = BackgroundJob(
        job_id=123,
        task_type="agent.plan",
        status="running",
        agent_phase="planning",
        priority=100,
        payload={},
        result={},
        error_message=None,
        attempt=0,
        max_attempts=5,
        scheduled_at=now,
        started_at=now,
        finished_at=None,
        trace_id="trace-123",
        idempotency_key=None,
        cancel_requested_at=now,
        requested_by=7,
        created_at=now,
        updated_at=now,
    )

    payload = to_background_job_response(job).model_dump(by_alias=True)
    assert payload["agentPhase"] == "planning"
    assert payload["cancelRequestedAt"] == now


@pytest.mark.asyncio
async def test_agent_settings_upsert_creates_and_updates(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    repo = AgentSettingsRepository(session)
    monkeypatch.setattr(repo, "get_by_user_id", AsyncMock(return_value=None))

    created = await repo.upsert_for_user(user_id=1, values={"llm_provider": "openai"})
    assert created.user_id == 1
    assert created.llm_provider == "openai"
    session.add.assert_called_once()
    session.flush.assert_awaited()

    existing = created
    session.add.reset_mock()
    session.flush.reset_mock()
    monkeypatch.setattr(repo, "get_by_user_id", AsyncMock(return_value=existing))
    updated = await repo.upsert_for_user(user_id=1, values={"llm_model": "gpt-5.4"})
    assert updated is existing
    assert updated.llm_model == "gpt-5.4"
    session.add.assert_not_called()
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_agent_skill_list_visible_maps_catalog_rows():
    session = DummySession()
    session.execute.return_value = FakeMappingResult(
        [
            {
                "skill_id": 1,
                "skill_key": "builtin:organizeByType",
                "name": "organizeByType",
                "description": "Organize files by type",
                "triggers_text": "organize, classify",
                "tool_whitelist_json": ["drive.listFolder"],
                "plan_template_json": {},
                "inputs_schema_json": {},
                "outputs_schema_json": {},
                "visibility": "global",
                "owner_user_id": None,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "search_text": "organize files by type",
            },
            {
                "skill_id": 2,
                "skill_key": "user:cleanup",
                "name": "cleanup",
                "description": "Private cleanup helper",
                "triggers_text": None,
                "tool_whitelist_json": [],
                "plan_template_json": {},
                "inputs_schema_json": {},
                "outputs_schema_json": {},
                "visibility": "private",
                "owner_user_id": 7,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "search_text": "cleanup helper",
            },
        ]
    )

    repo = AgentSkillRepository(session)
    items = await repo.list_visible(user_id=7)
    assert [item.skill_key for item in items] == ["builtin:organizeByType", "user:cleanup"]
    statement = session.execute.await_args.args[0]
    assert "owner_user_id = CAST(:user_id AS BIGINT)" in str(statement)


@pytest.mark.asyncio
async def test_agent_skill_list_visible_accepts_null_user_id():
    session = DummySession()
    session.execute.return_value = FakeMappingResult([])

    repo = AgentSkillRepository(session)
    items = await repo.list_visible(user_id=None)

    assert items == []
    params = session.execute.await_args.args[1]
    assert params["user_id"] is None


@pytest.mark.asyncio
async def test_agent_skill_search_visible_uses_bigint_cast_with_empty_query():
    session = DummySession()
    session.execute.return_value = FakeMappingResult([])

    repo = AgentSkillRepository(session)
    items = await repo.search_visible(user_id=1, query_text="", limit=20)

    assert items == []
    statement = session.execute.await_args.args[0]
    assert "owner_user_id = CAST(:user_id AS BIGINT)" in str(statement)
    params = session.execute.await_args.args[1]
    assert params["query_text"] == ""


@pytest.mark.asyncio
async def test_agent_skill_list_catalog_paginated_uses_bigint_cast_with_null_user():
    session = DummySession()
    session.execute = AsyncMock(
        side_effect=[
            FakeScalarResult(1),
            FakeMappingResult(
                [
                    {
                        "skill_id": 1,
                        "skill_key": "builtin:organizeByType",
                        "name": "organizeByType",
                        "description": "Organize files by type",
                        "triggers_text": "organize, classify",
                        "tool_whitelist_json": ["drive.listFolder"],
                        "plan_template_json": {},
                        "inputs_schema_json": {},
                        "outputs_schema_json": {},
                        "visibility": "global",
                        "owner_user_id": None,
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                        "search_text": "organize files by type",
                    }
                ]
            ),
        ]
    )

    repo = AgentSkillRepository(session)
    items, total_items = await repo.list_catalog_paginated(
        user_id=None,
        visibility="all",
        query_text="",
        page=1,
        per_page=20,
    )

    assert total_items == 1
    assert [item.skill_key for item in items] == ["builtin:organizeByType"]
    count_statement = session.execute.await_args_list[0].args[0]
    list_statement = session.execute.await_args_list[1].args[0]
    assert "owner_user_id = CAST(:user_id AS BIGINT)" in str(count_statement)
    assert "owner_user_id = CAST(:user_id AS BIGINT)" in str(list_statement)
    params = session.execute.await_args_list[1].args[1]
    assert params["query_text"] == ""
    assert params["offset"] == 0
    assert params["limit"] == 20


@pytest.mark.asyncio
async def test_agent_mcp_list_visible_maps_catalog_rows():
    session = DummySession()
    session.execute.return_value = FakeMappingResult(
        [
            {
                "mcp_server_id": 1,
                "name": "web-search",
                "description": "System MCP",
                "endpoint": "https://mcp.example.com",
                "transport": "streamable_http",
                "auth_type": "none",
                "headers_json": {},
                "tool_namespace": "web",
                "enabled": True,
                "metadata_json": {},
                "visibility": "system",
                "owner_user_id": None,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
            {
                "mcp_server_id": 2,
                "name": "private-python",
                "description": None,
                "endpoint": "http://localhost:9001",
                "transport": "stdio",
                "auth_type": "none",
                "headers_json": {},
                "tool_namespace": None,
                "enabled": True,
                "metadata_json": {},
                "visibility": "private",
                "owner_user_id": 7,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        ]
    )

    repo = AgentMcpRepository(session)
    items = await repo.list_visible(user_id=7)
    assert [item.name for item in items] == ["web-search", "private-python"]
    statement = session.execute.await_args.args[0]
    assert "owner_user_id = CAST(:user_id AS BIGINT)" in str(statement)


@pytest.mark.asyncio
async def test_agent_mcp_list_visible_accepts_null_user_id():
    session = DummySession()
    session.execute.return_value = FakeMappingResult([])

    repo = AgentMcpRepository(session)
    items = await repo.list_visible(user_id=None)

    assert items == []
    params = session.execute.await_args.args[1]
    assert params["user_id"] is None


@pytest.mark.asyncio
async def test_agent_memory_search_maps_active_rows():
    session = DummySession()
    now = datetime.now(UTC)
    session.execute.return_value = FakeMappingResult(
        [
            {
                "memory_id": 11,
                "user_id": 7,
                "scope": "workspace",
                "scope_key": "fld_projects",
                "kind": "preference",
                "title": "Naming rule",
                "content": "Use YYYY-Q1-Project",
                "source_job_id": None,
                "created_at": now,
                "updated_at": now,
                "expires_at": None,
            }
        ]
    )

    repo = AgentMemoryRepository(session)
    items = await repo.search_active(user_id=7, query_text="naming", scope="workspace", scope_key="fld_projects")
    assert len(items) == 1
    assert items[0].scope == "workspace"
    assert items[0].scope_key == "fld_projects"


@pytest.mark.asyncio
async def test_agent_plan_get_for_execute_binding_uses_job_user_and_hash():
    session = DummySession()
    expected = SimpleNamespace(plan_hash="sha256:abc")
    session.scalar.return_value = expected

    repo = AgentPlanRepository(session)
    result = await repo.get_for_execute_binding(job_id=99, user_id=7, plan_hash="sha256:abc")
    statement = session.scalar.await_args.args[0]

    assert result is expected
    assert "agent_plan.job_id" in str(statement)
    assert "agent_plan.user_id" in str(statement)
    assert "agent_plan.plan_hash" in str(statement)


@pytest.mark.asyncio
async def test_agent_action_log_finish_refreshes_work_session_metrics():
    session = DummySession()
    entry = SimpleNamespace(
        outputs_json={},
        status="running",
        duration_ms=None,
        error_message=None,
        finished_at=None,
    )
    session.scalar = AsyncMock(side_effect=[entry, 88])
    repo = AgentActionLogRepository(session)

    result = await repo.finish_step(
        job_id=101,
        step_no=3,
        outputs_json={"ok": True},
        status="failed",
        duration_ms=42,
        error_message="boom",
    )

    assert result is entry
    assert entry.outputs_json == {"ok": True}
    assert entry.status == "failed"
    assert entry.duration_ms == 42
    assert entry.error_message == "boom"
    session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_agent_action_log_append_step_normalizes_datetime_inputs():
    session = DummySession()
    session.scalar = AsyncMock(return_value=88)
    captured: list[SimpleNamespace] = []

    def add(entry: SimpleNamespace) -> None:
        captured.append(entry)

    session.add = Mock(side_effect=add)
    repo = AgentActionLogRepository(session)
    now = datetime.now(UTC)

    await repo.append_step(
        job_id=101,
        step_no=1,
        tool_name="drive.createFolder",
        inputs_json={"createdAt": now},
        status="running",
    )

    assert captured
    saved = captured[0]
    assert isinstance(saved.inputs_json["createdAt"], str)
    assert saved.inputs_json["createdAt"] == now.isoformat()


@pytest.mark.asyncio
async def test_agent_action_log_finish_step_normalizes_datetime_outputs():
    session = DummySession()
    entry = SimpleNamespace(
        outputs_json={},
        status="running",
        duration_ms=None,
        error_message=None,
        finished_at=None,
    )
    session.scalar = AsyncMock(side_effect=[entry, 88])
    repo = AgentActionLogRepository(session)
    now = datetime.now(UTC)

    await repo.finish_step(
        job_id=101,
        step_no=2,
        outputs_json={"updatedAt": now},
        status="succeeded",
        duration_ms=5,
    )

    assert isinstance(entry.outputs_json["updatedAt"], str)
    assert entry.outputs_json["updatedAt"] == now.isoformat()


@pytest.mark.asyncio
async def test_agent_work_session_refresh_metrics_executes_db_function():
    session = DummySession()
    work_session = SimpleNamespace(work_session_id=5)
    session.get.return_value = work_session

    repo = AgentWorkSessionRepository(session)
    result = await repo.refresh_metrics(work_session_id=5)

    assert result is work_session
    session.execute.assert_awaited()
    session.get.assert_awaited_once_with(AgentWorkSession, 5)


def test_agent_scaffold_modules_are_importable():
    assert PromptBuilder is not None
    assert PlanRunner is not None
