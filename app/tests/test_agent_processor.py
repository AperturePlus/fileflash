from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.processor import process_agent_job
from src.workers.contracts import WorkerJobMessage


@pytest.mark.asyncio
async def test_process_agent_job_plan_success() -> None:
    message = WorkerJobMessage(
        version=1,
        message_id="job-1-attempt-0",
        job_id=1,
        task_type="agent.plan",
        idempotency_key=None,
        attempt=0,
        max_attempts=3,
        trace_id="trace-1",
        requested_by="7",
        payload={
            "input": "list my files",
            "executionPolicy": "confirm",
        },
    )

    with (
        patch("src.agents.processor.mark_job_running", AsyncMock(return_value=message)),
        patch(
            "src.agents.processor._run_plan",
            AsyncMock(return_value=({"planHash": "sha256:x"}, "awaiting_confirm")),
        ),
        patch("src.agents.processor.mark_agent_job_succeeded", AsyncMock()) as mark_ok,
        patch("src.agents.processor.mark_agent_job_failed", AsyncMock()) as mark_fail,
    ):
        session_factory = Mock()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        begin_cm = AsyncMock()
        begin_cm.__aenter__ = AsyncMock(return_value=None)
        begin_cm.__aexit__ = AsyncMock(return_value=None)
        session.begin = Mock(return_value=begin_cm)
        session_factory.return_value = session

        await process_agent_job(1, session_factory=session_factory)

    mark_ok.assert_awaited()
    mark_fail.assert_not_awaited()
