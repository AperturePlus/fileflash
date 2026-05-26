from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from test_agent_inbox_repository import InboxSession

from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.agents.runtime import execute_runner as execute_module
from fileflash.agents.runtime.execute_runner import AgentJobCanceled, ExecuteRunner
from fileflash.models import BackgroundJob
from fileflash.models.enums import AgentInboxKind


class RuntimeInboxSession(InboxSession):
    async def refresh(self, _job: BackgroundJob) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _execute_job() -> BackgroundJob:
    now = datetime.now(UTC)
    return BackgroundJob(
        job_id=800,
        task_type="agent.execute",
        status="running",
        payload={
            "planJobId": "500",
            "planHash": "sha256:test",
            "approval": {
                "confirmedBy": "7",
                "confirmedAt": now.isoformat(),
                "highRiskConfirmed": False,
            },
        },
        result={},
        requested_by=7,
        scheduled_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_user_pause_then_cancel_via_inbox(monkeypatch: pytest.MonkeyPatch):
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

    session = RuntimeInboxSession()
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=session, event_bus=bus)  # type: ignore[arg-type]
    job = _execute_job()
    seen_events: list[str] = []

    await inbox.handle(job_id=int(job.job_id), kind=AgentInboxKind.CONTROL_PAUSE, payload={})
    await session.commit()

    async def cancel_when_paused() -> None:
        async with bus.subscribe(job_id=int(job.job_id)) as stream:
            while True:
                event = await stream.next(timeout=2.0)
                seen_events.append(event.event_type)
                if event.event_type == "agent.paused":
                    await inbox.handle(
                        job_id=int(job.job_id),
                        kind=AgentInboxKind.CONTROL_CANCEL,
                        payload={},
                    )
                    await session.commit()
                    return

    listener = asyncio.create_task(cancel_when_paused())
    await asyncio.sleep(0)
    with pytest.raises(AgentJobCanceled):
        await ExecuteRunner(event_bus=bus).run(db=session, job=job)  # type: ignore[arg-type]
    await listener

    assert "agent.paused" in seen_events
    assert job.cancel_requested_at is not None
