from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CostSnapshot:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: int = 0


class CostTracker:
    async def snapshot(self) -> CostSnapshot:
        raise NotImplementedError("CostTracker is scaffolded only in this stage")
