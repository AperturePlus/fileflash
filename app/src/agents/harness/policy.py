from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


class PolicyGuard:
    async def evaluate_tool_call(self, *args, **kwargs) -> PolicyDecision:
        raise NotImplementedError("PolicyGuard is scaffolded only in this stage")
