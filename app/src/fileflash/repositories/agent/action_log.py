from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentActionLog, AgentWorkSession


class AgentActionLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def append_step(
        self,
        *,
        job_id: int,
        step_no: int,
        tool_name: str,
        inputs_json: dict[str, Any] | None = None,
        status: str = "running",
        started_at: datetime | None = None,
    ) -> AgentActionLog:
        entry = AgentActionLog(
            job_id=job_id,
            step_no=step_no,
            tool_name=tool_name,
            inputs_json=jsonable_encoder(inputs_json or {}),
            status=status,
            started_at=started_at or datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        await self._refresh_work_session_metrics_for_job(job_id=job_id)
        return entry

    async def finish_step(
        self,
        *,
        job_id: int,
        step_no: int,
        outputs_json: dict[str, Any] | None = None,
        status: str = "succeeded",
        duration_ms: int | None = None,
        error_message: str | None = None,
        finished_at: datetime | None = None,
    ) -> AgentActionLog | None:
        entry = await self.db.scalar(
            select(AgentActionLog).where(
                AgentActionLog.job_id == job_id,
                AgentActionLog.step_no == step_no,
            )
        )
        if entry is None:
            return None

        entry.outputs_json = jsonable_encoder(outputs_json or {})
        entry.status = status
        entry.duration_ms = duration_ms
        entry.error_message = error_message
        entry.finished_at = finished_at or datetime.now(UTC)
        await self.db.flush()
        await self._refresh_work_session_metrics_for_job(job_id=job_id)
        return entry

    async def list_by_job_id(self, *, job_id: int) -> list[AgentActionLog]:
        result = await self.db.scalars(
            select(AgentActionLog)
            .where(AgentActionLog.job_id == job_id)
            .order_by(AgentActionLog.step_no.asc())
        )
        return list(result)

    async def _refresh_work_session_metrics_for_job(self, *, job_id: int) -> None:
        work_session_id = await self.db.scalar(
            select(AgentWorkSession.work_session_id).where(AgentWorkSession.job_id == job_id)
        )
        if work_session_id is None:
            return
        await self.db.execute(
            text("SELECT agent_refresh_work_session_metrics(:work_session_id)"),
            {"work_session_id": work_session_id},
        )
