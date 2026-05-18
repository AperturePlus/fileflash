from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..tools.drive import DriveToolContext


@dataclass(slots=True)
class ToolCall:
    tool: str
    inputs: dict[str, Any]


class ToolRouter:
    def __init__(self, *, drive: DriveToolContext) -> None:
        self._drive = drive

    async def execute(self, call: ToolCall) -> dict[str, Any]:
        return await self._drive.invoke(call.tool, call.inputs)
