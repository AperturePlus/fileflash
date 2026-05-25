from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models import BackgroundJob
from ...repositories import (
    AgentActionLogRepository,
    AgentPlanRepository,
    AgentWorkSessionRepository,
)
from ...schemas.agent import AgentExecutionResult, AgentProposedAction, ExecuteAgentRequest
from ..harness.policy import PolicyGuard
from ..harness.router import ToolCall, ToolRouter


class AgentJobCanceled(Exception):
    pass


class ExecuteRunner:
    def __init__(self, *, policy_guard: PolicyGuard | None = None) -> None:
        self.policy_guard = policy_guard or PolicyGuard()

    async def run(self, *, db: AsyncSession, job: BackgroundJob) -> AgentExecutionResult:
        if job.requested_by is None:
            raise ApiError(status_code=400, code=400, message="Agent job is missing requestedBy")
        request = ExecuteAgentRequest.model_validate(dict(job.payload or {}))
        plan_job_id = _parse_job_id(request.plan_job_id)
        plan_repo = AgentPlanRepository(db)
        work_sessions = AgentWorkSessionRepository(db)
        plan = await plan_repo.get_for_execute_binding(
            job_id=plan_job_id,
            user_id=int(job.requested_by),
            plan_hash=request.plan_hash,
        )
        if plan is None:
            raise ApiError(status_code=409, code=409, message="Plan hash mismatch")

        actions = [
            AgentProposedAction.model_validate(item)
            for item in (plan.proposed_actions_json or [])
        ]
        high_risk_confirmed = bool(request.approval.high_risk_confirmed)
        router = ToolRouter(db=db, user_id=int(job.requested_by))
        action_logs = AgentActionLogRepository(db)
        step_outputs: dict[int, dict[str, Any]] = {}
        applied = 0
        warnings: list[str] = []
        await work_sessions.create_for_job(
            job_id=int(job.job_id),
            user_id=int(job.requested_by),
            checkpoint_json={"planJobId": str(plan_job_id), "planHash": request.plan_hash},
        )
        await db.commit()

        for action in actions:
            await db.refresh(job)
            if job.cancel_requested_at is not None:
                raise AgentJobCanceled()

            decision = await self.policy_guard.evaluate_tool_call(
                tool_name=action.tool,
                high_risk_confirmed=high_risk_confirmed,
            )
            if not decision.allowed:
                raise ApiError(
                    status_code=409,
                    code=409,
                    message="High-risk action requires confirmation",
                    data={"reasons": decision.reasons, "step": action.step, "tool": action.tool},
                )

            started = datetime.now(UTC)
            try:
                resolved_input = _resolve_references(action.input, step_outputs)
            except Exception as exc:
                duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
                await action_logs.append_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    tool_name=action.tool,
                    inputs_json=action.input,
                    status="failed",
                    started_at=started,
                )
                await action_logs.finish_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    outputs_json={},
                    status="failed",
                    duration_ms=duration_ms,
                    error_message=f"{type(exc).__name__}: {exc}"[:2000],
                )
                await db.commit()
                raise

            await action_logs.append_step(
                job_id=int(job.job_id),
                step_no=action.step,
                tool_name=action.tool,
                inputs_json=resolved_input,
                status="running",
                started_at=started,
            )
            await db.commit()

            try:
                output = await router.dispatch(
                    ToolCall(tool_name=action.tool, arguments=resolved_input)
                )
            except Exception as exc:
                await db.rollback()
                duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
                await action_logs.finish_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    outputs_json={},
                    status="failed",
                    duration_ms=duration_ms,
                    error_message=f"{type(exc).__name__}: {exc}"[:2000],
                )
                await db.commit()
                raise

            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            await action_logs.finish_step(
                job_id=int(job.job_id),
                step_no=action.step,
                outputs_json=output,
                status="succeeded",
                duration_ms=duration_ms,
            )
            await db.commit()
            step_outputs[action.step] = output
            applied += 1

        skipped = max(0, len(actions) - applied)
        if skipped:
            warnings.append(f"{skipped} action(s) were skipped.")
        await work_sessions.close_session(job_id=int(job.job_id), status="closed")
        await db.commit()
        return AgentExecutionResult(
            plan_job_id=str(plan_job_id),
            execute_job_id=str(job.job_id),
            summary=f"Execution completed with {applied} applied action(s).",
            applied_actions=applied,
            skipped_actions=skipped,
            warnings=warnings,
            finished_at=datetime.now(UTC),
        )


def _parse_job_id(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid planJobId") from exc
    if value <= 0:
        raise ApiError(status_code=400, code=400, message="Invalid planJobId")
    return value


_STEP_REF = re.compile(r"^\$step(?P<step>\d+)\.(?P<path>[A-Za-z0-9_.-]+)$")


def _resolve_references(value: Any, step_outputs: dict[int, dict[str, Any]]) -> Any:
    if isinstance(value, str):
        match = _STEP_REF.match(value)
        if not match:
            return value
        step = int(match.group("step"))
        path = match.group("path").split(".")
        current: Any = step_outputs.get(step)
        for part in path:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
            if current is None:
                raise ApiError(
                    status_code=409,
                    code=409,
                    message=f"Unable to resolve tool reference: {value}",
                )
        return current
    if isinstance(value, list):
        return [_resolve_references(item, step_outputs) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_references(item, step_outputs) for key, item in value.items()}
    return value
