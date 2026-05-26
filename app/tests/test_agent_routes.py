from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.agents.harness.event_bus import AgentEventEnvelope, InMemoryAgentEventBus
from fileflash.core.deps import (
    get_agent_event_bus,
    get_agent_execute_service,
    get_agent_plan_service,
    get_current_user,
)
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.db.deps import get_db
from fileflash.models import AgentActionLog, AgentInboxMessage, BackgroundJob
from fileflash.models.enums import AgentInboxRole
from fileflash.models.tables_identity import User
from fileflash.routers.agent import router
from fileflash.schemas.agent import ExecuteAgentResponse, PlanAgentResponse


class StubPlanService:
    async def enqueue_plan(self, *, user_id, payload):  # noqa: ANN001
        return PlanAgentResponse(job_id="10", status="pending", task_type="agent.plan")


class StubExecuteService:
    async def enqueue_execute(self, *, user_id, payload):  # noqa: ANN001
        return ExecuteAgentResponse(job_id="11", status="pending", task_type="agent.execute")


class StubDb:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.job = BackgroundJob(
            job_id=12,
            task_type="agent.execute",
            status="pending",
            payload={},
            result={},
            requested_by=7,
            scheduled_at=now,
            created_at=now,
            updated_at=now,
        )
        self.messages: list[AgentInboxMessage] = []
        self._next_inbox_id = 1

    async def scalar(self, _query):  # noqa: ANN001
        return self.job

    async def scalars(self, _query):  # noqa: ANN001
        return []

    def add(self, msg: AgentInboxMessage) -> None:
        msg.inbox_message_id = self._next_inbox_id
        self._next_inbox_id += 1
        self.messages.append(msg)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, _job: BackgroundJob) -> None:
        return None

    async def get(self, _model, _id: int):  # noqa: ANN001
        return None


class RunningJobDb(StubDb):
    def __init__(self) -> None:
        super().__init__()
        self.job.status = "running"


class EventsDb(StubDb):
    def __init__(self) -> None:
        super().__init__()
        now = datetime.now(UTC)
        self.job.status = "succeeded"
        self.job.result = {
            "planJobId": "10",
            "executeJobId": "12",
            "summary": "done",
            "answer": "你上传了 2 部名称包含“银翼杀手”的电影（按视频文件统计）。",
            "appliedActions": 1,
            "skippedActions": 0,
            "warnings": [],
            "finishedAt": now.isoformat(),
        }
        self.job.finished_at = now
        self.job.updated_at = now
        self.action_log = AgentActionLog(
            action_log_id=1,
            job_id=12,
            step_no=1,
            tool_name="drive.countFiles",
            inputs_json={"folderId": "root", "category": "video", "search": "银翼杀手"},
            outputs_json={"totalItems": 2, "category": "video", "search": "银翼杀手"},
            status="succeeded",
            duration_ms=12,
            started_at=now,
            finished_at=now,
        )

    async def scalars(self, _query):  # noqa: ANN001
        return [self.action_log]


def _user() -> User:
    return User(user_id=7, username="u7", email="u7@example.com", password_hash="x")


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_agent_plan_service] = lambda: StubPlanService()
    app.dependency_overrides[get_agent_execute_service] = lambda: StubExecuteService()
    app.dependency_overrides[get_db] = lambda: StubDb()
    return TestClient(app)


def _client_with_running_job() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_agent_plan_service] = lambda: StubPlanService()
    app.dependency_overrides[get_agent_execute_service] = lambda: StubExecuteService()
    app.dependency_overrides[get_db] = lambda: RunningJobDb()
    return TestClient(app)


def _client_with_events() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_agent_plan_service] = lambda: StubPlanService()
    app.dependency_overrides[get_agent_execute_service] = lambda: StubExecuteService()
    app.dependency_overrides[get_db] = lambda: EventsDb()
    return TestClient(app)


def test_plan_route_returns_response_shell():
    response = _client().post(
        "/api/v1/agent/plan",
        json={
            "input": "organize",
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
            "hints": {"preferSkillId": None, "maxSteps": 12, "budgetTokens": 8000},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["jobId"] == "10"
    assert body["data"]["taskType"] == "agent.plan"


def test_execute_route_returns_response_shell():
    response = _client().post(
        "/api/v1/agent/execute",
        json={
            "planJobId": "10",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": datetime.now(UTC).isoformat(),
                "highRiskConfirmed": True,
                "highRiskConfirmedAt": datetime.now(UTC).isoformat(),
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["jobId"] == "11"
    assert body["data"]["taskType"] == "agent.execute"


def test_post_message_control_pause_returns_response_shell():
    bus = InMemoryAgentEventBus()
    db = StubDb()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_agent_event_bus] = lambda: bus
    client = TestClient(app)

    response = client.post("/api/v1/agent/jobs/12/messages", json={"kind": "control.pause"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["kind"] == "control.pause"
    assert body["data"]["inboxMessageId"] == "1"
    assert db.messages[0].role == AgentInboxRole.USER


def test_job_events_route_streams_tool_and_final_answer_events():
    response = _client_with_events().get("/api/v1/agent/jobs/12/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: tool.started" in body
    assert "event: tool.succeeded" in body
    assert "event: job.succeeded" in body
    assert "正在读取名称包含" in body
    assert "银翼杀手" in body
    assert "answer" in body


def test_job_events_route_streams_event_bus_events_after_initial_replay():
    now = datetime.now(UTC)
    events = [
        AgentEventEnvelope(
            job_id=12,
            event_type="agent.progress",
            payload={"step": 1, "total": 3, "message": "halfway"},
            emitted_at=now,
        ),
        AgentEventEnvelope(
            job_id=12,
            event_type="job.succeeded",
            payload={"status": "succeeded"},
            emitted_at=now,
        ),
    ]

    class StaticStream:
        async def next(self, *, timeout=None):  # noqa: ANN001
            if not events:
                raise TimeoutError
            return events.pop(0)

        async def aclose(self) -> None:
            return None

    class StaticBus:
        async def publish(self, envelope):  # noqa: ANN001
            return None

        @asynccontextmanager
        async def subscribe(self, *, job_id: int):  # noqa: ARG002
            yield StaticStream()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: RunningJobDb()
    app.dependency_overrides[get_agent_event_bus] = lambda: StaticBus()
    client = TestClient(app)

    response = client.get("/api/v1/agent/jobs/12/events")

    assert response.status_code == 200
    assert "event: agent.progress" in response.text
    assert "event: job.succeeded" in response.text
