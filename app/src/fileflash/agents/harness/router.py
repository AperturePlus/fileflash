from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...services.file import FileService
from ...services.folder import FolderService
from .tool_registry import REGISTRY, ToolContext


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]


class ToolRouter:
    def __init__(self, *, db: AsyncSession, user_id: int) -> None:
        self.db = db
        self.user_id = user_id
        self.file_service = FileService(db=db)
        self.folder_service = FolderService(db=db)

    async def dispatch(self, call: ToolCall) -> dict[str, Any]:
        tool_name = str(call.tool_name or "").strip()
        try:
            spec = REGISTRY.get(tool_name)
        except KeyError as exc:
            raise ApiError(
                status_code=400,
                code=400,
                message=f"Unsupported agent tool: {tool_name}",
            ) from exc

        ctx = ToolContext(
            db=self.db,
            user_id=self.user_id,
            file_service=self.file_service,
            folder_service=self.folder_service,
        )
        return await spec.handler(ctx, dict(call.arguments or {}))


__all__ = ["ToolCall", "ToolRouter"]
