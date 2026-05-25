from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_agent_execute_service, get_agent_plan_service, get_current_user
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.db.deps import get_db
from fileflash.models import BackgroundJob
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

    async def scalar(self, _query):  # noqa: ANN001
        return self.job

    async def commit(self) -> None:
        return None

    async def refresh(self, _job: BackgroundJob) -> None:
        return None


class RunningJobDb(StubDb):
    def __init__(self) -> None:
        super().__init__()
        self.job.status = "running"


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


def test_cancel_route_returns_response_shell():
    response = _client().post("/api/v1/agent/cancel/12")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["jobId"] == "12"
    assert body["data"]["status"] == "canceled"
    assert body["data"]["canceledAt"]


def test_cancel_route_marks_running_job_as_canceled():
    response = _client_with_running_job().post("/api/v1/agent/cancel/12")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["jobId"] == "12"
    assert body["data"]["status"] == "canceled"
