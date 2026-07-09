from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select

from ...core.errors import ApiError
from ...core.mime import resolve_file_mime_type
from ...models import File, Folder
from ...models.enums import FileStatus, FolderStatus, FolderType
from ...models.tables_storage import StorageObject
from ...schemas.file import (
    CreateFolderRequest,
    GetFolderContentsQuery,
    MoveFileRequest,
    MoveFolderRequest,
    RenameFileRequest,
    RenameFolderRequest,
)
from ..harness.tool_registry import REGISTRY, ToolContext, ToolSpec

_CATEGORIES = ("video", "audio", "image", "document", "archive", "other")
_COUNT_FILE_NAME_LIMIT = 12


async def _list_folder(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = _first_value(args, "folderId", "parentFolderId") or "root"
    query = GetFolderContentsQuery(
        folder_id=str(folder_id),
        page=_int_arg(args.get("page"), default=1, minimum=1),
        per_page=_int_arg(args.get("perPage"), default=200, minimum=1, maximum=200),
        search=_optional_text(args.get("search")),
    )
    if str(folder_id) == "root":
        result = await ctx.folder_service.get_root_contents(user_id=ctx.user_id, query=query)
    else:
        result = await ctx.folder_service.get_folder_contents(user_id=ctx.user_id, query=query)
    return result.model_dump(by_alias=True, mode="json")


async def _count_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = str(_first_value(args, "folderId", "parentFolderId") or "root")
    recursive = _bool_arg(args.get("recursive"), default=True)
    category = _normalize_category(args.get("category"))
    search = str(args.get("search") or "").strip()
    root_folder_id = await _resolve_folder_id(ctx, folder_id=folder_id)
    folder_ids = await _folder_scope_ids(ctx, root_folder_id=root_folder_id, recursive=recursive)

    statement = _active_files_query(ctx, folder_ids=folder_ids)
    if search:
        statement = statement.where(File.file_name.ilike(f"%{search}%"))
    statement = statement.order_by(File.file_name.asc())

    rows = list(await ctx.db.scalars(statement))
    by_mime_type: dict[str, int] = {}
    sample_items: list[dict[str, Any]] = []
    item_names: list[str] = []
    names_truncated = False
    total_items = 0
    for row in rows:
        resolved_mime = _resolved_mime(row)
        if category is not None and _category_for_file(row) != category:
            continue

        total_items += 1
        by_mime_type[resolved_mime] = by_mime_type.get(resolved_mime, 0) + 1
        file_name = str(row.file_name or "").strip()
        if file_name:
            if len(item_names) < _COUNT_FILE_NAME_LIMIT:
                item_names.append(file_name)
            else:
                names_truncated = True
        if len(sample_items) < 5:
            sample_items.append(await _file_payload(ctx, row, include_path=False))

    return {
        "totalItems": total_items,
        "category": category,
        "recursive": recursive,
        "folderId": str(root_folder_id),
        "search": search or None,
        "byMimeType": dict(sorted(by_mime_type.items())),
        "itemNames": item_names,
        "itemNamesTruncated": names_truncated,
        "sampleItems": sample_items,
    }


async def _create_folder(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    name = _required_text(args, "name", "folderName")
    parent_id = _first_value(args, "parentFolderId", "targetParentId", "folderId") or "root"
    result = await ctx.folder_service.create_folder(
        user_id=ctx.user_id,
        payload=CreateFolderRequest(folder_name=name, parent_folder_id=str(parent_id)),
    )
    data = result.model_dump(by_alias=True, mode="json")
    data.setdefault("folderId", data.get("id"))
    return data


async def _move_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    file_id = _required_text(args, "fileId", "id")
    target_folder_id = _required_text(args, "targetFolderId", "targetParentId")
    result = await ctx.file_service.move_file(
        user_id=ctx.user_id,
        file_id=file_id,
        payload=MoveFileRequest(
            target_folder_id=target_folder_id,
            share_handling=str(args.get("shareHandling") or "keep"),
        ),
    )
    return result.model_dump(by_alias=True, mode="json")


async def _move_folder(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = _required_text(args, "folderId", "id")
    target_parent_id = _required_text(args, "targetParentId", "targetFolderId")
    result = await ctx.folder_service.move_folder(
        user_id=ctx.user_id,
        folder_id=folder_id,
        payload=MoveFolderRequest(
            target_parent_id=target_parent_id,
            share_handling=str(args.get("shareHandling") or "keep"),
        ),
    )
    return result.model_dump(by_alias=True, mode="json")


async def _rename_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    file_id = _required_text(args, "fileId", "id")
    file_name = _required_text(args, "fileName", "name")
    result = await ctx.file_service.rename_file(
        user_id=ctx.user_id,
        file_id=file_id,
        payload=RenameFileRequest(file_name=file_name),
    )
    return result.model_dump(by_alias=True, mode="json")


async def _rename_folder(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = _required_text(args, "folderId", "id")
    folder_name = _required_text(args, "folderName", "name")
    result = await ctx.folder_service.rename_folder(
        user_id=ctx.user_id,
        folder_id=folder_id,
        payload=RenameFolderRequest(folder_name=folder_name),
    )
    return result.model_dump(by_alias=True, mode="json")


async def _delete_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    file_id = _required_text(args, "fileId", "id")
    result = await ctx.file_service.delete_file(user_id=ctx.user_id, file_id=file_id)
    return result.model_dump(by_alias=True, mode="json")


async def _delete_folder(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = _required_text(args, "folderId", "id")
    result = await ctx.folder_service.delete_folder(user_id=ctx.user_id, folder_id=folder_id)
    return result.model_dump(by_alias=True, mode="json")


async def _search_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    query = _optional_text(args.get("query")) or _optional_text(args.get("search")) or ""
    folder_id = str(args.get("folderId") or "root")
    recursive = _bool_arg(args.get("recursive"), default=True)
    category = _normalize_category(args.get("category"))
    mime_prefix = _optional_text(args.get("mimePrefix"))
    modified_after = _parse_datetime_arg(args.get("modifiedAfter"))
    limit = _int_arg(args.get("limit"), default=50, minimum=1, maximum=200)

    root_folder_id = await _resolve_folder_id(ctx, folder_id=folder_id)
    folder_ids = await _folder_scope_ids(ctx, root_folder_id=root_folder_id, recursive=recursive)
    statement = _active_files_query(ctx, folder_ids=folder_ids)
    if query:
        statement = statement.where(File.file_name.ilike(f"%{query}%"))
    if modified_after is not None:
        statement = statement.where(File.updated_at >= modified_after)
    statement = statement.order_by(File.file_name.asc())

    items: list[dict[str, Any]] = []
    for row in list(await ctx.db.scalars(statement)):
        mime_type = _resolved_mime(row)
        if mime_prefix and not mime_type.lower().startswith(mime_prefix.lower()):
            continue
        if category is not None and _category_for_file(row) != category:
            continue
        items.append(await _file_payload(ctx, row, include_path=True))
        if len(items) >= limit:
            break

    return {
        "items": items,
        "totalItems": len(items),
        "query": query or None,
        "folderId": str(root_folder_id),
        "recursive": recursive,
        "category": category,
        "mimePrefix": mime_prefix,
        "modifiedAfter": modified_after.isoformat() if modified_after else None,
    }


async def _get_file_info(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    file_id = _parse_positive_int(_required_text(args, "fileId", "id"), "fileId")
    row = await ctx.db.scalar(
        select(File).where(
            and_(
                File.file_id == file_id,
                File.owner_id == ctx.user_id,
                File.status == FileStatus.ACTIVE,
                File.is_latest.is_(True),
            )
        )
    )
    if row is None:
        raise ApiError(status_code=404, code=404, message="File not found")
    storage = await ctx.db.get(StorageObject, int(row.storage_object_id))
    payload = await _file_payload(ctx, row, include_path=True)
    payload.update(
        {
            "objectHash": str(storage.object_hash) if storage and storage.object_hash else None,
            "hashAlgorithm": str(storage.hash_algorithm) if storage else None,
            "storageObjectId": str(row.storage_object_id),
            "category": _category_for_file(row),
        }
    )
    return payload


async def _list_recent(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    limit = _int_arg(args.get("limit"), default=20, minimum=1, maximum=50)
    since = _parse_datetime_arg(args.get("since"))
    statement = _active_files_query(ctx, folder_ids=None)
    if since is not None:
        statement = statement.where(File.updated_at >= since)
    statement = statement.order_by(File.updated_at.desc(), File.file_id.desc()).limit(limit)
    rows = list(await ctx.db.scalars(statement))
    return {
        "items": [await _file_payload(ctx, row, include_path=True) for row in rows],
        "totalItems": len(rows),
        "limit": limit,
        "since": since.isoformat() if since else None,
    }


async def _stats_by_category(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = str(args.get("folderId") or "root")
    recursive = _bool_arg(args.get("recursive"), default=True)
    root_folder_id = await _resolve_folder_id(ctx, folder_id=folder_id)
    folder_ids = await _folder_scope_ids(ctx, root_folder_id=root_folder_id, recursive=recursive)
    rows = list(await ctx.db.scalars(_active_files_query(ctx, folder_ids=folder_ids)))

    categories = {
        category: {"count": 0, "totalSize": 0}
        for category in _CATEGORIES
    }
    total_size = 0
    for row in rows:
        category = _category_for_file(row)
        size = int(row.file_size or 0)
        categories[category]["count"] += 1
        categories[category]["totalSize"] += size
        total_size += size

    return {
        "folderId": str(root_folder_id),
        "recursive": recursive,
        "totalItems": len(rows),
        "totalSize": total_size,
        "categories": categories,
        "video": categories["video"]["count"],
        "audio": categories["audio"]["count"],
        "image": categories["image"]["count"],
        "document": categories["document"]["count"],
        "archive": categories["archive"]["count"],
        "other": categories["other"]["count"],
    }


async def _find_duplicates(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    folder_id = str(args.get("folderId") or "root")
    recursive = _bool_arg(args.get("recursive"), default=True)
    by = str(args.get("by") or "hash").strip() or "hash"
    if by not in {"hash", "nameSize"}:
        raise ApiError(status_code=400, code=400, message="Invalid duplicate mode")

    root_folder_id = await _resolve_folder_id(ctx, folder_id=folder_id)
    folder_ids = await _folder_scope_ids(ctx, root_folder_id=root_folder_id, recursive=recursive)
    rows = (
        await ctx.db.execute(
            _active_files_query(ctx, folder_ids=folder_ids)
            .join(StorageObject, StorageObject.object_id == File.storage_object_id)
            .add_columns(StorageObject.object_hash, StorageObject.hash_algorithm)
            .order_by(File.file_name.asc())
        )
    ).all()

    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        file_row: File = row[0]
        object_hash = row[1]
        hash_algorithm = row[2]
        if by == "hash":
            if not object_hash:
                continue
            key = f"{hash_algorithm}:{object_hash}:{int(file_row.file_size or 0)}"
        else:
            key = f"{file_row.file_name.lower()}:{int(file_row.file_size or 0)}"
        group = groups.setdefault(
            key,
            {
                "key": key,
                "by": by,
                "hash": str(object_hash) if object_hash else None,
                "hashAlgorithm": str(hash_algorithm) if hash_algorithm else None,
                "size": int(file_row.file_size or 0),
                "files": [],
            },
        )
        group["files"].append(await _file_payload(ctx, file_row, include_path=True))

    duplicate_groups = [group for group in groups.values() if len(group["files"]) > 1]
    return {
        "folderId": str(root_folder_id),
        "recursive": recursive,
        "by": by,
        "groups": duplicate_groups,
        "totalGroups": len(duplicate_groups),
        "totalFiles": sum(len(group["files"]) for group in duplicate_groups),
    }


_TEXT_MIME_ALLOWLIST = (
    "text/",
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/javascript",
    "application/x-sh",
    "application/pdf",
)


async def _read_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    file_id = _parse_positive_int(_required_text(args, "fileId", "id"), "fileId")
    max_bytes = _int_arg(args.get("maxBytes"), default=262144, minimum=1, maximum=1_048_576)
    offset = _int_arg(args.get("offset"), default=0, minimum=0)

    row = await ctx.db.scalar(
        select(File).where(
            and_(
                File.file_id == file_id,
                File.owner_id == ctx.user_id,
                File.status == FileStatus.ACTIVE,
                File.is_latest.is_(True),
            )
        )
    )
    if row is None:
        raise ApiError(status_code=404, code=404, message="File not found")

    storage = await ctx.db.scalar(
        select(StorageObject).where(StorageObject.object_id == row.storage_object_id)
    )
    if storage is None or ctx.storage_reader is None:
        raise ApiError(status_code=503, code=503, message="Object storage unavailable")

    mime = _resolved_mime(row)
    object_key = str(storage.object_key)
    stat = await ctx.storage_reader.stat_object(object_key=object_key)
    size = int(stat.size)

    if not mime.lower().startswith(_TEXT_MIME_ALLOWLIST):
        return {
            "fileId": str(file_id),
            "name": str(row.file_name),
            "mime": mime,
            "size": size,
            "truncated": True,
            "bytesReturned": 0,
            "note": "Binary content not sent to model.",
        }

    end = min(offset + max_bytes - 1, size - 1) if size > 0 else 0
    chunks: list[bytes] = []
    received = 0
    async for chunk in ctx.storage_reader.iter_object_range(
        object_key=object_key, start=offset, end=end
    ):
        chunks.append(chunk)
        received += len(chunk)
    content_bytes = b"".join(chunks)
    try:
        content = content_bytes.decode("utf-8", errors="replace")
    except Exception:
        content = content_bytes.decode("latin-1", errors="replace")

    return {
        "fileId": str(file_id),
        "name": str(row.file_name),
        "mime": mime,
        "size": size,
        "content": content,
        "truncated": (offset + received) < size,
        "bytesReturned": received,
        "offset": offset,
    }


def _active_files_query(ctx: ToolContext, *, folder_ids: list[int] | None):
    statement = select(File).where(
        and_(
            File.owner_id == ctx.user_id,
            File.status == FileStatus.ACTIVE,
            File.is_latest.is_(True),
        )
    )
    if folder_ids is not None:
        statement = statement.where(File.folder_id.in_(folder_ids))
    return statement


async def _file_payload(
    ctx: ToolContext,
    row: File,
    *,
    include_path: bool,
) -> dict[str, Any]:
    payload = {
        "id": str(row.file_id),
        "fileId": str(row.file_id),
        "name": str(row.file_name),
        "size": int(row.file_size or 0),
        "mimeType": _resolved_mime(row),
        "folderId": str(row.folder_id),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_path:
        folder_path = await _folder_path(ctx, folder_id=int(row.folder_id))
        payload["path"] = f"{folder_path}/{row.file_name}" if folder_path else str(row.file_name)
    return payload


async def _resolve_folder_id(ctx: ToolContext, *, folder_id: str) -> int:
    if not folder_id or folder_id == "root":
        root_id = await ctx.db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.owner_id == ctx.user_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_type == FolderType.ROOT,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if root_id is None:
            raise ApiError(status_code=404, code=404, message="Root folder not found")
        return int(root_id)
    parsed = _parse_positive_int(folder_id, "folderId")
    exists = await ctx.db.scalar(
        select(Folder.folder_id).where(
            and_(
                Folder.folder_id == parsed,
                Folder.owner_id == ctx.user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
    )
    if exists is None:
        raise ApiError(status_code=404, code=404, message="Folder not found")
    return parsed


async def _folder_scope_ids(
    ctx: ToolContext,
    *,
    root_folder_id: int,
    recursive: bool,
) -> list[int]:
    if not recursive:
        return [root_folder_id]
    return await _active_descendant_folder_ids(ctx, root_folder_id=root_folder_id)


async def _active_descendant_folder_ids(ctx: ToolContext, *, root_folder_id: int) -> list[int]:
    descendants = (
        select(Folder.folder_id)
        .where(
            and_(
                Folder.folder_id == root_folder_id,
                Folder.owner_id == ctx.user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
        .cte(name="agent_tool_descendants", recursive=True)
    )
    descendants = descendants.union_all(
        select(Folder.folder_id).where(
            and_(
                Folder.parent_folder_id == descendants.c.folder_id,
                Folder.owner_id == ctx.user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
    )
    folder_ids = list(await ctx.db.scalars(select(descendants.c.folder_id)))
    return [int(folder_id) for folder_id in folder_ids]


async def _folder_path(ctx: ToolContext, *, folder_id: int) -> str:
    parts: list[str] = []
    current_id: int | None = folder_id
    while current_id is not None:
        folder = await ctx.db.scalar(
            select(Folder).where(
                and_(
                    Folder.folder_id == current_id,
                    Folder.owner_id == ctx.user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if folder is None:
            break
        parts.append(str(folder.folder_name))
        current_id = int(folder.parent_folder_id) if folder.parent_folder_id is not None else None
    parts.reverse()
    return "/" + "/".join(parts) if parts else ""


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


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


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


def _int_arg(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    try:
        parsed = int(value if value is not None else default)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _parse_positive_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}") from exc
    if parsed <= 0:
        raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}")
    return parsed


def _parse_datetime_arg(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid datetime") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _normalize_category(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    aliases = {
        "movies": "video",
        "movie": "video",
        "film": "video",
        "films": "video",
        "videos": "video",
        "anime": "video",
        "animation": "video",
        "视频": "video",
        "影片": "video",
        "电影": "video",
        "动漫": "video",
        "番剧": "video",
        "documents": "document",
        "docs": "document",
        "images": "image",
        "pictures": "image",
        "archives": "archive",
        "compressed": "archive",
    }
    text = aliases.get(text, text)
    if text in _CATEGORIES:
        return text
    return None


def _resolved_mime(row: File) -> str:
    return resolve_file_mime_type(
        mime_type=row.mime_type,
        file_ext=row.file_ext,
        file_name=row.file_name,
    )


def _category_for_file(row: File) -> str:
    mime = _resolved_mime(row).lower()
    ext = _normalized_extension(row.file_ext) or _filename_extension(row.file_name)
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


def _count_files_answer(output: dict[str, Any]) -> str:
    total_items = int(output.get("totalItems") or 0)
    category = str(output.get("category") or "").strip().lower()
    qualifier = _search_qualifier(output)
    if category == "video":
        return f"你上传了 {total_items} 部{qualifier}电影（按视频文件统计）。"
    if category == "audio":
        return f"你上传了 {total_items} 个{qualifier}音频文件。"
    if category == "image":
        return f"你上传了 {total_items} 张{qualifier}图片。"
    if category == "document":
        return f"你上传了 {total_items} 个{qualifier}文档。"
    if category == "archive":
        return f"你上传了 {total_items} 个{qualifier}压缩包。"
    return f"你上传了 {total_items} 个{qualifier}文件。"


def _search_qualifier(output: dict[str, Any]) -> str:
    search = str(output.get("search") or "").strip()
    if not search:
        return ""
    return f"名称包含“{search}”的"


def _normalized_extension(value: str | None) -> str:
    return str(value or "").strip().lower().lstrip(".")


def _filename_extension(value: str | None) -> str:
    name = str(value or "").strip().lower()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1]


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
    }


_FOLDER_ID = {"type": "string", "description": "Folder id, or root for the user's root folder."}
_FILE_ID = {"type": "string", "description": "File id owned by the current user."}
_CATEGORY = {"type": "string", "enum": list(_CATEGORIES)}
_SHARE_HANDLING = {"type": "string", "enum": ["keep", "revoke"], "default": "keep"}


REGISTRY.register(
    ToolSpec(
        name="drive.listFolder",
        description="List direct files and folders inside a folder.",
        input_schema=_schema(
            {
                "folderId": _FOLDER_ID,
                "page": {"type": "integer", "minimum": 1, "default": 1},
                "perPage": {"type": "integer", "minimum": 1, "maximum": 200, "default": 200},
                "search": {"type": "string"},
            }
        ),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_list_folder,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.countFiles",
        description=(
            "Count files under a folder. Supports recursive counts, broad file categories, "
            "and filename contains search."
        ),
        input_schema=_schema(
            {
                "folderId": _FOLDER_ID,
                "recursive": {"type": "boolean", "default": True},
                "category": _CATEGORY,
                "search": {"type": "string"},
            }
        ),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_count_files,
        answer_formatter=_count_files_answer,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.createFolder",
        description="Create a folder under parentFolderId with name.",
        input_schema=_schema(
            {
                "parentFolderId": _FOLDER_ID,
                "name": {"type": "string", "minLength": 1, "maxLength": 255},
            },
            required=["name"],
        ),
        side_effect="write",
        risk_level="medium",
        requires_confirmation=False,
        handler=_create_folder,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.moveFile",
        description="Move fileId into targetFolderId.",
        input_schema=_schema(
            {
                "fileId": _FILE_ID,
                "targetFolderId": _FOLDER_ID,
                "shareHandling": _SHARE_HANDLING,
            },
            required=["fileId", "targetFolderId"],
        ),
        side_effect="write",
        risk_level="medium",
        requires_confirmation=False,
        handler=_move_file,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.moveFolder",
        description="Move folderId into targetParentId.",
        input_schema=_schema(
            {
                "folderId": _FOLDER_ID,
                "targetParentId": _FOLDER_ID,
                "shareHandling": _SHARE_HANDLING,
            },
            required=["folderId", "targetParentId"],
        ),
        side_effect="write",
        risk_level="medium",
        requires_confirmation=False,
        handler=_move_folder,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.renameFile",
        description="Rename fileId to fileName.",
        input_schema=_schema(
            {
                "fileId": _FILE_ID,
                "fileName": {"type": "string", "minLength": 1, "maxLength": 255},
            },
            required=["fileId", "fileName"],
        ),
        side_effect="write",
        risk_level="medium",
        requires_confirmation=False,
        handler=_rename_file,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.renameFolder",
        description="Rename folderId to folderName.",
        input_schema=_schema(
            {
                "folderId": _FOLDER_ID,
                "folderName": {"type": "string", "minLength": 1, "maxLength": 255},
            },
            required=["folderId", "folderName"],
        ),
        side_effect="write",
        risk_level="medium",
        requires_confirmation=False,
        handler=_rename_folder,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.deleteFile",
        description="Soft-delete fileId into the recycle bin. This is high risk.",
        input_schema=_schema({"fileId": _FILE_ID}, required=["fileId"]),
        side_effect="write",
        risk_level="high",
        requires_confirmation=True,
        handler=_delete_file,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.deleteFolder",
        description="Soft-delete folderId into the recycle bin. This is high risk.",
        input_schema=_schema({"folderId": _FOLDER_ID}, required=["folderId"]),
        side_effect="write",
        risk_level="high",
        requires_confirmation=True,
        handler=_delete_folder,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.searchFiles",
        description="Search active files by filename, folder scope, category, MIME prefix, and update time.",
        input_schema=_schema(
            {
                "query": {"type": "string"},
                "folderId": _FOLDER_ID,
                "recursive": {"type": "boolean", "default": True},
                "category": _CATEGORY,
                "mimePrefix": {"type": "string", "description": "MIME type prefix such as video/."},
                "modifiedAfter": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            }
        ),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_search_files,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.getFileInfo",
        description="Return detailed metadata for one active file.",
        input_schema=_schema({"fileId": _FILE_ID}, required=["fileId"]),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_get_file_info,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.listRecent",
        description="List recently updated active files.",
        input_schema=_schema(
            {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
                "since": {"type": "string", "format": "date-time"},
            }
        ),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_list_recent,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.statsByCategory",
        description="Compute file counts and sizes by broad category under a folder.",
        input_schema=_schema(
            {
                "folderId": _FOLDER_ID,
                "recursive": {"type": "boolean", "default": True},
            }
        ),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_stats_by_category,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.findDuplicates",
        description="Find duplicate active files by content hash or by name plus size.",
        input_schema=_schema(
            {
                "folderId": _FOLDER_ID,
                "recursive": {"type": "boolean", "default": True},
                "by": {"type": "string", "enum": ["hash", "nameSize"], "default": "hash"},
            }
        ),
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_find_duplicates,
    )
)

REGISTRY.register(
    ToolSpec(
        name="drive.readFile",
        description=(
            "Read text content of a file the user owns. Returns up to maxBytes; "
            "binary files are not returned directly. Subject to dataPolicy."
        ),
        input_schema=_schema(
            {
                "fileId": _FILE_ID,
                "maxBytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1048576,
                    "default": 262144,
                },
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
            required=["fileId"],
        ),
        side_effect="read",
        risk_level="medium",
        requires_confirmation=False,
        handler=_read_file,
    )
)

__all__ = []
