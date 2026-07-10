from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from fileflash.agents.harness.event_bus import AgentEventEnvelope
from fileflash.agents.harness.router import ToolCall, ToolRouter
from fileflash.agents.runtime import execute_runner as execute_module
from fileflash.agents.runtime import plan_runner as plan_module
from fileflash.agents.runtime.execute_runner import AgentJobCanceled, ExecuteRunner
from fileflash.agents.runtime.llm import AnthropicPlannerClient
from fileflash.agents.runtime.plan_runner import PlanRunner
from fileflash.core.errors import ApiError
from fileflash.models import BackgroundJob
from fileflash.models.enums import AgentInboxKind
from fileflash.repositories import (
    AgentPlanRepository,
    AgentSettingsRepository,
    AgentWorkSessionRepository,
)
from fileflash.schemas.agent import ExecuteAgentRequest, PlanAgentRequest
from fileflash.services.agent.execute_service import ExecuteService
from fileflash.services.agent.plan_service import PlanService


class DummyDb:
    def __init__(self) -> None:
        self.scalar = AsyncMock(return_value=None)
        self.execute = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.add = AsyncMock()
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.refresh = AsyncMock()


class FakeJobs:
    def __init__(self) -> None:
        self.kwargs = {}

    async def enqueue(self, db, **kwargs):  # noqa: ANN001
        self.kwargs = kwargs
        return BackgroundJob(
            job_id=123,
            task_type=kwargs["task_type"],
            status="pending",
            payload=kwargs["payload"],
            result={},
            requested_by=kwargs["requested_by"],
            max_attempts=kwargs["max_attempts"],
            priority=kwargs["priority"],
            scheduled_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


class FakeChatSessions:
    async def get_active(self, **_kwargs):  # noqa: ANN003
        return SimpleNamespace(chat_session_id=1, user_id=7, deleted_at=None)


def settings(**overrides):
    base = {
        "agent_enabled": True,
        "agent_job_max_tokens": 50_000,
        "agent_job_max_tool_calls": 100,
        "is_development_env": False,
        "agent_user_concurrent_limit": 2,
        "agent_user_daily_limit": 50,
        "agent_llm_base_url": None,
        "agent_llm_plan_max_tokens": 8192,
        "agent_skill_candidate_k": 3,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_plan_enqueue_returns_frontend_shape_and_sets_phase():
    db = DummyDb()
    db.scalar = AsyncMock(side_effect=[0, 0])
    jobs = FakeJobs()
    service = PlanService(
        db=db,
        settings=settings(),
        jobs=jobs,  # type: ignore[arg-type]
        plans=AgentPlanRepository(db),  # type: ignore[arg-type]
        settings_repo=AgentSettingsRepository(db),  # type: ignore[arg-type]
        work_sessions=AgentWorkSessionRepository(db),  # type: ignore[arg-type]
        chat_sessions=FakeChatSessions(),  # type: ignore[arg-type]
    )
    payload = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "整理当前文件夹",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
            "dataPolicy": {
                "allowFileContent": False,
                "maxReadBytes": 1024,
                "allowedMimeTypes": ["*/*"],
            },
            "hints": {
                "preferSkillId": None,
                "maxSteps": 12,
                "budgetTokens": 8000,
                "reasoningEffort": "adaptive",
            },
        }
    )

    result = await service.enqueue_plan(user_id=7, payload=payload)

    assert result.job_id == "123"
    assert result.task_type == "agent.plan"
    assert jobs.kwargs["agent_phase"] == "planning"
    assert jobs.kwargs["payload"]["executionPolicy"] == "confirm"
    assert jobs.kwargs["payload"]["hints"]["reasoningEffort"] == "adaptive"


@pytest.mark.asyncio
async def test_plan_enqueue_rejects_max_steps_above_server_limit_in_non_dev():
    db = DummyDb()
    jobs = FakeJobs()
    service = PlanService(
        db=db,
        settings=settings(),
        jobs=jobs,  # type: ignore[arg-type]
        plans=AgentPlanRepository(db),  # type: ignore[arg-type]
        settings_repo=AgentSettingsRepository(db),  # type: ignore[arg-type]
        work_sessions=AgentWorkSessionRepository(db),  # type: ignore[arg-type]
        chat_sessions=FakeChatSessions(),  # type: ignore[arg-type]
    )
    payload = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "整理当前文件夹",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
            "hints": {
                "preferSkillId": None,
                "maxSteps": 101,
                "budgetTokens": 8000,
                "reasoningEffort": "adaptive",
            },
        }
    )

    with pytest.raises(ApiError) as exc:
        await service.enqueue_plan(user_id=7, payload=payload)

    assert exc.value.status_code == 400
    assert exc.value.message == "Agent maxSteps exceeds server limit"


@pytest.mark.asyncio
async def test_plan_enqueue_allows_max_steps_above_server_limit_in_dev():
    db = DummyDb()
    db.scalar = AsyncMock(side_effect=[0, 0])
    jobs = FakeJobs()
    service = PlanService(
        db=db,
        settings=settings(is_development_env=True),
        jobs=jobs,  # type: ignore[arg-type]
        plans=AgentPlanRepository(db),  # type: ignore[arg-type]
        settings_repo=AgentSettingsRepository(db),  # type: ignore[arg-type]
        work_sessions=AgentWorkSessionRepository(db),  # type: ignore[arg-type]
        chat_sessions=FakeChatSessions(),  # type: ignore[arg-type]
    )
    payload = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "整理当前文件夹",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
            "hints": {
                "preferSkillId": None,
                "maxSteps": 5000,
                "budgetTokens": 8000,
                "reasoningEffort": "adaptive",
            },
        }
    )

    result = await service.enqueue_plan(user_id=7, payload=payload)

    assert result.job_id == "123"
    assert jobs.kwargs["payload"]["hints"]["maxSteps"] == 5000


@pytest.mark.asyncio
async def test_anthropic_planner_client_uses_sdk_and_parses_text_blocks():
    class FakeMessages:
        def __init__(self) -> None:
            self.kwargs = {}

        async def create(self, **kwargs):  # noqa: ANN003
            self.kwargs = kwargs
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text='{"summary":"ok","proposedActions":[]}',
                    )
                ],
                usage=SimpleNamespace(input_tokens=3, output_tokens=4),
            )

    fake_messages = FakeMessages()
    fake_client = SimpleNamespace(messages=fake_messages)
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=fake_client,  # type: ignore[arg-type]
    )

    result = await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=9000,
        reasoning_effort="adaptive",
    )

    assert fake_messages.kwargs["model"] == "claude-test"
    assert fake_messages.kwargs["max_tokens"] == 8192
    assert fake_messages.kwargs["system"] == "system"
    assert fake_messages.kwargs["messages"] == [{"role": "user", "content": "user"}]
    assert fake_messages.kwargs["thinking"] == {"type": "adaptive"}
    assert "output_config" not in fake_messages.kwargs
    assert result["summary"] == "ok"
    assert result["_usage"] == {"input_tokens": 3, "output_tokens": 4}


@pytest.mark.asyncio
async def test_anthropic_planner_client_maps_reasoning_effort_to_output_config():
    class FakeMessages:
        def __init__(self) -> None:
            self.kwargs = {}

        async def create(self, **kwargs):  # noqa: ANN003
            self.kwargs = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text='{"proposedActions":[]}')],
                usage={},
            )

    fake_messages = FakeMessages()
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=fake_messages),  # type: ignore[arg-type]
    )

    await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=800,
        reasoning_effort="xhigh",
    )

    assert fake_messages.kwargs["max_tokens"] == 800
    assert fake_messages.kwargs["thinking"] == {"type": "enabled"}
    assert fake_messages.kwargs["output_config"] == {"effort": "xhigh"}


@pytest.mark.asyncio
async def test_anthropic_planner_client_retries_without_reasoning_on_empty_output():
    class FakeMessages:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def create(self, **kwargs):  # noqa: ANN003
            self.calls.append(dict(kwargs))
            if len(self.calls) == 1:
                return SimpleNamespace(
                    content=[SimpleNamespace(type="thinking", thinking="...")],
                    usage={},
                )
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text='{"summary":"fallback","proposedActions":[]}')],
                usage={},
            )

    fake_messages = FakeMessages()
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=fake_messages),  # type: ignore[arg-type]
    )

    result = await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=1024,
        reasoning_effort="high",
    )

    assert len(fake_messages.calls) == 2
    assert "thinking" in fake_messages.calls[0]
    assert "output_config" in fake_messages.calls[0]
    assert "thinking" not in fake_messages.calls[1]
    assert "output_config" not in fake_messages.calls[1]
    assert result["summary"] == "fallback"


@pytest.mark.asyncio
async def test_anthropic_planner_client_retries_with_json_only_prompt_on_invalid_json():
    class FakeMessages:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def create(self, **kwargs):  # noqa: ANN003
            self.calls.append(dict(kwargs))
            if len(self.calls) == 1:
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text="I think we should move files.")],
                    usage={},
                )
            if len(self.calls) == 2:
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text="summary: move files")],
                    usage={},
                )
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text='{"summary":"strict","proposedActions":[]}')],
                usage={},
            )

    fake_messages = FakeMessages()
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=fake_messages),  # type: ignore[arg-type]
    )

    result = await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=1024,
        reasoning_effort="high",
    )

    assert len(fake_messages.calls) == 3
    assert "thinking" in fake_messages.calls[0]
    assert "output_config" in fake_messages.calls[0]
    assert "thinking" not in fake_messages.calls[1]
    assert "output_config" not in fake_messages.calls[1]
    assert "thinking" not in fake_messages.calls[2]
    assert "output_config" not in fake_messages.calls[2]
    assert fake_messages.calls[1]["max_tokens"] == 1024
    assert fake_messages.calls[2]["max_tokens"] == 8192
    third_messages = fake_messages.calls[2]["messages"]
    assert isinstance(third_messages, list)
    assert "Return ONLY one valid JSON object" in third_messages[0]["content"]
    assert result["summary"] == "strict"


@pytest.mark.asyncio
async def test_anthropic_planner_client_parses_json_from_wrapped_text():
    class FakeMessages:
        async def create(self, **kwargs):  # noqa: ANN003
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text='Here is the result:\n{"summary":"ok","proposedActions":[]}\nThanks!',
                    )
                ],
                usage={},
            )

    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=FakeMessages()),  # type: ignore[arg-type]
    )

    result = await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=1000,
    )

    assert result["summary"] == "ok"
    assert result["proposedActions"] == []


@pytest.mark.asyncio
async def test_anthropic_planner_client_raises_after_three_invalid_json_responses():
    class FakeMessages:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def create(self, **kwargs):  # noqa: ANN003
            self.calls.append(dict(kwargs))
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="not valid json")],
                usage={},
            )

    fake_messages = FakeMessages()
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=fake_messages),  # type: ignore[arg-type]
    )

    with pytest.raises(ApiError) as exc:
        await client.create_plan(
            system_prompt="system",
            user_prompt="user",
            max_tokens=1024,
            reasoning_effort="high",
        )

    assert exc.value.status_code == 502
    assert exc.value.message == "Agent LLM did not return valid JSON"
    assert len(fake_messages.calls) == 3


@pytest.mark.asyncio
async def test_anthropic_planner_client_uses_tools_and_parses_tool_use_blocks():
    class FakeMessages:
        def __init__(self) -> None:
            self.kwargs = {}

        async def create(self, **kwargs):  # noqa: ANN003
            self.kwargs = kwargs
            return SimpleNamespace(
                content=[
                    SimpleNamespace(type="text", text="Count matching videos."),
                    SimpleNamespace(
                        type="tool_use",
                        id="toolu_1",
                        name="drive_count_files",
                        input={"folderId": "root", "category": "video"},
                    ),
                ],
                usage={"input_tokens": 5, "output_tokens": 6},
            )

    fake_messages = FakeMessages()
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=fake_messages),  # type: ignore[arg-type]
    )

    result = await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=1024,
        tools=[
            {
                "name": "drive_count_files",
                "description": "Count files.",
                "input_schema": {"type": "object"},
                "internalName": "drive.countFiles",
            }
        ],
    )

    assert fake_messages.kwargs["tool_choice"] == {"type": "auto"}
    assert fake_messages.kwargs["tools"] == [
        {
            "name": "drive_count_files",
            "description": "Count files.",
            "input_schema": {"type": "object"},
        }
    ]
    assert result["summary"] == "Count matching videos."
    assert result["proposedActions"] == [
        {
            "step": 1,
            "tool": "drive.countFiles",
            "input": {"folderId": "root", "category": "video"},
        }
    ]
    assert result["_usage"] == {"input_tokens": 5, "output_tokens": 6}


@pytest.mark.asyncio
async def test_anthropic_planner_client_executes_tool_loop_before_final_plan():
    class FakeMessages:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def create(self, **kwargs):  # noqa: ANN003
            self.calls.append(dict(kwargs))
            if len(self.calls) == 1:
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(type="text", text="Need to inspect candidates first."),
                        SimpleNamespace(
                            type="tool_use",
                            id="toolu_1",
                            name="drive_search_files",
                            input={"folderId": "root", "query": "银翼杀手", "category": "video"},
                        ),
                    ],
                    usage={"input_tokens": 10, "output_tokens": 5},
                )
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text=(
                            '{"summary":"move matched file","proposedActions":['
                            '{"step":1,"tool":"drive.moveFile","input":{"fileId":"11","targetFolderId":"21"}}'
                            "]}"
                        ),
                    )
                ],
                usage={"input_tokens": 8, "output_tokens": 9},
            )

    fake_messages = FakeMessages()
    tool_executor = AsyncMock(return_value={"items": [{"id": "11", "name": "银翼杀手2049.mp4"}], "totalItems": 1})
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
        ),
        client=SimpleNamespace(messages=fake_messages),  # type: ignore[arg-type]
    )

    result = await client.create_plan(
        system_prompt="system",
        user_prompt="user",
        max_tokens=1024,
        tools=[
            {
                "name": "drive_search_files",
                "description": "Search files.",
                "input_schema": {"type": "object"},
                "internalName": "drive.searchFiles",
            },
            {
                "name": "drive_move_file",
                "description": "Move file.",
                "input_schema": {"type": "object"},
                "internalName": "drive.moveFile",
            },
        ],
        tool_executor=tool_executor,
        max_tool_roundtrips=4,
    )

    tool_executor.assert_awaited_once_with(
        "drive.searchFiles",
        {"folderId": "root", "query": "银翼杀手", "category": "video"},
    )
    assert len(fake_messages.calls) == 2
    second_messages = fake_messages.calls[1]["messages"]
    assert isinstance(second_messages, list)
    tool_result_blocks = second_messages[-1]["content"]
    assert isinstance(tool_result_blocks, list)
    assert tool_result_blocks[0]["type"] == "tool_result"
    assert result["summary"] == "move matched file"
    assert result["proposedActions"][0]["tool"] == "drive.moveFile"
    assert result["_usage"] == {"input_tokens": 18, "output_tokens": 14}


def test_anthropic_planner_client_uses_configured_base_url(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_async_anthropic(**kwargs):  # noqa: ANN003
        captured.update(kwargs)
        return SimpleNamespace(messages=SimpleNamespace())

    monkeypatch.setattr("fileflash.agents.runtime.llm.AsyncAnthropic", fake_async_anthropic)
    client = AnthropicPlannerClient(
        settings=settings(
            agent_llm_api_key="test-key",
            agent_llm_model="claude-test",
            agent_llm_base_url="https://api.deepseek.com/anthropic",
        ),
    )

    assert client._get_client("test-key").messages is not None
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://api.deepseek.com/anthropic"


@pytest.mark.asyncio
async def test_execute_rejects_high_risk_plan_without_confirmation():
    db = DummyDb()
    db.scalar.return_value = BackgroundJob(
        job_id=99,
        task_type="agent.plan",
        status="succeeded",
        payload={},
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    plans = AgentPlanRepository(db)  # type: ignore[arg-type]
    plans.get_for_execute_binding = AsyncMock(
        return_value=SimpleNamespace(
            proposed_actions_json=[
                {
                    "step": 1,
                    "tool": "drive.deleteFile",
                    "input": {"fileId": "1"},
                    "sideEffect": "write",
                    "riskLevel": "high",
                    "requiresConfirmation": True,
                }
            ]
        )
    )
    service = ExecuteService(
        db=db,
        settings=settings(),
        jobs=FakeJobs(),  # type: ignore[arg-type]
        plans=plans,
        work_sessions=AgentWorkSessionRepository(db),  # type: ignore[arg-type]
        chat_sessions=FakeChatSessions(),  # type: ignore[arg-type]
    )
    payload = ExecuteAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "planJobId": "99",
            "planHash": "sha256:test",
            "approval": {"confirmedBy": "7", "confirmedAt": datetime.now(UTC).isoformat()},
        }
    )

    with pytest.raises(ApiError) as exc:
        await service.enqueue_execute(user_id=7, payload=payload)

    assert exc.value.status_code == 409
    assert exc.value.data["highRiskActions"][0]["tool"] == "drive.deleteFile"


@pytest.mark.asyncio
async def test_execute_enqueue_serializes_approval_datetime_as_json_string():
    db = DummyDb()
    plan_job = BackgroundJob(
        job_id=99,
        task_type="agent.plan",
        status="succeeded",
        payload={},
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.scalar = AsyncMock(side_effect=[plan_job, None])
    plans = AgentPlanRepository(db)  # type: ignore[arg-type]
    plans.get_for_execute_binding = AsyncMock(return_value=SimpleNamespace(proposed_actions_json=[]))
    jobs = FakeJobs()
    service = ExecuteService(
        db=db,
        settings=settings(),
        jobs=jobs,  # type: ignore[arg-type]
        plans=plans,
        work_sessions=AgentWorkSessionRepository(db),  # type: ignore[arg-type]
        chat_sessions=FakeChatSessions(),  # type: ignore[arg-type]
    )
    payload = ExecuteAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "planJobId": "99",
            "planHash": "sha256:test",
            "approval": {"confirmedBy": "7", "confirmedAt": "2026-05-25T10:00:00Z"},
        }
    )

    await service.enqueue_execute(user_id=7, payload=payload)

    approval_payload = jobs.kwargs["payload"]["approval"]
    assert isinstance(approval_payload["confirmedAt"], str)
    assert approval_payload["confirmedAt"] == "2026-05-25T10:00:00Z"
    assert jobs.kwargs["idempotency_key"] == "agent.execute:99"


@pytest.mark.asyncio
async def test_execute_rejects_repeat_when_existing_execute_job_exists():
    db = DummyDb()
    plan_job = BackgroundJob(
        job_id=99,
        task_type="agent.plan",
        status="succeeded",
        payload={},
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    existing_execute = BackgroundJob(
        job_id=200,
        task_type="agent.execute",
        status="running",
        payload={},
        result={},
        requested_by=7,
        idempotency_key="agent.execute:99",
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.scalar = AsyncMock(side_effect=[plan_job, existing_execute])
    plans = AgentPlanRepository(db)  # type: ignore[arg-type]
    plans.get_for_execute_binding = AsyncMock(return_value=SimpleNamespace(proposed_actions_json=[]))
    jobs = FakeJobs()
    service = ExecuteService(
        db=db,
        settings=settings(),
        jobs=jobs,  # type: ignore[arg-type]
        plans=plans,
        work_sessions=AgentWorkSessionRepository(db),  # type: ignore[arg-type]
        chat_sessions=FakeChatSessions(),  # type: ignore[arg-type]
    )
    payload = ExecuteAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "planJobId": "99",
            "planHash": "sha256:test",
            "approval": {"confirmedBy": "7", "confirmedAt": "2026-05-25T10:00:00Z"},
        }
    )

    with pytest.raises(ApiError) as exc:
        await service.enqueue_execute(user_id=7, payload=payload)

    assert exc.value.status_code == 409
    assert "already been executed" in exc.value.message.lower() or "already" in exc.value.message.lower()
    assert exc.value.data["jobId"] == "200"
    assert jobs.kwargs == {}


@pytest.mark.asyncio
async def test_plan_runner_generates_stable_hash(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    planner = AsyncMock(
        return_value={
            "summary": "Move files into folders.",
            "proposedActions": [
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "1", "targetFolderId": "2"},
                },
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "Docs"},
                }
            ],
        }
    )
    client = SimpleNamespace(create_plan=planner)
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "autopilot",
            "dataPolicy": {
                "allowFileContent": False,
                "maxReadBytes": 1024,
                "allowedMimeTypes": ["*/*"],
            },
            "hints": {
                "preferSkillId": None,
                "maxSteps": 12,
                "budgetTokens": 8000,
                "reasoningEffort": "high",
            },
        }
    )
    job = BackgroundJob(
        job_id=321,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    runner = PlanRunner(settings=settings(), planner_client=client)  # type: ignore[arg-type]

    first = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]
    second = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert first.plan_hash == second.plan_hash
    assert first.requires_confirmation is False
    assert [action.step for action in first.proposed_actions] == [1, 2]
    assert "reasoningEffort" in planner.await_args.kwargs["user_prompt"]


@pytest.mark.asyncio
async def test_plan_runner_ignores_requested_max_steps_in_dev(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    planner = AsyncMock(
        return_value={
            "summary": "Move files into folders.",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "Docs"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "1", "targetFolderId": "2"},
                },
            ],
        }
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "autopilot",
            "hints": {
                "preferSkillId": None,
                "maxSteps": 1,
                "budgetTokens": 8000,
                "reasoningEffort": "adaptive",
            },
        }
    )
    job = BackgroundJob(
        job_id=3221,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    runner = PlanRunner(
        settings=settings(is_development_env=True),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert len(result.proposed_actions) == 2
    assert [action.step for action in result.proposed_actions] == [1, 2]


@pytest.mark.asyncio
async def test_plan_runner_commits_after_upsert(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(return_value={"summary": "ok", "proposedActions": []})
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
        }
    )
    job = BackgroundJob(
        job_id=321,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDb()

    await runner.run(db=db, job=job)  # type: ignore[arg-type]

    db.commit.assert_awaited_once()
    db.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_plan_runner_rolls_back_when_commit_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(return_value={"summary": "ok", "proposedActions": []})
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
        }
    )
    job = BackgroundJob(
        job_id=322,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDb()
    db.commit.side_effect = RuntimeError("commit failed")

    with pytest.raises(RuntimeError, match="commit failed"):
        await runner.run(db=db, job=job)  # type: ignore[arg-type]

    db.commit.assert_awaited_once()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_plan_runner_propagates_llm_output_errors_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(
        side_effect=ApiError(
            status_code=502,
            code=502,
            message="Agent LLM returned an empty response",
        )
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "autopilot",
        }
    )
    job = BackgroundJob(
        job_id=333,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDb()

    with pytest.raises(ApiError) as exc:
        await runner.run(db=db, job=job)  # type: ignore[arg-type]
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_plan_runner_asks_then_replans_when_plan_is_not_executable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    ask_mock = AsyncMock(return_value={"clarification": "Use the current folder."})
    monkeypatch.setattr(PlanRunner, "_ask", ask_mock)

    planner = AsyncMock(
        side_effect=[
            {"summary": "not executable"},
            {"summary": "ok", "proposedActions": []},
        ]
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
        }
    )
    job = BackgroundJob(
        job_id=331,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert result.summary == "ok"
    assert planner.await_count == 2
    ask_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_plan_runner_uses_planner_returned_count_action_for_movie_question(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(
        return_value={
            "summary": "count videos",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.countFiles",
                    "input": {"folderId": "root", "recursive": True, "category": "video"},
                }
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "我上传了多少部电影？",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=334,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert len(result.proposed_actions) == 1
    assert result.proposed_actions[0].tool == "drive.countFiles"
    assert result.proposed_actions[0].input["category"] == "video"
    assert result.proposed_actions[0].side_effect == "read"


@pytest.mark.asyncio
async def test_plan_runner_uses_planner_returned_count_action_for_anime_question(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(
        return_value={
            "summary": "count anime videos",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.countFiles",
                    "input": {"folderId": "root", "recursive": True, "category": "video"},
                }
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "我上传了多少动漫？",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=336,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert action.tool == "drive.countFiles"
    assert action.input["category"] == "video"
    assert action.input.get("search") in (None, "")


@pytest.mark.asyncio
async def test_plan_runner_delegates_count_question_with_search_term_to_planner(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(
        return_value={
            "summary": "count matching movies",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.countFiles",
                    "input": {
                        "folderId": "root",
                        "recursive": True,
                        "category": "video",
                        "search": "银翼杀手",
                    },
                }
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "我上传了几部银翼杀手？",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=335,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    planner.assert_awaited_once()
    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert action.tool == "drive.countFiles"
    assert action.input["category"] == "video"
    assert action.input["search"] == "银翼杀手"
    assert action.side_effect == "read"


@pytest.mark.asyncio
async def test_plan_runner_blocks_write_tool_in_exploratory_loop_and_continues(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    dispatch_mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(
        plan_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(dispatch=dispatch_mock),
    )

    async def fake_create_plan(**kwargs):  # noqa: ANN003
        tool_executor = kwargs["tool_executor"]
        blocked = await tool_executor("drive.createFolder", {"parentFolderId": "root", "name": "Movies"})
        assert blocked["_plannerBlocked"] is True
        assert blocked["_toolError"] is True
        assert blocked["tool"] == "drive.createFolder"
        return {
            "summary": "create then move",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "Movies"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "1", "targetFolderId": "$step1.folderId"},
                },
            ],
        }

    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=fake_create_plan),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "整理文件",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=340,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]
    assert len(result.proposed_actions) == 2
    assert result.proposed_actions[0].tool == "drive.createFolder"
    assert result.proposed_actions[1].input["targetFolderId"] == "$step1.folderId"
    dispatch_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_runner_passes_only_read_tools_to_planner_tool_use(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    captured_tools: list[dict[str, Any]] = []

    async def fake_create_plan(**kwargs):  # noqa: ANN003
        nonlocal captured_tools
        tools = kwargs.get("tools")
        if isinstance(tools, list):
            captured_tools = list(tools)
        return {"summary": "ok", "proposedActions": []}

    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=fake_create_plan),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "整理当前文件夹",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=341,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert captured_tools
    internal_names = {str(item.get("internalName") or "") for item in captured_tools}
    assert "drive.createFolder" not in internal_names
    assert "drive.moveFile" not in internal_names
    for internal_name in internal_names:
        assert plan_module.REGISTRY.get(internal_name).side_effect == "read"


@pytest.mark.asyncio
async def test_plan_runner_uses_planner_returned_move_action_when_unique_matches(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    planner = AsyncMock(
        return_value={
            "summary": "move one matching file",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "11", "targetFolderId": "21", "shareHandling": "keep"},
                }
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "把银翼杀手电影放到银翼杀手文件夹下",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=337,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert action.tool == "drive.moveFile"
    assert action.input["fileId"] == "11"
    assert action.input["targetFolderId"] == "21"
    assert action.side_effect == "write"


@pytest.mark.asyncio
async def test_plan_runner_uses_planner_returned_create_then_move_when_target_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    planner = AsyncMock(
        return_value={
            "summary": "create missing folder then move",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "银翼杀手"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "11", "targetFolderId": "$step1.folderId"},
                },
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "把银翼杀手电影放到银翼杀手文件夹下",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=338,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert len(result.proposed_actions) == 2
    assert result.proposed_actions[0].tool == "drive.createFolder"
    assert result.proposed_actions[0].input["name"] == "银翼杀手"
    assert result.proposed_actions[1].tool == "drive.moveFile"
    assert result.proposed_actions[1].input["fileId"] == "11"
    assert result.proposed_actions[1].input["targetFolderId"] == "$step1.folderId"


@pytest.mark.asyncio
async def test_plan_runner_rewrites_write_summary_with_grounded_facts(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    planner = AsyncMock(
        return_value={
            "summary": "创建银翼杀手文件夹，然后将 V字仇杀队 文件夹中的2部银翼杀手电影移入该文件夹。",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "银翼杀手"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "19", "targetFolderId": "$step1.folderId"},
                },
                {
                    "step": 3,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "20", "targetFolderId": "$step1.folderId"},
                },
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "把银翼杀手两部，移到银翼杀手文件夹里",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=348,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDb()

    class _Rows:
        def __init__(self, rows: list[tuple[Any, Any]]) -> None:
            self._rows = rows

        def all(self) -> list[tuple[Any, Any]]:
            return list(self._rows)

    db.execute = AsyncMock(return_value=_Rows([(19, "银翼杀手1982.mp4"), (20, "银翼杀手2049.mp4")]))

    result = await runner.run(db=db, job=job)  # type: ignore[arg-type]

    assert "V字仇杀队" not in result.summary
    assert "创建“银翼杀手”文件夹" in result.summary
    assert "2 个文件" in result.summary


@pytest.mark.asyncio
async def test_plan_runner_records_planning_evidence_from_read_tools(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    class _FakeToolRouter:
        async def dispatch(self, _call):  # noqa: ANN001
            return {
                "items": [
                    {"fileId": "19", "name": "银翼杀手1982.mp4", "path": "/My Files/videos/银翼杀手1982.mp4"},
                    {"fileId": "20", "name": "银翼杀手2049.mp4", "path": "/My Files/videos/银翼杀手2049.mp4"},
                    {"fileId": "21", "name": "Blade Runner Trailer.mp4", "path": "/My Files/videos/Blade Runner Trailer.mp4"},
                    {"fileId": "22", "name": "x1.mp4", "path": "/My Files/videos/x1.mp4"},
                    {"fileId": "23", "name": "x2.mp4", "path": "/My Files/videos/x2.mp4"},
                    {"fileId": "24", "name": "x3.mp4", "path": "/My Files/videos/x3.mp4"},
                    {"fileId": "25", "name": "x4.mp4", "path": "/My Files/videos/x4.mp4"},
                ],
                "totalItems": 7,
                "query": "银翼杀手",
                "folderId": "1",
                "recursive": True,
                "category": "video",
            }

    monkeypatch.setattr(plan_module, "ToolRouter", lambda **kwargs: _FakeToolRouter())

    async def _planner_with_read_tool(**kwargs):  # noqa: ANN003
        tool_executor = kwargs["tool_executor"]
        await tool_executor(
            "drive.searchFiles",
            {"folderId": "root", "query": "银翼杀手", "category": "video"},
        )
        return {
            "summary": "search first",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.searchFiles",
                    "input": {"folderId": "root", "query": "银翼杀手", "category": "video"},
                }
            ],
        }

    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=_planner_with_read_tool),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "找出银翼杀手视频文件",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=349,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert result.planning_evidence is not None
    assert len(result.planning_evidence) == 1
    evidence = result.planning_evidence[0]
    assert evidence.step == 1
    assert evidence.tool == "drive.searchFiles"
    assert evidence.input["query"] == "银翼杀手"
    assert evidence.output_preview["totalItems"] == 7
    assert isinstance(evidence.output_preview.get("items"), list)
    assert "..." in str(evidence.output_preview["items"][-1])


@pytest.mark.asyncio
async def test_plan_runner_uses_planner_returned_read_only_candidates_when_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_candidate_skills", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))
    planner = AsyncMock(
        return_value={
            "summary": "ambiguous, return candidates",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.searchFiles",
                    "input": {"folderId": "root", "query": "银翼杀手", "category": "video"},
                }
            ],
        }
    )
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "把银翼杀手电影放到银翼杀手文件夹下",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=339,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert action.tool == "drive.searchFiles"
    assert action.side_effect == "read"
    assert "ambiguous" in result.summary


@pytest.mark.asyncio
async def test_plan_runner_injects_skill_menu_and_use_skill_tool(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_candidate = SimpleNamespace(
        skill_key="organizeByType",
        name="Organize by Type",
        description="Organize files by type",
        triggers_text="organize",
        tool_whitelist_json=["drive.listFolder", "drive.moveFile"],
        plan_template_json={},
        search_text="organize",
    )
    monkeypatch.setattr(
        plan_module, "_candidate_skills", AsyncMock(return_value=[fake_candidate])
    )
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    captured: dict[str, Any] = {}

    async def fake_create_plan(**kwargs):  # noqa: ANN003
        captured["tools"] = kwargs.get("tools")
        captured["system_prompt"] = kwargs.get("system_prompt")
        return {"summary": "ok", "proposedActions": []}

    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=fake_create_plan),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize my files",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=360,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    tools = captured["tools"]
    assert tools is not None
    tool_names = [t["name"] for t in tools]
    assert "agent_use_skill" in tool_names  # provider name for agent.useSkill
    system_prompt = captured["system_prompt"]
    assert "Available skills" in system_prompt
    assert "organizeByType" in system_prompt


@pytest.mark.asyncio
async def test_plan_runner_use_skill_narrows_tools_and_blocks_out_of_whitelist(
    monkeypatch: pytest.MonkeyPatch,
):
    """LLM calls agent.useSkill('organizeByType') then drive.deleteFile; the
    latter must be blocked because it is not in the skill's whitelist."""
    fake_candidate = SimpleNamespace(
        skill_key="organizeByType",
        name="Organize by Type",
        description="Organize files by type",
        triggers_text="organize",
        tool_whitelist_json=["drive.listFolder", "drive.createFolder", "drive.moveFile"],
        plan_template_json={},
        search_text="organize",
    )
    monkeypatch.setattr(
        plan_module, "_candidate_skills", AsyncMock(return_value=[fake_candidate])
    )
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    # bind_skill_in_planner (in skill_tool.py) constructs AgentSkillRepository(db)
    # internally and calls get_by_key — patch it there to return a skill with the
    # same whitelist as the candidate.
    fake_skill = SimpleNamespace(
        skill_key="organizeByType",
        name="Organize by Type",
        description="Organize files by type",
        triggers_text="organize",
        tool_whitelist_json=["drive.listFolder", "drive.createFolder", "drive.moveFile"],
        plan_template_json={},
    )
    fake_repo = SimpleNamespace(get_by_key=AsyncMock(return_value=fake_skill))
    import fileflash.agents.harness.skill_tool as skill_tool_module
    monkeypatch.setattr(skill_tool_module, "AgentSkillRepository", lambda _db: fake_repo)

    captured: dict[str, Any] = {}

    async def fake_create_plan(**kwargs):  # noqa: ANN003
        tool_executor = kwargs["tool_executor"]
        # 1. LLM binds the skill via agent.useSkill.
        bind_result = await tool_executor("agent.useSkill", {"skillKey": "organizeByType"})
        assert bind_result["bound"] is True
        assert "drive.moveFile" in bind_result["allowedTools"]
        # 2. LLM attempts a non-whitelisted tool — must be blocked.
        delete_result = await tool_executor("drive.deleteFile", {"fileId": "1"})
        captured["delete_result"] = delete_result
        return {
            "summary": "organize by type",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "1", "targetFolderId": "2"},
                },
            ],
        }

    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=fake_create_plan),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
            "chatSessionId": "1",
            "input": "organize my files by type",
            "context": {
                "rootFolderId": "root",
                "selectedFileIds": [],
                "selectedFolderIds": [],
                "currentPath": "/My Files",
            },
            "executionPolicy": "confirm",
        }
    )
    job = BackgroundJob(
        job_id=361,
        task_type="agent.plan",
        status="running",
        payload=request.model_dump(by_alias=True),
        result={},
        requested_by=7,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = await runner.run(db=DummyDb(), job=job)  # type: ignore[arg-type]

    delete_result = captured["delete_result"]
    assert delete_result["_plannerBlocked"] is True
    assert delete_result["_toolError"] is True
    assert delete_result["tool"] == "drive.deleteFile"
    assert "not permitted" in delete_result["message"].lower() or "skill" in delete_result["message"].lower()
    assert result.chosen_skill is not None
    assert result.chosen_skill.id == "organizeByType"


def test_normalize_actions_rejects_symbolic_placeholder_target_folder():
    with pytest.raises(ApiError) as exc:
        plan_module._normalize_actions(
            llm_payload={
                "summary": "organize movies",
                "proposedActions": [
                    {
                        "step": 1,
                        "tool": "drive.createFolder",
                        "input": {"parentFolderId": "root", "name": "Movies"},
                    },
                    {
                        "step": 2,
                        "tool": "drive.moveFile",
                        "input": {"fileId": "13", "targetFolderId": "newFolderId"},
                    },
                ],
            },
            allowed_tools=("drive.createFolder", "drive.moveFile"),
            max_steps=10,
        )

    assert exc.value.status_code == 400
    assert "step 2" in exc.value.message
    assert "targetFolderId" in exc.value.message
    assert "newFolderId" in exc.value.message


def test_normalize_actions_allows_unbounded_steps_when_max_steps_none():
    actions = plan_module._normalize_actions(
        llm_payload={
            "summary": "organize movies",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "Movies"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "13", "targetFolderId": "$step1.folderId"},
                },
            ],
        },
        allowed_tools=("drive.createFolder", "drive.moveFile"),
        max_steps=None,
    )

    assert len(actions) == 2


def test_normalize_actions_accepts_previous_step_reference():
    actions = plan_module._normalize_actions(
        llm_payload={
            "summary": "organize movies",
            "proposedActions": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "Movies"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "13", "targetFolderId": "$step1.folderId"},
                },
            ],
        },
        allowed_tools=("drive.createFolder", "drive.moveFile"),
        max_steps=10,
    )

    assert len(actions) == 2
    assert actions[1].input["targetFolderId"] == "$step1.folderId"


def test_normalize_actions_rejects_future_step_reference():
    with pytest.raises(ApiError) as exc:
        plan_module._normalize_actions(
            llm_payload={
                "summary": "organize movies",
                "proposedActions": [
                    {
                        "step": 3,
                        "tool": "drive.moveFile",
                        "input": {"fileId": "13", "targetFolderId": "$step4.folderId"},
                    },
                    {
                        "step": 4,
                        "tool": "drive.createFolder",
                        "input": {"parentFolderId": "root", "name": "Movies"},
                    },
                ],
            },
            allowed_tools=("drive.createFolder", "drive.moveFile"),
            max_steps=10,
        )

    assert exc.value.status_code == 400
    assert "future step 4" in exc.value.message
    assert "$step4.folderId" in exc.value.message


def test_execute_reference_resolution_rejects_symbolic_placeholder():
    with pytest.raises(ApiError) as exc:
        execute_module._resolve_references(
            {"targetFolderId": "newFolderId"},
            step_outputs={},
        )

    assert exc.value.status_code == 409
    assert "targetFolderId" in exc.value.message
    assert "$stepN.field" in exc.value.message


@pytest.mark.asyncio
async def test_tool_router_dispatches_move_file():
    router = ToolRouter(db=DummyDb(), user_id=7)  # type: ignore[arg-type]
    router.file_service.move_file = AsyncMock(
        return_value=SimpleNamespace(
            model_dump=lambda **kwargs: {"fileId": "1", "targetFolderId": "2"}
        )
    )

    result = await router.dispatch(
        ToolCall(
            tool_name="drive.moveFile",
            arguments={"fileId": "1", "targetFolderId": "2"},
        )
    )

    assert result == {"fileId": "1", "targetFolderId": "2"}
    router.file_service.move_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_tool_router_count_files_counts_recursive_videos():
    db = DummyDb()
    db.scalar = AsyncMock(return_value=1)
    db.scalars = AsyncMock(
        side_effect=[
            [1, 2],
            [
                SimpleNamespace(
                    file_id=10,
                    file_name="movie.mp4",
                    file_size=100,
                    mime_type="application/octet-stream",
                    file_ext="mp4",
                    folder_id=1,
                    created_at=None,
                    updated_at=None,
                ),
                SimpleNamespace(
                    file_id=11,
                    file_name="clip.mkv",
                    file_size=200,
                    mime_type="video/x-matroska",
                    file_ext="mkv",
                    folder_id=2,
                    created_at=None,
                    updated_at=None,
                ),
                SimpleNamespace(
                    file_id=12,
                    file_name="notes.txt",
                    file_size=10,
                    mime_type="text/plain",
                    file_ext="txt",
                    folder_id=1,
                    created_at=None,
                    updated_at=None,
                ),
            ],
        ]
    )
    router = ToolRouter(db=db, user_id=7)  # type: ignore[arg-type]

    result = await router.dispatch(
        ToolCall(
            tool_name="drive.countFiles",
            arguments={"folderId": "root", "recursive": True, "category": "video"},
        )
    )

    assert result["totalItems"] == 2
    assert result["category"] == "video"
    assert result["recursive"] is True
    assert result["byMimeType"] == {"video/mp4": 1, "video/x-matroska": 1}
    assert [item["name"] for item in result["sampleItems"]] == ["movie.mp4", "clip.mkv"]
    executed_statement = str(db.scalars.await_args_list[-1].args[0])
    assert "file.status" in executed_statement
    assert "file.is_latest" in executed_statement


@pytest.mark.asyncio
async def test_tool_router_count_files_filters_by_search_term():
    db = DummyDb()
    db.scalar = AsyncMock(return_value=1)
    db.scalars = AsyncMock(
        side_effect=[
            [1],
            [
                SimpleNamespace(
                    file_id=10,
                    file_name="银翼杀手.mp4",
                    file_size=100,
                    mime_type="video/mp4",
                    file_ext="mp4",
                    folder_id=1,
                    created_at=None,
                    updated_at=None,
                ),
            ],
        ]
    )
    router = ToolRouter(db=db, user_id=7)  # type: ignore[arg-type]

    result = await router.dispatch(
        ToolCall(
            tool_name="drive.countFiles",
            arguments={
                "folderId": "root",
                "recursive": True,
                "category": "video",
                "search": "银翼杀手",
            },
        )
    )

    assert result["totalItems"] == 1
    assert result["search"] == "银翼杀手"
    executed_statement = str(db.scalars.await_args_list[-1].args[0])
    assert "file_name" in executed_statement


@pytest.mark.asyncio
async def test_execute_runner_normalizes_tool_output_before_action_log(monkeypatch: pytest.MonkeyPatch):
    started = datetime.now(UTC)
    output_time = datetime.now(UTC)
    job = BackgroundJob(
        job_id=600,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "500",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.createFolder",
        "input": {"parentFolderId": "root", "name": "Movies"},
        "sideEffect": "write",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()

    mock_plan_repo = SimpleNamespace(
        get_for_execute_binding=AsyncMock(
            return_value=SimpleNamespace(
                proposed_actions_json=[action],
            )
        )
    )
    monkeypatch.setattr(execute_module, "AgentPlanRepository", lambda _db: mock_plan_repo)

    mock_work_sessions = SimpleNamespace(
        create_for_job=AsyncMock(return_value=None),
        close_session=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(execute_module, "AgentWorkSessionRepository", lambda _db: mock_work_sessions)

    captured_outputs: list[dict[str, object]] = []
    mock_action_logs = SimpleNamespace(
        append_step=AsyncMock(return_value=None),
        finish_step=AsyncMock(
            side_effect=lambda **kwargs: captured_outputs.append(dict(kwargs)) or None
        ),
    )
    monkeypatch.setattr(execute_module, "AgentActionLogRepository", lambda _db: mock_action_logs)

    mock_router = SimpleNamespace(
        dispatch=AsyncMock(
            return_value={
                "id": "9",
                "createdAt": output_time,
                "updatedAt": output_time,
            }
        )
    )
    monkeypatch.setattr(execute_module, "ToolRouter", lambda **kwargs: mock_router)

    result = await ExecuteRunner(
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok"))  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert captured_outputs
    success_call = next(item for item in captured_outputs if item.get("status") == "succeeded")
    outputs_json = success_call["outputs_json"]
    assert isinstance(outputs_json, dict)
    assert isinstance(outputs_json["createdAt"], str)
    assert outputs_json["createdAt"] == output_time.isoformat()


@pytest.mark.asyncio
async def test_execute_runner_propagates_answer_model_errors(monkeypatch: pytest.MonkeyPatch):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=610,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "510",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.countFiles",
        "input": {"folderId": "root", "recursive": True, "category": "video"},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()
    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(return_value=SimpleNamespace(proposed_actions_json=[action]))
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "totalItems": 3,
                    "category": "video",
                    "recursive": True,
                    "folderId": "1",
                    "byMimeType": {"video/mp4": 3},
                }
            )
        ),
    )

    with pytest.raises(ApiError) as exc:
        await ExecuteRunner(
            answer_client=SimpleNamespace(
                create_answer=AsyncMock(
                    side_effect=ApiError(status_code=503, code=503, message="Agent LLM API key is not configured")
                )
            )  # type: ignore[arg-type]
        ).run(db=db, job=job)  # type: ignore[arg-type]

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_execute_runner_returns_count_files_answer(monkeypatch: pytest.MonkeyPatch):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=601,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "501",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.countFiles",
        "input": {"folderId": "root", "recursive": True, "category": "video"},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()

    mock_plan_repo = SimpleNamespace(
        get_for_execute_binding=AsyncMock(
            return_value=SimpleNamespace(
                proposed_actions_json=[action],
            )
        )
    )
    monkeypatch.setattr(execute_module, "AgentPlanRepository", lambda _db: mock_plan_repo)

    mock_work_sessions = SimpleNamespace(
        create_for_job=AsyncMock(return_value=None),
        close_session=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(execute_module, "AgentWorkSessionRepository", lambda _db: mock_work_sessions)
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "totalItems": 3,
                    "category": "video",
                    "recursive": True,
                    "folderId": "1",
                    "byMimeType": {"video/mp4": 3},
                    "sampleItems": [],
                }
            )
        ),
    )

    result = await ExecuteRunner(
        answer_client=SimpleNamespace(
            create_answer=AsyncMock(return_value="你上传了 3 部电影（按视频文件统计）。")
        )  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    assert result.answer == "你上传了 3 部电影（按视频文件统计）。"
    assert result.applied_actions == 1


@pytest.mark.asyncio
async def test_execute_runner_returns_count_files_answer_with_search_term(
    monkeypatch: pytest.MonkeyPatch,
):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=602,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "502",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.countFiles",
        "input": {
            "folderId": "root",
            "recursive": True,
            "category": "video",
            "search": "银翼杀手",
        },
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(
                return_value=SimpleNamespace(proposed_actions_json=[action])
            )
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "totalItems": 2,
                    "category": "video",
                    "recursive": True,
                    "folderId": "1",
                    "search": "银翼杀手",
                    "byMimeType": {"video/mp4": 2},
                    "sampleItems": [],
                }
            )
        ),
    )

    result = await ExecuteRunner(
        answer_client=SimpleNamespace(
            create_answer=AsyncMock(return_value="你上传了 2 部名称包含“银翼杀手”的电影（按视频文件统计）。")
        )  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    assert result.answer == "你上传了 2 部名称包含“银翼杀手”的电影（按视频文件统计）。"
    assert "只读操作" not in (result.answer or "")


@pytest.mark.asyncio
async def test_execute_runner_returns_count_files_answer_with_names_when_asked(
    monkeypatch: pytest.MonkeyPatch,
):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=604,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "504",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.countFiles",
        "input": {"folderId": "root", "recursive": True, "category": "archive"},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(
                return_value=SimpleNamespace(
                    input_text="我上传了多少压缩包，叫什么名字",
                    proposed_actions_json=[action],
                )
            )
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "totalItems": 2,
                    "category": "archive",
                    "recursive": True,
                    "folderId": "1",
                    "itemNames": ["photos.zip", "backup.7z"],
                    "itemNamesTruncated": False,
                    "byMimeType": {"application/zip": 1, "application/x-7z-compressed": 1},
                    "sampleItems": [],
                }
            )
        ),
    )

    result = await ExecuteRunner(
        answer_client=SimpleNamespace(
            create_answer=AsyncMock(return_value="你上传了 2 个压缩包，名字是：photos.zip、backup.7z。")
        )  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    assert result.answer == "你上传了 2 个压缩包，名字是：photos.zip、backup.7z。"


@pytest.mark.asyncio
async def test_execute_runner_lists_archive_names_for_read_only_archive_question(
    monkeypatch: pytest.MonkeyPatch,
):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=603,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "503",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.listFolder",
        "input": {"folderId": "root"},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(
                return_value=SimpleNamespace(
                    input_text="我上传了哪些压缩包",
                    proposed_actions_json=[action],
                )
            )
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "items": [
                        {
                            "itemType": "file",
                            "id": "1",
                            "name": "photos.zip",
                            "size": 10,
                            "mimeType": "application/zip",
                        },
                        {
                            "itemType": "file",
                            "id": "2",
                            "name": "movie.mp4",
                            "size": 20,
                            "mimeType": "video/mp4",
                        },
                        {
                            "itemType": "file",
                            "id": "3",
                            "name": "backup.7z",
                            "size": 30,
                            "mimeType": "application/octet-stream",
                        },
                    ],
                    "pagination": {
                        "totalItems": 3,
                        "totalPages": 1,
                        "perPage": 200,
                        "currentPage": 1,
                        "hasPrev": False,
                        "hasNext": False,
                    },
                }
            )
        ),
    )

    result = await ExecuteRunner(
        answer_client=SimpleNamespace(
            create_answer=AsyncMock(return_value="当前文件夹中的压缩包有 2 个：photos.zip、backup.7z。")
        )  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    assert result.answer == "当前文件夹中的压缩包有 2 个：photos.zip、backup.7z。"


@pytest.mark.asyncio
async def test_execute_runner_returns_search_files_candidate_answer(
    monkeypatch: pytest.MonkeyPatch,
):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=605,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "505",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.searchFiles",
        "input": {"folderId": "root", "query": "银翼杀手", "category": "video"},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    db = DummyDb()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(
                return_value=SimpleNamespace(
                    input_text="把银翼杀手电影放到银翼杀手文件夹下",
                    proposed_actions_json=[action],
                )
            )
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "items": [
                        {"id": "11", "name": "银翼杀手1982.mp4", "mimeType": "video/mp4"},
                        {"id": "12", "name": "银翼杀手2049.mp4", "mimeType": "video/mp4"},
                    ],
                    "totalItems": 2,
                    "query": "银翼杀手",
                    "folderId": "1",
                    "recursive": False,
                    "category": "video",
                }
            )
        ),
    )

    result = await ExecuteRunner(
        answer_client=SimpleNamespace(
            create_answer=AsyncMock(
                return_value="找到 2 个名称包含“银翼杀手”的文件：银翼杀手1982.mp4、银翼杀手2049.mp4。"
            )
        )  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    assert result.answer == "找到 2 个名称包含“银翼杀手”的文件：银翼杀手1982.mp4、银翼杀手2049.mp4。"


class _NeverStream:
    async def next(self, *, timeout=None):  # noqa: ANN001
        await asyncio.Future()

    async def aclose(self) -> None:
        return None


class _CaptureBus:
    def __init__(self) -> None:
        self.events: list[AgentEventEnvelope] = []

    async def publish(self, envelope: AgentEventEnvelope) -> None:
        self.events.append(envelope)

    @asynccontextmanager
    async def subscribe(self, *, job_id: int):  # noqa: ARG002
        yield _NeverStream()


def _execute_job_for_controls() -> BackgroundJob:
    started = datetime.now(UTC)
    return BackgroundJob(
        job_id=700,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "500",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )


def _patch_execute_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    controls: list[list[SimpleNamespace]],
    dropped: list[int],
) -> None:
    action = {
        "step": 1,
        "tool": "drive.countFiles",
        "input": {"folderId": "root", "recursive": True, "category": "video"},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }

    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(
                return_value=SimpleNamespace(proposed_actions_json=[action])
            )
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "totalItems": 1,
                    "category": "video",
                    "recursive": True,
                    "folderId": "1",
                    "byMimeType": {"video/mp4": 1},
                    "sampleItems": [],
                }
            )
        ),
    )

    class FakeInboxRepository:
        def __init__(self, _db) -> None:  # noqa: ANN001
            return None

        async def list_pending_controls(self, *, job_id: int):  # noqa: ARG002
            if controls:
                return controls.pop(0)
            return []

        async def mark_dropped(self, *, inbox_message_id: int) -> None:
            dropped.append(inbox_message_id)

    monkeypatch.setattr(execute_module, "AgentInboxMessageRepository", FakeInboxRepository)


@pytest.mark.asyncio
async def test_execute_runner_pauses_then_resumes_at_step_boundary(
    monkeypatch: pytest.MonkeyPatch,
):
    controls = [
        [SimpleNamespace(inbox_message_id=1, kind=AgentInboxKind.CONTROL_PAUSE)],
        [SimpleNamespace(inbox_message_id=2, kind=AgentInboxKind.CONTROL_RESUME)],
    ]
    dropped: list[int] = []
    _patch_execute_dependencies(monkeypatch, controls=controls, dropped=dropped)
    db = DummyDb()
    db.refresh = AsyncMock()
    bus = _CaptureBus()

    result = await ExecuteRunner(
        event_bus=bus,
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
    ).run(db=db, job=_execute_job_for_controls())  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert dropped == [1, 2]
    event_types = [event.event_type for event in bus.events]
    assert "agent.paused" in event_types
    assert "agent.resumed" in event_types
    assert "tool.started" in event_types
    assert "tool.succeeded" in event_types


@pytest.mark.asyncio
async def test_execute_runner_canceled_via_inbox_at_step_boundary(
    monkeypatch: pytest.MonkeyPatch,
):
    controls = [[SimpleNamespace(inbox_message_id=1, kind=AgentInboxKind.CONTROL_CANCEL)]]
    dropped: list[int] = []
    _patch_execute_dependencies(monkeypatch, controls=controls, dropped=dropped)
    db = DummyDb()
    db.refresh = AsyncMock()

    with pytest.raises(AgentJobCanceled):
        await ExecuteRunner(
            event_bus=_CaptureBus(),
            answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
        ).run(  # type: ignore[arg-type]
            db=db,
            job=_execute_job_for_controls(),
        )

    assert dropped == [1]


def _control_message(
    *,
    inbox_message_id: int,
    kind: AgentInboxKind,
    step: int,
    reason: str | None = None,
) -> SimpleNamespace:
    metadata: dict[str, Any] = {"step": step}
    if reason is not None:
        metadata["reason"] = reason
    return SimpleNamespace(
        inbox_message_id=inbox_message_id,
        kind=kind,
        payload_json={"metadata": metadata},
    )


def _patch_execute_dependencies_with_actions(
    monkeypatch: pytest.MonkeyPatch,
    *,
    actions: list[dict[str, Any]],
    controls: list[list[SimpleNamespace]],
    dropped: list[int],
) -> None:
    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(
                return_value=SimpleNamespace(proposed_actions_json=actions)
            )
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(return_value=None),
            finish_step=AsyncMock(return_value=None),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(
            dispatch=AsyncMock(
                return_value={
                    "totalItems": 1,
                    "category": "video",
                    "recursive": True,
                    "folderId": "1",
                    "byMimeType": {"video/mp4": 1},
                    "sampleItems": [],
                }
            )
        ),
    )

    class FakeInboxRepository:
        def __init__(self, _db) -> None:  # noqa: ANN001
            return None

        async def list_pending_controls(self, *, job_id: int):  # noqa: ARG002
            if controls:
                return controls.pop(0)
            return []

        async def mark_dropped(self, *, inbox_message_id: int) -> None:
            dropped.append(inbox_message_id)

    monkeypatch.setattr(execute_module, "AgentInboxMessageRepository", FakeInboxRepository)


@pytest.mark.asyncio
async def test_execute_control_deny_skips_matching_step(monkeypatch: pytest.MonkeyPatch):
    actions = [
        {
            "step": 1,
            "tool": "drive.countFiles",
            "input": {"folderId": "root", "recursive": True, "category": "video"},
            "sideEffect": "read",
            "riskLevel": "low",
            "requiresConfirmation": False,
        },
        {
            "step": 2,
            "tool": "drive.countFiles",
            "input": {"folderId": "root", "recursive": True, "category": "image"},
            "sideEffect": "read",
            "riskLevel": "low",
            "requiresConfirmation": False,
        },
    ]
    deny_ctrl = _control_message(
        inbox_message_id=10,
        kind=AgentInboxKind.CONTROL_DENY,
        step=1,
        reason="user changed mind",
    )
    controls = [[deny_ctrl], []]
    dropped: list[int] = []
    _patch_execute_dependencies_with_actions(
        monkeypatch, actions=actions, controls=controls, dropped=dropped
    )
    db = DummyDb()
    db.refresh = AsyncMock()

    result = await ExecuteRunner(
        event_bus=_CaptureBus(),
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
    ).run(db=db, job=_execute_job_for_controls())  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert result.skipped_actions == 1
    assert dropped == [10]
    assert any("denied by user" in w and "Step 1" in w for w in result.warnings)
    assert any("user changed mind" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_execute_control_deny_does_not_affect_wrong_step(monkeypatch: pytest.MonkeyPatch):
    deny_ctrl = _control_message(
        inbox_message_id=11,
        kind=AgentInboxKind.CONTROL_DENY,
        step=2,
        reason="not this step",
    )
    controls = [[deny_ctrl]]
    dropped: list[int] = []
    _patch_execute_dependencies(monkeypatch, controls=controls, dropped=dropped)
    db = DummyDb()
    db.refresh = AsyncMock()

    result = await ExecuteRunner(
        event_bus=_CaptureBus(),
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
    ).run(db=db, job=_execute_job_for_controls())  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert result.skipped_actions == 0
    assert dropped == []
    assert not any("denied by user" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_execute_control_approve_proceeds(monkeypatch: pytest.MonkeyPatch):
    approve_ctrl = _control_message(
        inbox_message_id=12,
        kind=AgentInboxKind.CONTROL_APPROVE,
        step=1,
    )
    controls = [[approve_ctrl]]
    dropped: list[int] = []
    _patch_execute_dependencies(monkeypatch, controls=controls, dropped=dropped)
    db = DummyDb()
    db.refresh = AsyncMock()

    result = await ExecuteRunner(
        event_bus=_CaptureBus(),
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
    ).run(db=db, job=_execute_job_for_controls())  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert result.skipped_actions == 0
    assert dropped == [12]
    assert not any("skipped by user" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_execute_control_skip_step_matching(monkeypatch: pytest.MonkeyPatch):
    actions = [
        {
            "step": 1,
            "tool": "drive.countFiles",
            "input": {"folderId": "root", "recursive": True, "category": "video"},
            "sideEffect": "read",
            "riskLevel": "low",
            "requiresConfirmation": False,
        },
        {
            "step": 2,
            "tool": "drive.countFiles",
            "input": {"folderId": "root", "recursive": True, "category": "image"},
            "sideEffect": "read",
            "riskLevel": "low",
            "requiresConfirmation": False,
        },
    ]
    skip_ctrl = _control_message(
        inbox_message_id=20,
        kind=AgentInboxKind.CONTROL_SKIP,
        step=2,
    )
    # The control persists across both step boundaries (not dropped at step 1
    # because the step-matching guard skips it), then fires at step 2.
    controls = [[skip_ctrl], [skip_ctrl]]
    dropped: list[int] = []
    _patch_execute_dependencies_with_actions(
        monkeypatch, actions=actions, controls=controls, dropped=dropped
    )
    db = DummyDb()
    db.refresh = AsyncMock()

    result = await ExecuteRunner(
        event_bus=_CaptureBus(),
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
    ).run(db=db, job=_execute_job_for_controls())  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert result.skipped_actions == 1
    assert dropped == [20]
    assert any("Step 2 skipped by user" in w for w in result.warnings)
    assert not any("Step 1 skipped by user" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_execute_runner_publish_state_ignores_event_bus_failures():
    bus = SimpleNamespace(publish=AsyncMock(side_effect=RuntimeError("boom")))
    runner = ExecuteRunner(event_bus=bus)  # type: ignore[arg-type]

    await runner._publish_state("agent.paused", job_id=1)

    assert bus.publish.await_count == 1


@pytest.mark.asyncio
async def test_execute_runner_publish_tool_ignores_event_bus_failures():
    bus = SimpleNamespace(publish=AsyncMock(side_effect=RuntimeError("boom")))
    runner = ExecuteRunner(event_bus=bus)  # type: ignore[arg-type]

    await runner._publish_tool(
        "tool.started",
        job_id=1,
        step=1,
        tool="drive.listFolder",
        payload={"input": {"folderId": "root"}},
    )

    assert bus.publish.await_count == 1


@pytest.mark.asyncio
async def test_execute_denies_readfile_when_data_policy_disables_content(
    monkeypatch: pytest.MonkeyPatch,
):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=630,
        task_type="agent.execute",
        status="running",
        payload={
            "chatSessionId": "1",
            "planJobId": "520",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": started.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=started,
        created_at=started,
        updated_at=started,
    )
    action = {
        "step": 1,
        "tool": "drive.readFile",
        "input": {"fileId": "1", "maxBytes": 1024},
        "sideEffect": "read",
        "riskLevel": "low",
        "requiresConfirmation": False,
    }
    plan = SimpleNamespace(
        proposed_actions_json=[action],
        execution_policy="confirm",
        data_policy_json={"allowFileContent": False, "maxReadBytes": 1024, "allowedMimeTypes": ["*/*"]},
        chosen_skill_id=None,
        input_text="read the file",
        context_json={},
    )
    db = DummyDb()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        execute_module,
        "AgentPlanRepository",
        lambda _db: SimpleNamespace(
            get_for_execute_binding=AsyncMock(return_value=plan)
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentWorkSessionRepository",
        lambda _db: SimpleNamespace(
            create_for_job=AsyncMock(return_value=None),
            close_session=AsyncMock(return_value=None),
        ),
    )
    captured_steps: list[dict[str, object]] = []

    def _capture_append(**kwargs):  # noqa: ANN003
        captured_steps.append({"phase": "append", **kwargs})
        return None

    def _capture_finish(**kwargs):  # noqa: ANN003
        captured_steps.append({"phase": "finish", **kwargs})
        return None

    monkeypatch.setattr(
        execute_module,
        "AgentActionLogRepository",
        lambda _db: SimpleNamespace(
            append_step=AsyncMock(side_effect=_capture_append),
            finish_step=AsyncMock(side_effect=_capture_finish),
        ),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentSettingsRepository",
        lambda _db: SimpleNamespace(get_by_user_id=AsyncMock(return_value=None)),
    )
    monkeypatch.setattr(
        execute_module,
        "AgentSkillRepository",
        lambda _db: SimpleNamespace(get_by_key=AsyncMock(return_value=None)),
    )
    monkeypatch.setattr(
        execute_module,
        "ToolRouter",
        lambda **kwargs: SimpleNamespace(dispatch=AsyncMock(return_value={"content": "secret"})),
    )
    bus = _CaptureBus()

    result = await ExecuteRunner(
        event_bus=bus,
        answer_client=SimpleNamespace(create_answer=AsyncMock(return_value="ok")),  # type: ignore[arg-type]
    ).run(db=db, job=job)  # type: ignore[arg-type]

    # Job did NOT fail: it completed with 0 applied and 1 skipped (denied) action.
    assert result.applied_actions == 0
    assert result.skipped_actions == 1
    assert any("denied by policy" in w for w in result.warnings)

    # ActionLog: append_step + finish_step both called with status="denied".
    finish_calls = [c for c in captured_steps if c["phase"] == "finish"]
    assert len(finish_calls) == 1
    assert finish_calls[0]["status"] == "denied"
    assert finish_calls[0]["step_no"] == 1
    append_calls = [c for c in captured_steps if c["phase"] == "append"]
    assert len(append_calls) == 1
    assert append_calls[0]["status"] == "denied"

    # tool.failed event published with denied: True.
    failed_events = [e for e in bus.events if e.event_type == "tool.failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["denied"] is True
    assert failed_events[0].payload["tool"] == "drive.readFile"
    assert "File content access disabled by dataPolicy." in failed_events[0].payload["reasons"]

    # The tool dispatch was never called (denied before dispatch).
    # ToolRouter is constructed once; verify dispatch not awaited by checking no
    # tool.succeeded event exists.
    succeeded_events = [e for e in bus.events if e.event_type == "tool.succeeded"]
    assert succeeded_events == []
