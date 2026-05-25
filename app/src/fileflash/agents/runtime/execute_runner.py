from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
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
from .reference_rules import is_symbolic_id_placeholder, parse_step_reference


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

            safe_output = jsonable_encoder(output)
            duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            await action_logs.finish_step(
                job_id=int(job.job_id),
                step_no=action.step,
                outputs_json=safe_output,
                status="succeeded",
                duration_ms=duration_ms,
            )
            await db.commit()
            step_outputs[action.step] = safe_output
            applied += 1

        skipped = max(0, len(actions) - applied)
        if skipped:
            warnings.append(f"{skipped} action(s) were skipped.")
        await work_sessions.close_session(job_id=int(job.job_id), status="closed")
        await db.commit()
        answer = _build_execution_answer(actions=actions, step_outputs=step_outputs)
        return AgentExecutionResult(
            plan_job_id=str(plan_job_id),
            execute_job_id=str(job.job_id),
            summary=f"Execution completed with {applied} applied action(s).",
            answer=answer,
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


def _resolve_references(
    value: Any,
    step_outputs: dict[int, dict[str, Any]],
    *,
    field_name: str | None = None,
    field_path: str = "input",
) -> Any:
    if isinstance(value, str):
        reference = parse_step_reference(value)
        if reference is not None:
            step, path = reference
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
        if is_symbolic_id_placeholder(value=value, field_name=field_name):
            raise ApiError(
                status_code=409,
                code=409,
                message=(
                    f"Invalid tool input at '{field_path}': unresolved placeholder '{value}'. "
                    "Use '$stepN.field' references."
                ),
            )
        return value
    if isinstance(value, list):
        return [
            _resolve_references(
                item,
                step_outputs,
                field_name=field_name,
                field_path=f"{field_path}[{index}]",
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _resolve_references(
                item,
                step_outputs,
                field_name=key,
                field_path=f"{field_path}.{key}",
            )
            for key, item in value.items()
        }
    return value


def _build_execution_answer(
    *,
    actions: list[AgentProposedAction],
    step_outputs: dict[int, dict[str, Any]],
) -> str | None:
    for action in actions:
        if action.tool != "drive.countFiles":
            continue
        output = step_outputs.get(action.step)
        if not isinstance(output, dict):
            continue
        return _count_files_answer(output)

    if actions and all(action.side_effect == "read" for action in actions):
        return f"已完成 {len(step_outputs)} 个只读操作。"
    return None


def _count_files_answer(output: dict[str, Any]) -> str:
    total_items = int(output.get("totalItems") or 0)
    category = str(output.get("category") or "").strip().lower()
    if category == "video":
        return f"你上传了 {total_items} 部电影（按视频文件统计）。"
    if category == "audio":
        return f"你上传了 {total_items} 个音频文件。"
    if category == "image":
        return f"你上传了 {total_items} 张图片。"
    if category == "document":
        return f"你上传了 {total_items} 个文档。"
    if category == "archive":
        return f"你上传了 {total_items} 个压缩包。"
    return f"你上传了 {total_items} 个文件。"
