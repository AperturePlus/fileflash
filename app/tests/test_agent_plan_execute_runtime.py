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
