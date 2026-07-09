from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import and_, select

from ...core.errors import ApiError
from ...core.mime import resolve_file_mime_type
from ...models import File
from ...models.enums import FileStatus
from ...schemas.agent import AgentProposedAction
from .permission import EffectivePermission
from .tool_registry import REGISTRY, ToolContext

_CONTENT_READ_TOOLS = frozenset({"drive.readFile"})
_Phase = Literal["planning", "executing"]


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
    async def evaluate(
        self,
        *,
        ctx: ToolContext,
        action: AgentProposedAction,
        permission: EffectivePermission,
        phase: _Phase,
    ) -> PolicyDecision:
        try:
            spec = REGISTRY.get(action.tool)
        except KeyError:
            return PolicyDecision(
                allowed=False,
                reasons=[f"Unsupported agent tool: {action.tool}"],
            )
        if action.tool not in permission.allowed_tools:
            return PolicyDecision(
                allowed=False,
                reasons=[f"Tool not permitted by active skill/policy: {action.tool}"],
            )
        if spec.side_effect == "read" and action.tool in _CONTENT_READ_TOOLS:
            decision = await self._check_content_read(
                ctx=ctx, action=action, permission=permission
            )
            if decision is not None:
                return decision
        if spec.risk_level == "high" and not permission.high_risk_confirmed:
            return PolicyDecision(
                allowed=False,
                reasons=["High-risk action requires explicit confirmation."],
            )
        if permission.execution_policy == "planOnly" and phase == "executing":
            return PolicyDecision(
                allowed=False,
                reasons=["planOnly policy forbids execution."],
            )
        return PolicyDecision(allowed=True)

    async def _check_content_read(
        self,
        *,
        ctx: ToolContext,
        action: AgentProposedAction,
        permission: EffectivePermission,
    ) -> PolicyDecision | None:
        if permission.deny_read_content:
            return PolicyDecision(
                allowed=False,
                reasons=["File content access disabled by dataPolicy."],
            )
        max_bytes = self._byte_range(action.input)
        if max_bytes > permission.data_policy.max_read_bytes:
            return PolicyDecision(
                allowed=False,
                reasons=[
                    f"Requested bytes ({max_bytes}) exceed max_read_bytes "
                    f"({permission.data_policy.max_read_bytes})."
                ],
            )
        mime = await _resolve_target_mime(ctx=ctx, action=action)
        if mime is not None and not _mime_allowed(
            mime, permission.data_policy.allowed_mime_types
        ):
            return PolicyDecision(
                allowed=False,
                reasons=[f"File mime '{mime}' not in allowed_mime_types."],
            )
        return None

    def _byte_range(self, action_input: dict[str, Any]) -> int:
        max_bytes = int(action_input.get("maxBytes", 262144) or 262144)
        offset = int(action_input.get("offset", 0) or 0)
        return max_bytes + offset


def _mime_allowed(mime: str, allowed: list[str]) -> bool:
    lowered = mime.lower()
    return any(fnmatch.fnmatch(lowered, pattern.lower()) for pattern in allowed)


async def _resolve_target_mime(
    *, ctx: ToolContext, action: AgentProposedAction
) -> str | None:
    file_id = action.input.get("fileId") or action.input.get("id")
    if file_id is None:
        return None
    try:
        parsed = int(str(file_id))
    except (TypeError, ValueError):
        return None
    row = await ctx.db.scalar(
        select(File).where(
            and_(
                File.file_id == parsed,
                File.owner_id == ctx.user_id,
                File.status == FileStatus.ACTIVE,
            )
        )
    )
    if row is None:
        return None
    return resolve_file_mime_type(
        mime_type=row.mime_type,
        file_ext=row.file_ext,
        file_name=row.file_name,
    )


__all__ = [
    "PolicyDecision",
    "PolicyGuard",
    "classify_tool_risk",
    "classify_tool_side_effect",
    "normalize_action_risk",
]
