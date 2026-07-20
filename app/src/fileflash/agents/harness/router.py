from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.settings import Settings, get_settings
from ...s3.minio_client import MinioObjectStorageClient
from ...services.file import FileService
from ...services.folder import FolderService
from .tool_registry import REGISTRY, ToolContext


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]


class ToolRouter:
    def __init__(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        settings: Settings | None = None,
        storage_reader: MinioObjectStorageClient | None = None,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.settings = settings or get_settings()
        self.file_service = FileService(db=db)
        self.folder_service = FolderService(db=db)
        self._storage_reader = storage_reader

    def _resolve_storage_reader(self) -> MinioObjectStorageClient | None:
        if self._storage_reader is not None:
            return self._storage_reader
        try:
            return MinioObjectStorageClient.from_settings(self.settings)
        except Exception:
            return None

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
            storage_reader=self._resolve_storage_reader(),
        )
        return await spec.handler(ctx, dict(call.arguments or {}))


__all__ = ["ToolCall", "ToolRouter"]
