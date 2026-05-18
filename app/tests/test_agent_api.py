from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_agent_execute_service, get_agent_plan_service, require_verified_user
from fileflash.routers.agent import router as agent_router
from fileflash.schemas.agent import ExecuteAgentRequest, PlanAgentRequest, PlanAgentResponse


class StubUser:
    user_id = 1
    email_verified = True


class StubPlanService:
    async def enqueue_plan(self, *, user_id: int, request: PlanAgentRequest) -> PlanAgentResponse:
        assert user_id == 1
        assert request.input
        return PlanAgentResponse(job_id="101", status="pending")


class StubExecuteService:
    async def enqueue_execute(self, *, user_id: int, request: ExecuteAgentRequest):
        from fileflash.schemas.agent import ExecuteAgentResponse

        assert user_id == 1
        assert request.plan_job_id == "101"
        return ExecuteAgentResponse(job_id="202", status="pending")

    async def cancel_job(self, *, user_id: int, job_id: str) -> dict:
        assert user_id == 1
        return {
            "jobId": job_id,
            "status": "canceled",
            "canceledAt": datetime.now(UTC),
        }


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agent_router, prefix="/api/v1")
    app.dependency_overrides[require_verified_user] = lambda: StubUser()
    app.dependency_overrides[get_agent_plan_service] = lambda: StubPlanService()
    app.dependency_overrides[get_agent_execute_service] = lambda: StubExecuteService()
    return TestClient(app)


def test_plan_agent_returns_job_envelope() -> None:
    with _build_client() as client:
        response = client.post(
            "/api/v1/agent/plan",
            json={"input": "整理下载文件夹"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["jobId"] == "101"
    assert body["data"]["taskType"] == "agent.plan"


def test_execute_agent_requires_plan_fields() -> None:
    with _build_client() as client:
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "planJobId": "101",
                "planHash": "sha256:abc",
                "approval": {
                    "confirmedBy": "1",
                    "confirmedAt": "2026-05-17T12:00:00Z",
                },
            },
        )
    assert response.status_code == 200
    assert response.json()["data"]["jobId"] == "202"


def test_cancel_agent_job() -> None:
    with _build_client() as client:
        response = client.post("/api/v1/agent/cancel/202")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "canceled"


def test_mock_planner_builds_plan_result() -> None:
    from fileflash.agents.mock_planner import build_mock_plan_result, should_simulate_failure

    request = PlanAgentRequest(input="organize my files")
    plan = build_mock_plan_result(job_id=99, request=request)
    assert plan.plan_job_id == "99"
    assert len(plan.proposed_actions) >= 2
    assert plan.requires_confirmation is True
    assert not should_simulate_failure("hello")
    assert should_simulate_failure("this will fail")


def test_policy_guard_blocks_writes_by_default() -> None:
    from fileflash.agents.harness.policy import PolicyGuard

    guard = PolicyGuard(allow_writes=False, execution_policy="confirm")
    decision = guard.evaluate_tool_call("drive.moveFile", "write")
    assert decision.allowed is False
