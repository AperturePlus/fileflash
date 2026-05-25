from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .common import CamelModel

AgentExecutionPolicy = Literal["planOnly", "confirm", "autopilot"]
AgentActionSideEffect = Literal["read", "write"]
AgentRiskLevel = Literal["low", "medium", "high"]
AgentReasoningEffort = Literal["adaptive", "low", "medium", "high", "xhigh", "max"]
AgentJobPhase = Literal[
    "planning",
    "awaiting_confirm",
    "executing",
    "awaiting_commit",
    "completed",
    "failed",
    "canceled",
]


class AgentDataPolicy(CamelModel):
    allow_file_content: bool = False
    max_read_bytes: int = Field(default=1_048_576, ge=0)
    allowed_mime_types: list[str] = Field(default_factory=lambda: ["*/*"])


class AgentHints(CamelModel):
    prefer_skill_id: str | None = None
    max_steps: int = Field(default=12, ge=1, le=100)
    budget_tokens: int = Field(default=8_000, ge=1)
    reasoning_effort: AgentReasoningEffort = "adaptive"


class AgentPlanContext(CamelModel):
    root_folder_id: str = "root"
    selected_file_ids: list[str] = Field(default_factory=list)
    selected_folder_ids: list[str] = Field(default_factory=list)
    current_path: str = "/My Files"


class PlanAgentRequest(CamelModel):
    input: str = Field(min_length=1, max_length=4_000)
    context: AgentPlanContext
    execution_policy: AgentExecutionPolicy = "confirm"
    data_policy: AgentDataPolicy = Field(default_factory=AgentDataPolicy)
    hints: AgentHints = Field(default_factory=AgentHints)


class PlanAgentResponse(CamelModel):
    job_id: str
    status: str
    task_type: Literal["agent.plan"] = "agent.plan"


class AgentProposedAction(CamelModel):
    step: int = Field(ge=1)
    tool: str = Field(min_length=1, max_length=120)
    input: dict[str, Any] = Field(default_factory=dict)
    side_effect: AgentActionSideEffect
    risk_level: AgentRiskLevel = "low"
    requires_confirmation: bool = False
    confirmation_reason: str | None = None


class AgentCostEstimate(CamelModel):
    tokens: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    duration_sec_estimate: int = Field(ge=0)


class AgentChosenSkill(CamelModel):
    id: str
    name: str


class AgentPlanResult(CamelModel):
    plan_job_id: str
    plan_hash: str
    chosen_skill: AgentChosenSkill | None = None
    proposed_actions: list[AgentProposedAction]
    summary: str
    requires_confirmation: bool
    cost_estimate: AgentCostEstimate


class AgentApproval(CamelModel):
    confirmed_by: str
    confirmed_at: datetime
    high_risk_confirmed: bool = False
    high_risk_confirmed_at: datetime | None = None


class ExecuteAgentRequest(CamelModel):
    plan_job_id: str
    plan_hash: str
    approval: AgentApproval


class ExecuteAgentResponse(CamelModel):
    job_id: str
    status: str
    task_type: Literal["agent.execute"] = "agent.execute"


class CancelAgentResponse(CamelModel):
    job_id: str
    status: str
    canceled_at: datetime


class AgentExecutionResult(CamelModel):
    plan_job_id: str
    execute_job_id: str
    summary: str
    applied_actions: int = Field(ge=0)
    skipped_actions: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    finished_at: datetime


__all__ = [
    "AgentActionSideEffect",
    "AgentApproval",
    "AgentChosenSkill",
    "AgentCostEstimate",
    "AgentDataPolicy",
    "AgentExecutionPolicy",
    "AgentExecutionResult",
    "AgentHints",
    "AgentJobPhase",
    "AgentPlanContext",
    "AgentPlanResult",
    "AgentProposedAction",
    "AgentReasoningEffort",
    "AgentRiskLevel",
    "CancelAgentResponse",
    "ExecuteAgentRequest",
    "ExecuteAgentResponse",
    "PlanAgentRequest",
    "PlanAgentResponse",
]
