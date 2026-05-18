from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.settings import Settings, get_settings
from ...models.enums import AgentExecutionPolicy
from ...repositories import AgentPlanRepository
from ...schemas.agent import PlanAgentRequest
from ..llm import build_chat_model
from ..mock_planner import build_mock_plan_result, should_simulate_failure


class PlanRunner:
    def __init__(
        self,
        *,
        db: AsyncSession,
        plans: AgentPlanRepository,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.plans = plans
        self.settings = settings or get_settings()

    async def run(self, *, job_id: int, user_id: int, payload: dict) -> dict:
        request = PlanAgentRequest.model_validate(payload)
        if should_simulate_failure(request.input):
            raise RuntimeError("Agent planning failed. Try a different prompt.")

        plan_result = await self._build_plan(job_id=job_id, request=request)
        await self.plans.create(
            values={
                "job_id": job_id,
                "user_id": user_id,
                "input_text": request.input,
                "context_json": request.context.model_dump(by_alias=True),
                "execution_policy": AgentExecutionPolicy(request.execution_policy),
                "data_policy_json": request.data_policy.model_dump(by_alias=True),
                "chosen_skill_id": plan_result.chosen_skill.id if plan_result.chosen_skill else None,
                "proposed_actions_json": [a.model_dump(by_alias=True) for a in plan_result.proposed_actions],
                "plan_hash": plan_result.plan_hash,
                "summary": plan_result.summary,
                "cost_estimate_json": plan_result.cost_estimate.model_dump(by_alias=True),
            },
        )
        return plan_result.model_dump(by_alias=True, mode="json")

    async def _build_plan(self, *, job_id: int, request: PlanAgentRequest):
        model = build_chat_model(self.settings)
        if model is None:
            return build_mock_plan_result(job_id=job_id, request=request)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            system = (
                "You are a file management planning assistant. "
                "Respond with a concise plan summary only; structured actions are filled by the system."
            )
            response = await model.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=request.input),
                ]
            )
            summary_text = str(getattr(response, "content", "") or "").strip()
            plan = build_mock_plan_result(job_id=job_id, request=request)
            if summary_text:
                plan = plan.model_copy(update={"summary": summary_text[:2000]})
            return plan
        except Exception:
            return build_mock_plan_result(job_id=job_id, request=request)
