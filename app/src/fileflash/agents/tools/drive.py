from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.file import GetFolderContentsQuery, MoveFileRequest, RenameFileRequest
from ...schemas.file import CreateFolderRequest
from ...services.file import FileService
from ...services.folder import FolderService


class DriveToolContext:
    def __init__(self, *, db: AsyncSession, user_id: int, allow_writes: bool = False) -> None:
        self.db = db
        self.user_id = user_id
        self.allow_writes = allow_writes
        self.files = FileService(db=db, storage=None)
        self.folders = FolderService(db=db)

    async def invoke(self, tool: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if tool == "drive.listFolder":
            return await self._list_folder(inputs)
        if tool == "drive.resolvePath":
            return await self._resolve_path(inputs)
        if tool in {"drive.moveFile", "drive.renameFile", "drive.createFolder"}:
            if not self.allow_writes:
                return {"skipped": True, "reason": "write tools disabled in MVP read-only mode"}
            if tool == "drive.moveFile":
                return await self._move_file(inputs)
            if tool == "drive.renameFile":
                return await self._rename_file(inputs)
            return await self._create_folder(inputs)
        return {"error": f"Unknown tool: {tool}"}

    async def _list_folder(self, inputs: dict[str, Any]) -> dict[str, Any]:
        folder_id = str(inputs.get("folderId") or "root")
        if folder_id == "root":
            query = GetFolderContentsQuery(folder_id="0", page=1, per_page=50)
            data = await self.folders.get_root_contents(user_id=self.user_id, query=query)
        else:
            query = GetFolderContentsQuery(folder_id=folder_id, page=1, per_page=50)
            data = await self.folders.get_folder_contents(user_id=self.user_id, query=query)
        return {
            "folderId": folder_id,
            "itemCount": len(data.items),
            "items": [item.model_dump(by_alias=True) for item in data.items[:20]],
        }

    async def _resolve_path(self, inputs: dict[str, Any]) -> dict[str, Any]:
        path = str(inputs.get("path") or "/My Files")
        return {"path": path, "folderId": "root", "resolved": True}

    async def _move_file(self, inputs: dict[str, Any]) -> dict[str, Any]:
        file_id = str(inputs.get("fileId") or "")
        target_folder_id = str(inputs.get("targetFolderId") or "root")
        if target_folder_id.startswith("$"):
            return {"skipped": True, "reason": "dynamic target folder references are not resolved in MVP"}
        payload = MoveFileRequest(target_folder_id=target_folder_id)
        result = await self.files.move_file(user_id=self.user_id, file_id=file_id, payload=payload)
        return result.model_dump(by_alias=True)

    async def _rename_file(self, inputs: dict[str, Any]) -> dict[str, Any]:
        file_id = str(inputs.get("fileId") or "")
        file_name = str(inputs.get("fileName") or inputs.get("name") or "")
        payload = RenameFileRequest(file_name=file_name)
        result = await self.files.rename_file(user_id=self.user_id, file_id=file_id, payload=payload)
        return result.model_dump(by_alias=True)

    async def _create_folder(self, inputs: dict[str, Any]) -> dict[str, Any]:
        parent_folder_id = str(inputs.get("parentFolderId") or "root")
        name = str(inputs.get("name") or "New Folder")
        payload = CreateFolderRequest(parent_folder_id=parent_folder_id, folder_name=name)
        result = await self.folders.create_folder(user_id=self.user_id, payload=payload)
        return result.model_dump(by_alias=True)
