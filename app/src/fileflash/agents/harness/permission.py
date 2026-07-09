from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...models import AgentUserSetting
from ...schemas.agent import AgentDataPolicy, AgentExecutionPolicy, PlanAgentRequest
from .tool_registry import REGISTRY


@dataclass(frozen=True, slots=True)
class EffectivePermission:
    execution_policy: AgentExecutionPolicy
    data_policy: AgentDataPolicy
    allowed_tools: frozenset[str]
    skill_key: str | None
    deny_read_content: bool
    high_risk_confirmed: bool


class PermissionResolver:
    async def effective(
        self,
        *,
        request: PlanAgentRequest,
        setting: AgentUserSetting | None,
        skill: Any,
        high_risk_confirmed: bool,
    ) -> EffectivePermission:
        execution_policy = request.execution_policy
        data_policy = _merge_data_policy(request.data_policy, setting)
        skill_whitelist = _skill_tool_whitelist(skill)
        allowed_tools = frozenset(skill_whitelist)
        skill_key = _skill_key(skill)
        deny_read_content = (
            not data_policy.allow_file_content
            or not data_policy.allowed_mime_types
        )
        return EffectivePermission(
            execution_policy=execution_policy,
            data_policy=data_policy,
            allowed_tools=allowed_tools,
            skill_key=skill_key,
            deny_read_content=deny_read_content,
            high_risk_confirmed=high_risk_confirmed,
        )


def _merge_data_policy(
    request_policy: AgentDataPolicy, setting: AgentUserSetting | None
) -> AgentDataPolicy:
    if setting is None:
        return request_policy
    setting_policy = _setting_data_policy(setting)
    allow = request_policy.allow_file_content and setting_policy.allow_file_content
    max_bytes = min(request_policy.max_read_bytes, setting_policy.max_read_bytes)
    allowed_mimes = _intersect_mime_globs(
        request_policy.allowed_mime_types, setting_policy.allowed_mime_types
    )
    return AgentDataPolicy(
        allow_file_content=allow,
        max_read_bytes=max_bytes,
        allowed_mime_types=allowed_mimes,
    )


def _setting_data_policy(setting: AgentUserSetting) -> AgentDataPolicy:
    raw = setting.default_data_policy_json or {}
    if not isinstance(raw, dict):
        raw = {}
    return AgentDataPolicy.model_validate(raw)


def _intersect_mime_globs(a: list[str], b: list[str]) -> list[str]:
    # ["*/*"] means "all"; intersection with X = X.
    if "*/*" in a and "*/*" in b:
        return ["*/*"]
    if "*/*" in a:
        return list(b)
    if "*/*" in b:
        return list(a)
    return [m for m in a if m in b]


def _skill_tool_whitelist(skill: Any) -> tuple[str, ...]:
    if skill is None:
        return REGISTRY.all_names()
    raw = getattr(skill, "tool_whitelist_json", None)
    if isinstance(raw, list) and raw:
        tools = tuple(str(item) for item in raw if str(item).strip())
        unknown = REGISTRY.unknown_names(tools)
        if unknown:
            from ...core.errors import ApiError
            raise ApiError(
                status_code=422,
                code=422,
                message="Unknown agent tool in selected skill",
                data={"unknownTools": sorted(unknown)},
            )
        return tools
    return REGISTRY.all_names()


def _skill_key(skill: Any) -> str | None:
    if skill is None:
        return None
    return str(getattr(skill, "skill_key", None) or "")


__all__ = ["EffectivePermission", "PermissionResolver"]
