from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

ToolSideEffect = Literal["read", "write"]
ToolRiskLevel = Literal["low", "medium", "high"]


@dataclass(slots=True)
class ToolContext:
    db: AsyncSession
    user_id: int
    file_service: Any
    folder_service: Any


ToolHandler = Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]
ToolAnswerFormatter = Callable[[dict[str, Any]], str | None]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    side_effect: ToolSideEffect
    risk_level: ToolRiskLevel
    requires_confirmation: bool
    handler: ToolHandler
    anthropic_name: str | None = None
    answer_formatter: ToolAnswerFormatter | None = None

    def __post_init__(self) -> None:
        if self.anthropic_name is None:
            object.__setattr__(self, "anthropic_name", _to_provider_tool_name(self.name))

    def to_anthropic_tool(self) -> dict[str, Any]:
        return {
            "name": self.anthropic_name,
            "description": self.description,
            "input_schema": self.input_schema,
            "internalName": self.name,
        }

    def to_planner_schema(self) -> dict[str, Any]:
        return {
            "tool": self.name,
            "providerTool": self.anthropic_name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "sideEffect": self.side_effect,
            "riskLevel": self.risk_level,
            "requiresConfirmation": self.requires_confirmation,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._by_name: dict[str, ToolSpec] = {}
        self._by_provider_name: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._by_name:
            raise ValueError(f"Agent tool already registered: {spec.name}")
        provider_name = str(spec.anthropic_name or "")
        if provider_name in self._by_provider_name:
            raise ValueError(f"Agent provider tool already registered: {provider_name}")
        self._by_name[spec.name] = spec
        self._by_provider_name[provider_name] = spec
        return spec

    def get(self, name: str) -> ToolSpec:
        ensure_builtin_tools_registered()
        return self._by_name[name]

    def get_by_provider_name(self, name: str) -> ToolSpec:
        ensure_builtin_tools_registered()
        return self._by_provider_name[name]

    def all(self) -> list[ToolSpec]:
        ensure_builtin_tools_registered()
        return list(self._by_name.values())

    def all_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.all())

    def unknown_names(self, names: list[str] | tuple[str, ...]) -> list[str]:
        ensure_builtin_tools_registered()
        return [name for name in names if name not in self._by_name]

    def validate_names(self, names: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        unknown = self.unknown_names(names)
        if unknown:
            raise ValueError(f"Unknown agent tools: {', '.join(sorted(unknown))}")
        return tuple(names)

    def schemas_for(self, names: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
        return [self.get(name).to_planner_schema() for name in names]

    def anthropic_tools_for(self, names: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
        return [self.get(name).to_anthropic_tool() for name in names]


REGISTRY = ToolRegistry()
_BUILTINS_REGISTERED = False


def ensure_builtin_tools_registered() -> None:
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    from .. import tools as _tools  # noqa: F401
    _BUILTINS_REGISTERED = True


def _to_provider_tool_name(name: str) -> str:
    value = name.replace(".", "_").replace("-", "_")
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")
    return value or "tool"


__all__ = [
    "REGISTRY",
    "ToolAnswerFormatter",
    "ToolContext",
    "ToolHandler",
    "ToolRegistry",
    "ToolRiskLevel",
    "ToolSideEffect",
    "ToolSpec",
    "ensure_builtin_tools_registered",
]
