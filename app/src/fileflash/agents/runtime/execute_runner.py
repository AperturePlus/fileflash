from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.settings import Settings, get_settings
from ...models import BackgroundJob
from ...models.enums import AgentInboxKind
from ...repositories import (
    AgentActionLogRepository,
    AgentInboxMessageRepository,
    AgentPlanRepository,
    AgentSettingsRepository,
    AgentSkillRepository,
    AgentWorkSessionRepository,
)
from ...schemas.agent import (
    AgentDataPolicy,
    AgentExecutionResult,
    AgentProposedAction,
    ExecuteAgentRequest,
    PlanAgentRequest,
)
from ..harness.ask import AskProtocol
from ..harness.event_bus import AgentEventBus, AgentEventEnvelope
from ..harness.permission import (
    PermissionResolver,
    _apply_setting_defaults,
)
from ..harness.policy import PolicyGuard
from ..harness.router import ToolCall, ToolRouter
from ..harness.tool_registry import ToolContext
from .llm import AnswerClient, AnthropicPlannerClient
from .reference_rules import is_symbolic_id_placeholder, parse_step_reference

logger = logging.getLogger(__name__)


class AgentJobCanceled(Exception):
    pass


class ExecuteRunner:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        policy_guard: PolicyGuard | None = None,
        event_bus: AgentEventBus | None = None,
        answer_client: AnswerClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.policy_guard = policy_guard or PolicyGuard()
        self.event_bus = event_bus
        self.answer_client = answer_client or AnthropicPlannerClient(settings=self.settings)

    async def run(self, *, db: AsyncSession, job: BackgroundJob) -> AgentExecutionResult:
        ask: AskProtocol | None = None
        if self.event_bus is not None:
            ask = AskProtocol(db=db, event_bus=self.event_bus, job_id=int(job.job_id))
            await ask.start()
        try:
            return await self._run(db=db, job=job, ask=ask)
        finally:
            if ask is not None:
                await ask.aclose()

    async def _run(
        self,
        *,
        db: AsyncSession,
        job: BackgroundJob,
        ask: AskProtocol | None,
    ) -> AgentExecutionResult:
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
        # Build the effective permission from the plan row (execution_policy +
        # data_policy_json) merged with the user's setting defaults (取最严).
        setting = await AgentSettingsRepository(db).get_by_user_id(int(job.requested_by))
        base_request = PlanAgentRequest.model_validate(
            {
                "chatSessionId": request.chat_session_id,
                "input": str(getattr(plan, "input_text", "") or "") or "-",
                "context": {"rootFolderId": "root"},
                "executionPolicy": getattr(plan, "execution_policy", "confirm") or "confirm",
                "dataPolicy": AgentDataPolicy.model_validate(
                    getattr(plan, "data_policy_json", None) or {}
                ).model_dump(by_alias=True, mode="json"),
            }
        )
        base_request = _apply_setting_defaults(base_request, setting)
        skill = None
        if getattr(plan, "chosen_skill_id", None):
            skill = await AgentSkillRepository(db).get_by_key(
                skill_key=str(plan.chosen_skill_id), user_id=int(job.requested_by)
            )
        permission = await PermissionResolver().effective(
            request=base_request,
            setting=setting,
            skill=skill,
            high_risk_confirmed=high_risk_confirmed,
        )
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

        inbox_repo = AgentInboxMessageRepository(db) if self.event_bus is not None else None
        paused = False
        for action in actions:
            await db.refresh(job)
            if job.cancel_requested_at is not None:
                raise AgentJobCanceled()
            if inbox_repo is not None:
                paused, skip_current = await self._handle_step_boundary_controls(
                    db=db,
                    job=job,
                    inbox_repo=inbox_repo,
                    action=action,
                    warnings=warnings,
                    paused=paused,
                )
                if skip_current:
                    continue

            decision = await self.policy_guard.evaluate(
                ctx=ToolContext(
                    db=db,
                    user_id=int(job.requested_by),
                    file_service=None,
                    folder_service=None,
                ),
                action=action,
                permission=permission,
                phase="executing",
            )
            if not decision.allowed:
                denied_started = datetime.now(UTC)
                await action_logs.append_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    tool_name=action.tool,
                    inputs_json=action.input,
                    status="denied",
                    started_at=denied_started,
                )
                await action_logs.finish_step(
                    job_id=int(job.job_id),
                    step_no=action.step,
                    outputs_json={},
                    status="denied",
                    duration_ms=0,
                    error_message="; ".join(decision.reasons)[:2000],
                )
                await db.commit()
                await self._publish_tool(
                    "tool.failed",
                    job_id=int(job.job_id),
                    step=action.step,
                    tool=action.tool,
                    payload={"denied": True, "reasons": decision.reasons},
                )
                warnings.append(
                    f"Step {action.step} denied by policy: {'; '.join(decision.reasons)}"
                )
                continue

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
                await self._publish_tool(
                    "tool.failed",
                    job_id=int(job.job_id),
                    step=action.step,
                    tool=action.tool,
                    payload={"errorMessage": f"{type(exc).__name__}: {exc}"[:2000]},
                )
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
            await self._publish_tool(
                "tool.started",
                job_id=int(job.job_id),
                step=action.step,
                tool=action.tool,
                payload={"input": resolved_input},
                emitted_at=started,
            )

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
                await self._publish_tool(
                    "tool.failed",
                    job_id=int(job.job_id),
                    step=action.step,
                    tool=action.tool,
                    payload={"errorMessage": f"{type(exc).__name__}: {exc}"[:2000]},
                )
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
            await self._publish_tool(
                "tool.succeeded",
                job_id=int(job.job_id),
                step=action.step,
                tool=action.tool,
                payload={"output": safe_output, "durationMs": duration_ms},
            )
            step_outputs[action.step] = safe_output
            applied += 1

        skipped = max(0, len(actions) - applied)
        if skipped:
            warnings.append(f"{skipped} action(s) were skipped.")
        await work_sessions.close_session(job_id=int(job.job_id), status="closed")
        await db.commit()
        answer = await _build_execution_answer(
            task_input=str(getattr(plan, "input_text", "") or ""),
            actions=actions,
            step_outputs=step_outputs,
            answer_client=self.answer_client,
        )
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

    async def _handle_step_boundary_controls(
        self,
        *,
        db: AsyncSession,
        job: BackgroundJob,
        inbox_repo: AgentInboxMessageRepository,
        action: AgentProposedAction,
        warnings: list[str],
        paused: bool,
    ) -> tuple[bool, bool]:
        while True:
            skip_current = False
            pending = await inbox_repo.list_pending_controls(job_id=int(job.job_id))
            for ctrl in pending:
                kind = AgentInboxKind(ctrl.kind)
                if kind == AgentInboxKind.CONTROL_CANCEL:
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                    job.cancel_requested_at = datetime.now(UTC)
                    await db.commit()
                    raise AgentJobCanceled()
                if kind == AgentInboxKind.CONTROL_PAUSE:
                    paused = True
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                    await self._publish_state("agent.paused", job_id=int(job.job_id))
                elif kind == AgentInboxKind.CONTROL_RESUME:
                    paused = False
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                    await self._publish_state("agent.resumed", job_id=int(job.job_id))
                elif kind == AgentInboxKind.CONTROL_SKIP:
                    if _control_step(ctrl) != action.step:
                        continue
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                    warnings.append(f"Step {action.step} skipped by user")
                    skip_current = True
                elif kind == AgentInboxKind.CONTROL_DENY:
                    if _control_step(ctrl) != action.step:
                        continue
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                    reason = _control_reason(ctrl) or "denied by user"
                    warnings.append(f"Step {action.step} denied by user: {reason}")
                    skip_current = True
                elif kind == AgentInboxKind.CONTROL_APPROVE:
                    if _control_step(ctrl) != action.step:
                        continue
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                else:
                    await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
            await db.commit()
            if skip_current:
                return paused, True
            if not paused:
                return paused, False
            await asyncio.sleep(0.1)

    async def _publish_state(self, event_type: str, *, job_id: int) -> None:
        if self.event_bus is None:
            return
        try:
            await self.event_bus.publish(
                AgentEventEnvelope(
                    job_id=job_id,
                    event_type=event_type,
                    payload={},
                    emitted_at=datetime.now(UTC),
                )
            )
        except Exception:
            logger.exception(
                "Failed to publish state event jobId=%s eventType=%s",
                job_id,
                event_type,
            )

    async def _publish_tool(
        self,
        event_type: str,
        *,
        job_id: int,
        step: int,
        tool: str,
        payload: dict[str, Any],
        emitted_at: datetime | None = None,
    ) -> None:
        if self.event_bus is None:
            return
        try:
            await self.event_bus.publish(
                AgentEventEnvelope(
                    job_id=job_id,
                    event_type=event_type,
                    payload={"step": int(step), "tool": str(tool), **payload},
                    emitted_at=emitted_at or datetime.now(UTC),
                )
            )
        except Exception:
            logger.exception(
                "Failed to publish tool event jobId=%s eventType=%s step=%s tool=%s",
                job_id,
                event_type,
                step,
                tool,
            )


def _parse_job_id(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid planJobId") from exc
    if value <= 0:
        raise ApiError(status_code=400, code=400, message="Invalid planJobId")
    return value


def _control_metadata(ctrl: Any) -> dict[str, Any]:
    payload = getattr(ctrl, "payload_json", None)
    if not isinstance(payload, dict):
        return {}
    metadata = payload.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _control_step(ctrl: Any) -> int | None:
    try:
        value = int(_control_metadata(ctrl).get("step"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _control_reason(ctrl: Any) -> str | None:
    value = _control_metadata(ctrl).get("reason")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


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


async def _build_execution_answer(
    *,
    task_input: str = "",
    actions: list[AgentProposedAction],
    step_outputs: dict[int, dict[str, Any]],
    answer_client: AnswerClient,
) -> str | None:
    if not actions:
        return None
    user_prompt = _answer_user_prompt(
        task_input=task_input,
        actions=actions,
        step_outputs=step_outputs,
    )
    text = await answer_client.create_answer(
        system_prompt=_answer_system_prompt(),
        user_prompt=user_prompt,
        max_tokens=640,
        reasoning_effort="low",
    )
    answer = _normalize_answer(text)
    if answer is None:
        raise ApiError(status_code=502, code=502, message="Agent answer model returned empty response")
    return answer


def _answer_system_prompt() -> str:
    return (
        "You are FileFlash execution answer generator. "
        "Only describe results that are present in tool outputs. "
        "Do not invent filenames, counts, or paths. "
        "Keep the response concise and user-facing in the same language as the user input."
    )


def _answer_user_prompt(
    *,
    task_input: str,
    actions: list[AgentProposedAction],
    step_outputs: dict[int, dict[str, Any]],
) -> str:
    payload_actions: list[dict[str, Any]] = []
    for action in sorted(actions, key=lambda item: item.step):
        payload_actions.append(
            {
                "step": action.step,
                "tool": action.tool,
                "sideEffect": action.side_effect,
                "input": action.input,
                "output": _compact_output(step_outputs.get(action.step)),
            }
        )
    payload = {
        "task": task_input,
        "actions": payload_actions,
        "responseGuidance": {
            "includeNamesWhenAvailable": True,
            "mentionTruncationWhenProvided": True,
            "ifAmbiguous": "state candidate count and ask for clarification",
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _compact_output(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(text) <= 12_000:
        return value
    compact = dict(value)
    compact["truncated"] = True
    compact["truncatedFields"] = sorted(compact.keys())[:16]
    compact.pop("items", None)
    compact.pop("sampleItems", None)
    return compact


def _normalize_answer(text: str) -> str | None:
    candidate = str(text or "").strip()
    if not candidate:
        return None
    candidate = " ".join(candidate.split())
    if len(candidate) > 1200:
        candidate = candidate[:1200].rstrip() + "…"
    return candidate
