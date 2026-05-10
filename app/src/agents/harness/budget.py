from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContextBudget:
    max_tokens: int
    max_steps: int


class ContextBudgeter:
    async def apply(self, *args, **kwargs) -> ContextBudget:
        raise NotImplementedError("ContextBudgeter is scaffolded only in this stage")
