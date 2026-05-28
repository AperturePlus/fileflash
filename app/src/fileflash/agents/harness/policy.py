from __future__ import annotations

from dataclasses import dataclass, field

from ...schemas.agent import AgentProposedAction
from .tool_registry import REGISTRY


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def classify_tool_side_effect(tool_name: str) -> str:
    try:
        return REGISTRY.get(tool_name).side_effect
    except KeyError:
        return "write"


def classify_tool_risk(tool_name: str) -> str:
    try:
        return REGISTRY.get(tool_name).risk_level
    except KeyError:
        return "high"


def normalize_action_risk(action: AgentProposedAction) -> AgentProposedAction:
    risk_level = classify_tool_risk(action.tool)
    requires_confirmation = action.requires_confirmation or risk_level == "high"
    reason = action.confirmation_reason
    if risk_level == "high" and not reason:
        reason = (
            "Deleting files or folders is a high-risk action and requires explicit confirmation."
        )
    return action.model_copy(
        update={
            "side_effect": classify_tool_side_effect(action.tool),
            "risk_level": risk_level,
            "requires_confirmation": requires_confirmation,
            "confirmation_reason": reason,
        }
    )


class PolicyGuard:
    async def evaluate_tool_call(
        self,
        *,
        tool_name: str,
        high_risk_confirmed: bool = False,
    ) -> PolicyDecision:
        try:
            REGISTRY.get(tool_name)
        except KeyError:
            return PolicyDecision(
                allowed=False,
                reasons=[f"Unsupported agent tool: {tool_name}"],
            )
        if classify_tool_risk(tool_name) == "high" and not high_risk_confirmed:
            return PolicyDecision(
                allowed=False,
                reasons=["High-risk delete action requires explicit user confirmation."],
            )
        return PolicyDecision(allowed=True)
