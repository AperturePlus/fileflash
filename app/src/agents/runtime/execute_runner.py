from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ...models import BackgroundJob
from ...repositories import AgentActionLogRepository, AgentPlanRepository, AgentWorkSessionRepository
from ...schemas.agent import AgentExecutionResult, AgentProposedAction
from ..harness.policy import PolicyGuard
from ..harness.router import ToolCall, ToolRouter
from ..mock_planner import should_simulate_failure
from ..tools.drive import DriveToolContext


class ExecuteRunner:
    def __init__(
        self,
        *,
        db: AsyncSession,
        plans: AgentPlanRepository,
        action_logs: AgentActionLogRepository,
        work_sessions: AgentWorkSessionRepository,
        allow_write_tools: bool = False,
    ) -> None:
        self.db = db
        self.plans = plans
        self.action_logs = action_logs
        self.work_sessions = work_sessions
        self.allow_write_tools = allow_write_tools

    async def run(self, *, job_id: int, user_id: int, payload: dict) -> dict:
        plan_job_id = int(payload["planJobId"])
        plan_hash = str(payload["planHash"])
        plan_row = await self.plans.get_for_execute_binding(
            job_id=plan_job_id,
            user_id=user_id,
            plan_hash=plan_hash,
        )
        if plan_row is None:
            raise RuntimeError("Plan not found or planHash mismatch")

        plan_job = await self.db.get(BackgroundJob, plan_job_id)
        source_input = ""
        if plan_job and plan_job.payload:
            source_input = str(plan_job.payload.get("input") or "")
        if should_simulate_failure(source_input):
            raise RuntimeError("Agent execution failed. You can retry with a safer plan.")

        await self.work_sessions.create_for_job(job_id=job_id, user_id=user_id, status="active")

        raw_actions = plan_row.proposed_actions_json
        if isinstance(raw_actions, dict):
            raw_actions = raw_actions.get("items", [])
        proposed = [AgentProposedAction.model_validate(item) for item in (raw_actions or [])]

        data_policy = dict(plan_row.data_policy_json or {})
        drive = DriveToolContext(db=self.db, user_id=user_id, allow_writes=self.allow_write_tools)
        router = ToolRouter(drive=drive)
        execution_policy = str(plan_row.execution_policy.value if hasattr(plan_row.execution_policy, "value") else plan_row.execution_policy)
        policy = PolicyGuard(
            allow_writes=self.allow_write_tools,
            data_policy=data_policy,
            execution_policy=execution_policy,
        )

        applied = 0
        skipped = 0
        warnings: list[str] = []

        for action in proposed:
            if await self._is_cancel_requested(job_id):
                raise RuntimeError("Execution canceled by user")

            decision = policy.evaluate_tool_call(action.tool, action.side_effect)
            if not decision.allowed:
                skipped += 1
                warnings.extend(decision.reasons)
                continue

            step = await self.action_logs.append_step(
                job_id=job_id,
                step_no=action.step,
                tool_name=action.tool,
                inputs_json=action.input,
                status="running",
            )
            try:
                output = await router.execute(ToolCall(tool=action.tool, inputs=action.input))
                if output.get("skipped"):
                    skipped += 1
                    warnings.append(str(output.get("reason") or "skipped"))
                elif output.get("error"):
                    skipped += 1
                    warnings.append(str(output["error"]))
                else:
                    applied += 1
                await self.action_logs.finish_step(
                    job_id=job_id,
                    step_no=action.step,
                    outputs_json=output,
                    status="succeeded",
                )
            except Exception as exc:
                await self.action_logs.finish_step(
                    job_id=job_id,
                    step_no=action.step,
                    outputs_json={"error": str(exc)},
                    status="failed",
                    error_message=str(exc),
                )
                warnings.append(f"Step {action.step} failed: {exc}")

        await self.work_sessions.close_session(job_id=job_id, status="closed")

        result = AgentExecutionResult(
            plan_job_id=str(plan_job_id),
            execute_job_id=str(job_id),
            summary=f"Execution completed with {applied} applied and {skipped} skipped steps.",
            applied_actions=applied,
            skipped_actions=skipped,
            warnings=warnings,
            finished_at=datetime.now(UTC),
        )
        return result.model_dump(by_alias=True, mode="json")

    async def _is_cancel_requested(self, job_id: int) -> bool:
        job = await self.db.get(BackgroundJob, job_id)
        return job is not None and job.cancel_requested_at is not None
