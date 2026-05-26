from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.mime import resolve_file_mime_type
from ...models import File, Folder
from ...models.enums import FileStatus, FolderStatus, FolderType
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

        if tool == "drive.countFiles":
            return await self._count_files(args)

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

    async def _count_files(self, args: dict[str, Any]) -> dict[str, Any]:
        folder_id = str(_first_value(args, "folderId", "parentFolderId") or "root")
        recursive = _bool_arg(args.get("recursive"), default=True)
        category = _normalize_category(args.get("category"))
        search = str(args.get("search") or "").strip()
        root_folder_id = await _resolve_folder_id(
            self.db,
            user_id=self.user_id,
            folder_id=folder_id,
        )
        folder_ids = (
            await _active_descendant_folder_ids(
                self.db,
                user_id=self.user_id,
                root_folder_id=root_folder_id,
            )
            if recursive
            else [root_folder_id]
        )

        statement = select(
            File.file_id,
            File.file_name,
            File.file_size,
            File.mime_type,
            File.file_ext,
            File.folder_id,
        ).where(
            and_(
                File.owner_id == self.user_id,
                File.folder_id.in_(folder_ids),
                File.status == FileStatus.ACTIVE,
                File.is_latest.is_(True),
            )
        )
        if search:
            statement = statement.where(File.file_name.ilike(f"%{search}%"))
        statement = statement.order_by(File.file_name.asc())

        rows = (await self.db.execute(statement)).all()
        by_mime_type: dict[str, int] = {}
        sample_items: list[dict[str, Any]] = []
        total_items = 0
        for row in rows:
            file_id, file_name, file_size, mime_type, file_ext, row_folder_id = row
            resolved_mime = resolve_file_mime_type(
                mime_type=mime_type,
                file_ext=file_ext,
                file_name=file_name,
            )
            if category is not None and _category_for_file(
                mime_type=resolved_mime,
                file_ext=file_ext,
                file_name=file_name,
            ) != category:
                continue

            total_items += 1
            by_mime_type[resolved_mime] = by_mime_type.get(resolved_mime, 0) + 1
            if len(sample_items) < 5:
                sample_items.append(
                    {
                        "id": str(file_id),
                        "name": str(file_name),
                        "size": int(file_size or 0),
                        "mimeType": resolved_mime,
                        "folderId": str(row_folder_id),
                    }
                )

        return {
            "totalItems": total_items,
            "category": category,
            "recursive": recursive,
            "folderId": str(root_folder_id),
            "search": search or None,
            "byMimeType": dict(sorted(by_mime_type.items())),
            "sampleItems": sample_items,
        }


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


def _bool_arg(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return default


async def _resolve_folder_id(db: AsyncSession, *, user_id: int, folder_id: str) -> int:
    if not folder_id or folder_id == "root":
        root_id = await db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_type == FolderType.ROOT,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if root_id is None:
            raise ApiError(status_code=404, code=404, message="Root folder not found")
        return int(root_id)
    try:
        parsed = int(folder_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid folderId") from exc
    exists = await db.scalar(
        select(Folder.folder_id).where(
            and_(
                Folder.folder_id == parsed,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
    )
    if exists is None:
        raise ApiError(status_code=404, code=404, message="Folder not found")
    return parsed


async def _active_descendant_folder_ids(
    db: AsyncSession,
    *,
    user_id: int,
    root_folder_id: int,
) -> list[int]:
    descendants = (
        select(Folder.folder_id)
        .where(
            and_(
                Folder.folder_id == root_folder_id,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
        .cte(name="agent_count_descendants", recursive=True)
    )
    descendants = descendants.union_all(
        select(Folder.folder_id).where(
            and_(
                Folder.parent_folder_id == descendants.c.folder_id,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
    )
    folder_ids = list(await db.scalars(select(descendants.c.folder_id)))
    return [int(folder_id) for folder_id in folder_ids]


def _normalize_category(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    aliases = {
        "movies": "video",
        "movie": "video",
        "film": "video",
        "films": "video",
        "视频": "video",
        "影片": "video",
        "电影": "video",
        "videos": "video",
        "documents": "document",
        "docs": "document",
        "images": "image",
        "pictures": "image",
        "archives": "archive",
        "compressed": "archive",
    }
    text = aliases.get(text, text)
    if text in {"video", "audio", "image", "document", "archive", "other"}:
        return text
    return None


def _category_for_file(*, mime_type: str, file_ext: str | None, file_name: str | None) -> str:
    mime = (mime_type or "").lower()
    ext = _normalized_extension(file_ext) or _filename_extension(file_name)
    if mime.startswith("video/") or ext in {"mp4", "mov", "avi", "mkv", "webm", "m4v"}:
        return "video"
    if mime.startswith("audio/") or ext in {"mp3", "wav", "flac", "m4a", "aac", "ogg"}:
        return "audio"
    if mime.startswith("image/") or ext in {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"}:
        return "image"
    if mime in {"application/pdf"} or ext in {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md"}:
        return "document"
    if ext in {"zip", "rar", "7z", "tar", "gz", "bz2", "xz"}:
        return "archive"
    return "other"


def _normalized_extension(value: str | None) -> str:
    return str(value or "").strip().lower().lstrip(".")


def _filename_extension(value: str | None) -> str:
    name = str(value or "").strip().lower()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1]
