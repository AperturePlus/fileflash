from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...schemas.file import (
    CreateFolderRequest,
    GetFolderContentsQuery,
    MoveFileRequest,
    MoveFolderRequest,
    RenameFileRequest,
    RenameFolderRequest,
)
from ...services.file import FileService
from ...services.folder import FolderService


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
        tool = call.tool_name
        args = dict(call.arguments or {})

        if tool == "drive.listFolder":
            folder_id = _first_value(args, "folderId", "parentFolderId") or "root"
            query = GetFolderContentsQuery(
                folder_id=str(folder_id),
                page=int(args.get("page") or 1),
                per_page=min(200, int(args.get("perPage") or 200)),
            )
            if str(folder_id) == "root":
                result = await self.folder_service.get_root_contents(
                    user_id=self.user_id,
                    query=query,
                )
            else:
                result = await self.folder_service.get_folder_contents(
                    user_id=self.user_id,
                    query=query,
                )
            return result.model_dump(by_alias=True, mode="json")

        if tool == "drive.createFolder":
            name = _required_text(args, "name", "folderName")
            parent_id = _first_value(args, "parentFolderId", "targetParentId", "folderId") or "root"
            result = await self.folder_service.create_folder(
                user_id=self.user_id,
                payload=CreateFolderRequest(folder_name=name, parent_folder_id=str(parent_id)),
            )
            data = result.model_dump(by_alias=True, mode="json")
            data.setdefault("folderId", data.get("id"))
            return data

        if tool == "drive.moveFile":
            file_id = _required_text(args, "fileId", "id")
            target_folder_id = _required_text(args, "targetFolderId", "targetParentId")
            result = await self.file_service.move_file(
                user_id=self.user_id,
                file_id=file_id,
                payload=MoveFileRequest(
                    target_folder_id=target_folder_id,
                    share_handling=str(args.get("shareHandling") or "keep"),
                ),
            )
            return result.model_dump(by_alias=True, mode="json")

        if tool == "drive.moveFolder":
            folder_id = _required_text(args, "folderId", "id")
            target_parent_id = _required_text(args, "targetParentId", "targetFolderId")
            result = await self.folder_service.move_folder(
                user_id=self.user_id,
                folder_id=folder_id,
                payload=MoveFolderRequest(
                    target_parent_id=target_parent_id,
                    share_handling=str(args.get("shareHandling") or "keep"),
                ),
            )
            return result.model_dump(by_alias=True, mode="json")

        if tool == "drive.renameFile":
            file_id = _required_text(args, "fileId", "id")
            file_name = _required_text(args, "fileName", "name")
            result = await self.file_service.rename_file(
                user_id=self.user_id,
                file_id=file_id,
                payload=RenameFileRequest(file_name=file_name),
            )
            return result.model_dump(by_alias=True, mode="json")

        if tool == "drive.renameFolder":
            folder_id = _required_text(args, "folderId", "id")
            folder_name = _required_text(args, "folderName", "name")
            result = await self.folder_service.rename_folder(
                user_id=self.user_id,
                folder_id=folder_id,
                payload=RenameFolderRequest(folder_name=folder_name),
            )
            return result.model_dump(by_alias=True, mode="json")

        if tool == "drive.deleteFile":
            file_id = _required_text(args, "fileId", "id")
            result = await self.file_service.delete_file(user_id=self.user_id, file_id=file_id)
            return result.model_dump(by_alias=True, mode="json")

        if tool == "drive.deleteFolder":
            folder_id = _required_text(args, "folderId", "id")
            result = await self.folder_service.delete_folder(
                user_id=self.user_id,
                folder_id=folder_id,
            )
            return result.model_dump(by_alias=True, mode="json")

        raise ApiError(status_code=400, code=400, message=f"Unsupported agent tool: {tool}")


def _first_value(args: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = args.get(key)
        if value not in (None, ""):
            return value
    return None


def _required_text(args: dict[str, Any], *keys: str) -> str:
    value = _first_value(args, *keys)
    if value is None:
        raise ApiError(status_code=400, code=400, message=f"Missing required tool input: {keys[0]}")
    text = str(value).strip()
    if not text:
        raise ApiError(status_code=400, code=400, message=f"Missing required tool input: {keys[0]}")
    return text
