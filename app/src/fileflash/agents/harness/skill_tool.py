from __future__ import annotations

from typing import Any

from ...models import AgentUserSetting
from ...repositories import AgentSkillRepository
from ...schemas.agent import PlanAgentRequest
from .permission import EffectivePermission, PermissionResolver
from .tool_registry import REGISTRY, ToolContext, ToolSpec


async def _use_skill_handler(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    # This handler is never reached at runtime — the planner intercepts agent.useSkill
    # before dispatch. It exists only so the tool has a valid handler for registration.
    return {"bound": False, "message": "agent.useSkill must be intercepted by the planner."}


def register_use_skill_tool() -> None:
    try:
        REGISTRY.get("agent.useSkill")
        return  # already registered
    except KeyError:
        pass
    REGISTRY.register(
        ToolSpec(
            name="agent.useSkill",
            description=(
                "Adopt a skill to constrain your tool set to that skill's whitelist. "
                "Call once during planning if a skill fits; optional. Returns the bound "
                "tool list. Use skillKey 'none' to decline all skills. "
                "Cannot be used during execution."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "skillKey": {
                        "type": "string",
                        "description": "One of the offered skill keys, or 'none' to decline.",
                    }
                },
                "required": ["skillKey"],
            },
            side_effect="read",
            risk_level="low",
            requires_confirmation=False,
            handler=_use_skill_handler,
        )
    )


async def bind_skill_in_planner(
    *,
    db: Any,
    user_id: int,
    skill_key: str,
    candidates: list[Any],
    request: PlanAgentRequest,
    setting: AgentUserSetting | None,
    current_permission: EffectivePermission,
) -> tuple[EffectivePermission, dict[str, Any]]:
    if skill_key == "none":
        return current_permission, {"bound": False, "declined": True, "skillKey": "none"}
    candidate_keys = {getattr(c, "skill_key", None) for c in candidates}
    if skill_key not in candidate_keys:
        return current_permission, {
            "bound": False,
            "skillKey": skill_key,
            "message": f"Unknown or unoffered skill key: {skill_key}",
        }
    repo = AgentSkillRepository(db)
    skill = await repo.get_by_key(skill_key=skill_key, user_id=user_id)
    if skill is None:
        return current_permission, {
            "bound": False,
            "skillKey": skill_key,
            "message": f"Skill not found: {skill_key}",
        }
    new_perm = await PermissionResolver().effective(
        request=request,
        setting=setting,
        skill=skill,
        high_risk_confirmed=current_permission.high_risk_confirmed,
    )
    return new_perm, {
        "bound": True,
        "skillKey": skill_key,
        "allowedTools": sorted(new_perm.allowed_tools),
    }


# Register on import so the LLM sees the tool whenever builtin tools are registered.
register_use_skill_tool()


__all__ = ["bind_skill_in_planner", "register_use_skill_tool"]
