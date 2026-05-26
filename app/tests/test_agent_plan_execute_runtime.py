from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.agents.harness.policy import PolicyGuard, classify_tool_risk
from fileflash.agents.harness.router import ToolCall, ToolRouter
from fileflash.agents.runtime import execute_runner as execute_module
from fileflash.agents.runtime.execute_runner import ExecuteRunner
from fileflash.agents.runtime import plan_runner as plan_module
from fileflash.agents.runtime.llm import AnthropicPlannerClient
from fileflash.agents.runtime.plan_runner import PlanRunner
from fileflash.core.errors import ApiError
from fileflash.models import BackgroundJob
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
        self.scalar = AsyncMock()
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


def settings(**overrides):
    base = {
        "agent_enabled": True,
        "agent_job_max_tokens": 50_000,
        "agent_job_max_tool_calls": 100,
        "agent_user_concurrent_limit": 2,
        "agent_user_daily_limit": 50,
        "agent_llm_base_url": None,
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
    )
    payload = PlanAgentRequest.model_validate(
        {
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
    assert fake_messages.kwargs["max_tokens"] == 4096
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
    )
    payload = ExecuteAgentRequest.model_validate(
        {
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
    )
    payload = ExecuteAgentRequest.model_validate(
        {
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
    )
    payload = ExecuteAgentRequest.model_validate(
        {
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
    monkeypatch.setattr(plan_module, "_choose_skill", AsyncMock(return_value=None))
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
async def test_plan_runner_commits_after_upsert(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plan_module, "_choose_skill", AsyncMock(return_value=None))
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
    monkeypatch.setattr(plan_module, "_choose_skill", AsyncMock(return_value=None))
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
async def test_plan_runner_uses_safe_read_only_fallback_when_planner_returns_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_choose_skill", AsyncMock(return_value=None))
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

    result = await runner.run(db=db, job=job)  # type: ignore[arg-type]

    assert "fallback mode" in result.summary.lower()
    assert len(result.proposed_actions) == 1
    assert result.proposed_actions[0].tool == "drive.listFolder"
    assert result.proposed_actions[0].side_effect == "read"
    assert result.requires_confirmation is False


@pytest.mark.asyncio
async def test_plan_runner_fallback_uses_count_files_for_movie_count_question(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_choose_skill", AsyncMock(return_value=None))
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
async def test_plan_runner_uses_deterministic_count_plan_with_search_term(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(plan_module, "_choose_skill", AsyncMock(return_value=None))
    monkeypatch.setattr(
        plan_module,
        "_collect_context_metadata",
        AsyncMock(return_value={"scope": "currentFolder", "rootFolderId": "root", "files": [], "folders": []}),
    )
    monkeypatch.setattr(plan_module, "_upsert_agent_plan", AsyncMock(return_value=None))

    planner = AsyncMock(return_value={"summary": "wrong", "proposedActions": []})
    runner = PlanRunner(
        settings=settings(),
        planner_client=SimpleNamespace(create_plan=planner),  # type: ignore[arg-type]
    )
    request = PlanAgentRequest.model_validate(
        {
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

    planner.assert_not_awaited()
    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert action.tool == "drive.countFiles"
    assert action.input["category"] == "video"
    assert action.input["search"] == "银翼杀手"
    assert action.side_effect == "read"


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
async def test_policy_guard_blocks_delete_without_confirmation():
    decision = await PolicyGuard().evaluate_tool_call(
        tool_name="drive.deleteFile",
        high_risk_confirmed=False,
    )
    assert decision.allowed is False
    assert classify_tool_risk("drive.deleteFolder") == "high"


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
    db.scalars = AsyncMock(return_value=[1, 2])
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            all=lambda: [
                (10, "movie.mp4", 100, "application/octet-stream", "mp4", 1),
                (11, "clip.mkv", 200, "video/x-matroska", "mkv", 2),
                (12, "notes.txt", 10, "text/plain", "txt", 1),
            ]
        )
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
    executed_statement = str(db.execute.await_args.args[0])
    assert "file.status" in executed_statement
    assert "file.is_latest" in executed_statement


@pytest.mark.asyncio
async def test_tool_router_count_files_filters_by_search_term():
    db = DummyDb()
    db.scalar = AsyncMock(return_value=1)
    db.scalars = AsyncMock(return_value=[1])
    db.execute = AsyncMock(
        return_value=SimpleNamespace(
            all=lambda: [
                (10, "银翼杀手.mp4", 100, "video/mp4", "mp4", 1),
            ]
        )
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
    executed_statement = str(db.execute.await_args.args[0])
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

    result = await ExecuteRunner().run(db=db, job=job)  # type: ignore[arg-type]

    assert result.applied_actions == 1
    assert captured_outputs
    success_call = next(item for item in captured_outputs if item.get("status") == "succeeded")
    outputs_json = success_call["outputs_json"]
    assert isinstance(outputs_json, dict)
    assert isinstance(outputs_json["createdAt"], str)
    assert outputs_json["createdAt"] == output_time.isoformat()


@pytest.mark.asyncio
async def test_execute_runner_returns_count_files_answer(monkeypatch: pytest.MonkeyPatch):
    started = datetime.now(UTC)
    job = BackgroundJob(
        job_id=601,
        task_type="agent.execute",
        status="running",
        payload={
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

    result = await ExecuteRunner().run(db=db, job=job)  # type: ignore[arg-type]

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

    result = await ExecuteRunner().run(db=db, job=job)  # type: ignore[arg-type]

    assert result.answer == "你上传了 2 部名称包含“银翼杀手”的电影（按视频文件统计）。"
    assert "只读操作" not in (result.answer or "")
