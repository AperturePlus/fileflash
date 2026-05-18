from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]


class ToolRouter:
    async def dispatch(self, call: ToolCall) -> dict[str, Any]:
        raise NotImplementedError("ToolRouter is scaffolded only in this stage")
