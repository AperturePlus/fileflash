from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PromptBuildRequest:
    task_input: str
    system_prompt: str
    memory_items: list[dict[str, Any]] = field(default_factory=list)
    tool_schemas: list[dict[str, Any]] = field(default_factory=list)


class PromptBuilder:
    async def build(self, request: PromptBuildRequest) -> list[dict[str, Any]]:
        raise NotImplementedError("PromptBuilder is scaffolded only in this stage")
