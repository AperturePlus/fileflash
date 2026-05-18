from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


class PolicyGuard:
    def __init__(
        self,
        *,
        allow_writes: bool = False,
        data_policy: dict[str, Any] | None = None,
        execution_policy: str = "confirm",
    ) -> None:
        self.allow_writes = allow_writes
        self.data_policy = data_policy or {}
        self.execution_policy = execution_policy

    def evaluate_tool_call(self, tool: str, side_effect: str) -> PolicyDecision:  # noqa: ARG002
        if side_effect == "write":
            if self.execution_policy == "planOnly":
                return PolicyDecision(allowed=False, reasons=["executionPolicy is planOnly"])
            if not self.allow_writes:
                return PolicyDecision(
                    allowed=False,
                    reasons=["Write tools disabled (set AGENT_ALLOW_WRITE_TOOLS=true to enable)"],
                )
            if not self.data_policy.get("allowFileContent", self.data_policy.get("allow_file_content", True)):
                return PolicyDecision(allowed=False, reasons=["dataPolicy disallows write operations"])
        return PolicyDecision(allowed=True)
