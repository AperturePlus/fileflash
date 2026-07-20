from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from math import ceil
from pathlib import Path
from typing import Literal

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.http_headers import build_content_disposition
from ..core.security import (
    create_share_access_token,
    decode_share_access_token,
    get_password_hash,
    verify_password,
)
from ..core.settings import Settings
from ..db.transaction import (
    apply_local_lock_timeout,
    is_retryable_database_error,
    run_with_transaction_retry,
    to_retryable_concurrency_error,
)
from ..models.enums import FileStatus, FolderStatus, FolderType, ShareStatus
from ..models.tables_access_share import Share, ShareAccessLog
from ..models.tables_storage import File, FileMediaMetadata, Folder, StorageObject
from ..s3.minio_client import MinioObjectStorageClient
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.share import (
    AccessShareResponseData,
    AccessUrls,
    CreateShareRequest,
    GetSharesQuery,
    SaveShareRequest,
    SaveShareResponse,
    SharedItemInfo,
    ShareSettings,
    UpdateShareSettingsRequest,
)
from ..schemas.share import (
    Share as ShareSchema,
)

logger = logging.getLogger(__name__)


class ShareService:
    SHARE_CODE_LENGTH = 4
    SHARE_ACCESS_TOKEN_TTL_SECONDS = 30 * 60

    def __init__(self, *, db: AsyncSession, settings: Settings, storage: MinioObjectStorageClient) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage

    async def create_share(self, *, user_id: int, payload: CreateShareRequest) -> ShareSchema:
        resource_id = self._parse_int(payload.resource_id, field_name="resourceId")

        async def _operation() -> ShareSchema:
            now = datetime.now(UTC)
            await apply_local_lock_timeout(self.db)

            if payload.resource_type == "file":
                file_row = await self._get_active_file(file_id=resource_id, owner_id=user_id, for_update=True)
                existing = await self._find_existing_active_share(
                    user_id=user_id,
                    now=now,
                    file_id=file_row.file_id,
                    folder_id=None,
                )
                if existing is not None:
                    return await self._build_share_schema(existing)

                share_code = await self._generate_share_code()
                share_row = Share(
                    user_id=user_id,
                    resource_type="file",
                    file_id=file_row.file_id,
                    folder_id=None,
                    share_link=share_code,
                    share_code=share_code,
                    status=ShareStatus.ACTIVE,
                    share_type="public",
                    permission_role="viewer",
                    allow_preview=True,
                    allow_download=True,
                    allow_save=True,
                    allow_reshare=False,
                    require_login=False,
                )
                self.db.add(share_row)
                await self.db.commit()
                return await self._build_share_schema(share_row)

            if payload.resource_type == "folder":
                folder_row = await self._get_active_folder(folder_id=resource_id, owner_id=user_id, for_update=True)
                existing = await self._find_existing_active_share(
                    user_id=user_id,
                    now=now,
                    file_id=None,
                    folder_id=folder_row.folder_id,
                )
                if existing is not None:
                    return await self._build_share_schema(existing)

                share_code = await self._generate_share_code()
                share_row = Share(
                    user_id=user_id,
                    resource_type="folder",
                    file_id=None,
                    folder_id=folder_row.folder_id,
                    share_link=share_code,
                    share_code=share_code,
                    status=ShareStatus.ACTIVE,
                    share_type="public",
                    permission_role="viewer",
                    allow_preview=False,
                    allow_download=False,
                    allow_save=True,
                    allow_reshare=False,
                    require_login=False,
                )
                self.db.add(share_row)
                await self.db.commit()
                return await self._build_share_schema(share_row)

            raise ApiError(status_code=400, code=400, message="resourceType must be file or folder")

        try:
            return await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def list_shares(self, *, user_id: int, query: GetSharesQuery) -> PaginatedData[ShareSchema]:
        page = max(1, query.page)
        per_page = max(1, query.per_page)
        offset = (page - 1) * per_page

        total_items = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Share)
                .where(
                    and_(
                        Share.user_id == user_id,
                        Share.status != ShareStatus.DELETED,
                    )
                )
            )
            or 0
        )

        share_rows = list(
            await self.db.scalars(
                select(Share)
                .where(
                    and_(
                        Share.user_id == user_id,
                        Share.status != ShareStatus.DELETED,
                    )
                )
                .order_by(Share.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        )

        items: list[ShareSchema] = []
        for row in share_rows:
            items.append(await self._build_share_schema(row))

        pagination = PaginationMeta(
            total_items=total_items,
            total_pages=max(1, ceil(total_items / per_page)) if per_page else 1,
            per_page=per_page,
            current_page=page,
            has_prev=page > 1,
            has_next=(page * per_page) < total_items,
        )
        return PaginatedData(items=items, pagination=pagination)

    async def get_share_details(self, *, share_link: str) -> ShareSchema:
        share_row = await self._get_share_by_link(share_link=share_link)
        if share_row is None or share_row.status == ShareStatus.DELETED:
            raise ApiError(status_code=404, code=404, message="Share not found")
        return await self._build_share_schema(share_row)

    async def access_share(
        self,
        *,
        share_link: str,
        password: str | None,
        ip_address: str,
        user_agent: str | None,
    ) -> AccessShareResponseData:
        async def _operation() -> AccessShareResponseData:
            await apply_local_lock_timeout(self.db)
            share_row = await self._get_share_by_link(share_link=share_link, for_update=True)
            if share_row is None or share_row.status == ShareStatus.DELETED:
                raise ApiError(status_code=404, code=404, message="Share not found")

            now = datetime.now(UTC)
            if share_row.expire_time and share_row.expire_time <= now:
                raise ApiError(status_code=410, code=410, message="Share link expired")
            if share_row.status != ShareStatus.ACTIVE:
                raise ApiError(status_code=404, code=404, message="Share not found")

            if share_row.password_hash:
                if not password:
                    await self._log_share_event(
                        share_id=share_row.share_id,
                        user_id=None,
                        event_type="access",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        result="failed",
                    )
                    await self.db.commit()
                    raise ApiError(status_code=403, code=403, message="Share password required")
                if not verify_password(password, share_row.password_hash):
                    await self._log_share_event(
                        share_id=share_row.share_id,
                        user_id=None,
                        event_type="access",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        result="failed",
                    )
                    await self.db.commit()
                    raise ApiError(status_code=403, code=403, message="Invalid share password")

            await self.db.execute(
                update(Share)
                .where(Share.share_id == share_row.share_id)
                .values(
                    visit_count=Share.visit_count + 1,
                    last_accessed_at=now,
                )
            )
            await self._log_share_event(
                share_id=share_row.share_id,
                user_id=None,
                event_type="access",
                ip_address=ip_address,
                user_agent=user_agent,
                result="success",
            )

            access_token = create_share_access_token(
                share_id=int(share_row.share_id),
                settings=self.settings,
                ttl_seconds=self.SHARE_ACCESS_TOKEN_TTL_SECONDS,
            )
            await self.db.commit()

            item_type, item_info = await self._load_share_item_info(share_row)
            access_urls = AccessUrls(
                download=self._share_download_url(share_row) if (item_type == "file" and share_row.allow_download) else "",
                preview=self._share_preview_url(share_row) if (item_type == "file" and share_row.allow_preview) else "",
            )
            return AccessShareResponseData(
                access_token=access_token,
                expires_in=self.SHARE_ACCESS_TOKEN_TTL_SECONDS,
                item_type=item_type,
                item_info=item_info,
                access_urls=access_urls,
            )

        try:
            return await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def update_settings(
        self,
        *,
        user_id: int,
        share_link: str,
        payload: UpdateShareSettingsRequest,
    ) -> ShareSchema:
        share_row = await self._get_share_for_update(user_id=user_id, share_link=share_link)
        if share_row is None or share_row.status == ShareStatus.DELETED:
            raise ApiError(status_code=404, code=404, message="Share not found")

        issued_password: str | None = None

        if "allow_download" in payload.model_fields_set and payload.allow_download is not None:
            share_row.allow_download = bool(payload.allow_download)
        if "allow_preview" in payload.model_fields_set and payload.allow_preview is not None:
            share_row.allow_preview = bool(payload.allow_preview)
        if "expire_at" in payload.model_fields_set:
            share_row.expire_time = payload.expire_at

        if "password_protected" in payload.model_fields_set and payload.password_protected is False:
            share_row.password_hash = None
        elif payload.password_protected is True:
            wants_regenerate = bool(payload.regenerate_password)
            has_custom = bool(payload.password and payload.password.strip())
            has_existing = bool(share_row.password_hash)

            if wants_regenerate or has_custom or not has_existing:
                issued_password = payload.password.strip() if has_custom else self._generate_password()
                share_row.password_hash = get_password_hash(issued_password)

        await self.db.commit()
        return await self._build_share_schema(share_row, password=issued_password)

    async def delete_share(self, *, user_id: int, share_link: str) -> tuple[str, str, datetime]:
        share_row = await self._get_share_for_update(user_id=user_id, share_link=share_link)
        if share_row is None or share_row.status == ShareStatus.DELETED:
            raise ApiError(status_code=404, code=404, message="Share not found")

        now = datetime.now(UTC)
        share_row.status = ShareStatus.DELETED
        await self.db.commit()
        return str(share_row.share_id), share_row.share_link, now

    async def save_to_my_space(
        self,
        *,
        user_id: int,
        share_link: str,
        payload: SaveShareRequest,
        ip_address: str,
        user_agent: str | None,
    ) -> SaveShareResponse:
        share_row = await self._resolve_share_for_access_token(
            share_link=share_link,
            share_access_token=payload.share_access_token,
        )
        if not share_row.allow_save:
            raise ApiError(status_code=403, code=403, message="Saving is not allowed for this share")

        target_folder_id = await self._resolve_target_folder_id(user_id=user_id, target_folder_id=payload.target_folder_id)

        now = datetime.now(UTC)

        if share_row.resource_type == "file":
            if not share_row.file_id:
                raise ApiError(status_code=404, code=404, message="Shared file not found")
            new_file = await self._copy_file_to_user_space(
                actor_user_id=user_id,
                source_owner_id=share_row.user_id,
                source_file_id=int(share_row.file_id),
                target_folder_id=target_folder_id,
            )
            await self._log_share_event(
                share_id=share_row.share_id,
                user_id=user_id,
                event_type="save",
                ip_address=ip_address,
                user_agent=user_agent,
                result="success",
            )
            await self.db.commit()
            return SaveShareResponse(
                saved_at=now,
                item_type="file",
                item_id=str(new_file.file_id),
                target_folder_id=payload.target_folder_id,
            )

        if share_row.resource_type == "folder":
            if not share_row.folder_id:
                raise ApiError(status_code=404, code=404, message="Shared folder not found")
            new_folder = await self._copy_folder_to_user_space(
                actor_user_id=user_id,
                source_owner_id=share_row.user_id,
                source_folder_id=int(share_row.folder_id),
                target_parent_folder_id=target_folder_id,
            )
            await self._log_share_event(
                share_id=share_row.share_id,
                user_id=user_id,
                event_type="save",
                ip_address=ip_address,
                user_agent=user_agent,
                result="success",
            )
            await self.db.commit()
            return SaveShareResponse(
                saved_at=now,
                item_type="folder",
                item_id=str(new_folder.folder_id),
                target_folder_id=payload.target_folder_id,
            )

        raise ApiError(status_code=400, code=400, message="resourceType must be file or folder")

    async def get_shared_file_stream(
        self,
        *,
        share_link: str,
        share_access_token: str,
        action: Literal["download", "preview"],
        ip_address: str,
        user_agent: str | None,
    ) -> tuple[AsyncIterator[bytes], str, str, int]:
        stream, filename, content_type, status_code, _headers = await self.get_shared_file_download_stream_response(
            share_link=share_link,
            share_access_token=share_access_token,
            action=action,
            range_header=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return stream, filename, content_type, status_code

    async def get_shared_file_download_stream_response(
        self,
        *,
        share_link: str,
        share_access_token: str,
        action: Literal["download", "preview"],
        range_header: str | None,
        ip_address: str,
        user_agent: str | None,
        rate_limit_check: Callable[[int], Awaitable[None]] | None = None,
    ) -> tuple[AsyncIterator[bytes], str, str, int, dict[str, str]]:
        async def _operation() -> tuple[AsyncIterator[bytes], str, str, int, dict[str, str]]:
            await apply_local_lock_timeout(self.db)
            share_row = await self._resolve_share_for_access_token(
                share_link=share_link,
                share_access_token=share_access_token,
                for_update=True,
            )
            if share_row.resource_type != "file" or not share_row.file_id:
                raise ApiError(status_code=400, code=400, message="Only file shares support download/preview")

            if action == "download" and not share_row.allow_download:
                raise ApiError(status_code=403, code=403, message="Download is not allowed for this share")
            if action == "preview" and not share_row.allow_preview:
                raise ApiError(status_code=403, code=403, message="Preview is not allowed for this share")

            file_row = await self._get_active_file(file_id=int(share_row.file_id), owner_id=share_row.user_id)
            storage_object = await self._resolve_shared_stream_storage_object(
                file_row=file_row,
                prefer_optimized=(action == "preview"),
            )
            if storage_object is None:
                raise ApiError(status_code=404, code=404, message="Shared file content not found")
            object_size = int(storage_object.object_size or file_row.file_size or 0)
            if object_size <= 0:
                raise ApiError(status_code=404, code=404, message="Shared file content not found")

            byte_range = self._parse_range_header(range_header=range_header, file_size=object_size)
            bytes_to_send = object_size if byte_range is None else byte_range[1] - byte_range[0] + 1
            if rate_limit_check is not None:
                await rate_limit_check(bytes_to_send)

            if action == "download":
                await self.db.execute(
                    update(Share)
                    .where(Share.share_id == share_row.share_id)
                    .values(download_count=Share.download_count + 1)
                )

            await self._log_share_event(
                share_id=share_row.share_id,
                user_id=None,
                event_type=action,
                ip_address=ip_address,
                user_agent=user_agent,
                result="success",
            )
            await self.db.commit()

            content_type = (
                storage_object.content_type
                or file_row.mime_type
                or "application/octet-stream"
            )
            headers = {
                "Accept-Ranges": "bytes",
                "Content-Disposition": build_content_disposition(
                    file_row.file_name,
                    disposition="attachment" if action == "download" else "inline",
                ),
            }

            if byte_range is None:
                headers["Content-Length"] = str(object_size)
                return (
                    self.storage.iter_object(
                        bucket_name=storage_object.bucket_name,
                        object_key=storage_object.object_key,
                    ),
                    file_row.file_name,
                    content_type,
                    200,
                    headers,
                )

            start, end = byte_range
            headers["Content-Length"] = str(end - start + 1)
            headers["Content-Range"] = f"bytes {start}-{end}/{object_size}"
            return (
                self.storage.iter_object_range(
                    bucket_name=storage_object.bucket_name,
                    object_key=storage_object.object_key,
                    start=start,
                    end=end,
                ),
                file_row.file_name,
                content_type,
                206,
                headers,
            )

        try:
            return await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def _resolve_share_for_access_token(
        self,
        *,
        share_link: str,
        share_access_token: str,
        for_update: bool = False,
    ) -> Share:
        try:
            payload = decode_share_access_token(share_access_token, self.settings)
            share_id = int(payload["sub"])
        except Exception as exc:  # noqa: BLE001
            raise ApiError(status_code=401, code=401, message="Invalid share access token") from exc

        statement = select(Share).where(Share.share_id == share_id)
        if for_update:
            statement = statement.with_for_update()
        share_row = await self.db.scalar(statement)
        if share_row is None or share_row.status == ShareStatus.DELETED:
            raise ApiError(status_code=401, code=401, message="Invalid share access token")

        if share_link not in {share_row.share_link, share_row.share_code}:
            raise ApiError(status_code=403, code=403, message="Invalid share access token")

        now = datetime.now(UTC)
        if share_row.expire_time and share_row.expire_time <= now:
            raise ApiError(status_code=410, code=410, message="Share link expired")
        if share_row.status != ShareStatus.ACTIVE:
            raise ApiError(status_code=404, code=404, message="Share not found")

        return share_row

    async def _find_existing_active_share(
        self,
        *,
        user_id: int,
        now: datetime,
        file_id: int | None,
        folder_id: int | None,
    ) -> Share | None:
        stmt = select(Share).where(
            and_(
                Share.user_id == user_id,
                Share.status == ShareStatus.ACTIVE,
                Share.file_id == file_id,
                Share.folder_id == folder_id,
                or_(Share.expire_time.is_(None), Share.expire_time > now),
            )
        )
        return await self.db.scalar(stmt.limit(1))

    async def _get_share_by_link(self, *, share_link: str, for_update: bool = False) -> Share | None:
        statement = select(Share).where(or_(Share.share_link == share_link, Share.share_code == share_link)).limit(1)
        if for_update:
            statement = statement.with_for_update()
        return await self.db.scalar(statement)

    async def _get_share_for_update(self, *, user_id: int, share_link: str) -> Share | None:
        return await self.db.scalar(
            select(Share)
            .where(
                and_(
                    Share.user_id == user_id,
                    or_(Share.share_link == share_link, Share.share_code == share_link),
                )
            )
            .with_for_update()
            .limit(1)
        )

    async def _build_share_schema(self, share_row: Share, *, password: str | None = None) -> ShareSchema:
        item_type, item_info = await self._load_share_item_info(share_row)
        settings = ShareSettings(
            password_protected=bool(share_row.password_hash),
            password=password,
            expire_at=share_row.expire_time,
            allow_download=bool(share_row.allow_download),
            allow_preview=bool(share_row.allow_preview),
        )
        return ShareSchema(
            share_id=str(share_row.share_id),
            share_link=str(share_row.share_link),
            item_type=item_type,
            item_info=item_info,
            settings=settings,
            created_at=share_row.created_at or datetime.now(UTC),
            visit_count=int(share_row.visit_count or 0),
            download_count=int(share_row.download_count or 0),
        )

    async def _load_share_item_info(self, share_row: Share) -> tuple[Literal["file", "folder"], SharedItemInfo]:
        if share_row.resource_type == "file":
            file_id = int(share_row.file_id or 0)
            file_row = await self.db.get(File, file_id) if file_id else None
            if file_row is None:
                return (
                    "file",
                    SharedItemInfo(
                        id=str(file_id or ""),
                        name="(missing file)",
                        size=0,
                        mime_type="application/octet-stream",
                        folder_path=None,
                    ),
                )
            return (
                "file",
                SharedItemInfo(
                    id=str(file_row.file_id),
                    name=file_row.file_name,
                    size=int(file_row.file_size or 0),
                    mime_type=file_row.mime_type or "application/octet-stream",
                    folder_path=None,
                ),
            )

        folder_id = int(share_row.folder_id or 0)
        folder_row = await self.db.get(Folder, folder_id) if folder_id else None
        if folder_row is None:
            return (
                "folder",
                SharedItemInfo(
                    id=str(folder_id or ""),
                    name="(missing folder)",
                    size=0,
                    mime_type="inode/directory",
                    folder_path=None,
                ),
            )

        return (
            "folder",
            SharedItemInfo(
                id=str(folder_row.folder_id),
                name=folder_row.folder_name,
                size=int(folder_row.cached_size or 0),
                mime_type="inode/directory",
                folder_path=None,
            ),
        )

    async def _get_active_file(self, *, file_id: int, owner_id: int, for_update: bool = False) -> File:
        statement = select(File).where(
            and_(
                File.file_id == file_id,
                File.owner_id == owner_id,
                File.status == FileStatus.ACTIVE,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        file_row = await self.db.scalar(statement)
        if file_row is None:
            raise ApiError(status_code=404, code=404, message="File not found")
        return file_row

    async def _get_active_folder(self, *, folder_id: int, owner_id: int, for_update: bool = False) -> Folder:
        statement = select(Folder).where(
            and_(
                Folder.folder_id == folder_id,
                Folder.owner_id == owner_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        folder_row = await self.db.scalar(statement)
        if folder_row is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")
        return folder_row

    async def _resolve_target_folder_id(self, *, user_id: int, target_folder_id: str) -> int:
        if target_folder_id == "root":
            folder = await self.db.scalar(
                select(Folder).where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.parent_folder_id.is_(None),
                        Folder.folder_type == FolderType.ROOT,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
            if folder is None:
                folder_name = await self._next_available_root_folder_name(user_id=user_id, base_name="My Files")
                folder = Folder(
                    owner_id=user_id,
                    folder_name=folder_name,
                    parent_folder_id=None,
                    status=FolderStatus.ACTIVE,
                    folder_type=FolderType.ROOT,
                )
                self.db.add(folder)
                await self.db.flush()
            return int(folder.folder_id)

        folder_id = self._parse_int(target_folder_id, field_name="targetFolderId")
        folder_row = await self._get_active_folder(folder_id=folder_id, owner_id=user_id)
        return int(folder_row.folder_id)

    async def _next_available_root_folder_name(self, *, user_id: int, base_name: str) -> str:
        candidate = base_name
        suffix = 1
        while await self.db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_name == candidate,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        ):
            suffix += 1
            candidate = f"{base_name} ({suffix})"
        return candidate

    async def _next_available_folder_name(self, *, user_id: int, parent_folder_id: int, original_name: str) -> str:
        stem = original_name.strip() or "Folder"
        index = 1
        while True:
            candidate = f"{stem} ({index})"
            conflict = await self.db.scalar(
                select(Folder.folder_id).where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.parent_folder_id == parent_folder_id,
                        Folder.folder_name == candidate,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
            if conflict is None:
                return candidate
            index += 1

    async def _next_available_file_name(self, *, user_id: int, folder_id: int, original_name: str) -> str:
        stem = Path(original_name).stem or "file"
        suffix = Path(original_name).suffix
        index = 1
        while True:
            candidate = f"{stem} ({index}){suffix}"
            conflict = await self.db.scalar(
                select(File.file_id).where(
                    and_(
                        File.owner_id == user_id,
                        File.folder_id == folder_id,
                        File.file_name == candidate,
                        File.status == FileStatus.ACTIVE,
                    )
                )
            )
            if conflict is None:
                return candidate
            index += 1

    async def _copy_file_to_user_space(
        self,
        *,
        actor_user_id: int,
        source_owner_id: int,
        source_file_id: int,
        target_folder_id: int,
    ) -> File:
        source = await self._get_active_file(file_id=source_file_id, owner_id=source_owner_id)

        target_name = source.file_name
        conflict = await self.db.scalar(
            select(File.file_id).where(
                and_(
                    File.owner_id == actor_user_id,
                    File.folder_id == target_folder_id,
                    File.file_name == target_name,
                    File.status == FileStatus.ACTIVE,
                )
            )
        )
        if conflict is not None:
            target_name = await self._next_available_file_name(
                user_id=actor_user_id,
                folder_id=target_folder_id,
                original_name=target_name,
            )

        new_file = File(
            uploader_id=actor_user_id,
            owner_id=actor_user_id,
            folder_id=target_folder_id,
            file_name=target_name,
            file_ext=self._extract_ext(target_name),
            mime_type=source.mime_type,
            storage_object_id=source.storage_object_id,
            file_size=source.file_size,
            status=FileStatus.ACTIVE,
        )
        self.db.add(new_file)
        await self.db.flush()

        await self.db.execute(
            update(StorageObject)
            .where(StorageObject.object_id == source.storage_object_id)
            .values(ref_count=StorageObject.ref_count + 1)
        )
        return new_file

    async def _copy_folder_to_user_space(
        self,
        *,
        actor_user_id: int,
        source_owner_id: int,
        source_folder_id: int,
        target_parent_folder_id: int,
    ) -> Folder:
        source = await self._get_active_folder(folder_id=source_folder_id, owner_id=source_owner_id)

        target_name = source.folder_name
        conflict = await self.db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.owner_id == actor_user_id,
                    Folder.parent_folder_id == target_parent_folder_id,
                    Folder.folder_name == target_name,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if conflict is not None:
            target_name = await self._next_available_folder_name(
                user_id=actor_user_id,
                parent_folder_id=target_parent_folder_id,
                original_name=target_name,
            )

        new_folder = Folder(
            owner_id=actor_user_id,
            parent_folder_id=target_parent_folder_id,
            folder_name=target_name,
            cached_size=source.cached_size or 0,
            status=FolderStatus.ACTIVE,
            folder_type=FolderType.NORMAL,
        )
        self.db.add(new_folder)
        await self.db.flush()

        await self._copy_folder_children(
            actor_user_id=actor_user_id,
            source_owner_id=source_owner_id,
            source_folder_id=int(source.folder_id),
            target_folder_id=int(new_folder.folder_id),
        )

        return new_folder

    async def _copy_folder_children(
        self,
        *,
        actor_user_id: int,
        source_owner_id: int,
        source_folder_id: int,
        target_folder_id: int,
    ) -> None:
        child_folders = list(
            await self.db.scalars(
                select(Folder).where(
                    and_(
                        Folder.owner_id == source_owner_id,
                        Folder.parent_folder_id == source_folder_id,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
        )

        for child in child_folders:
            child_name = child.folder_name
            conflict = await self.db.scalar(
                select(Folder.folder_id).where(
                    and_(
                        Folder.owner_id == actor_user_id,
                        Folder.parent_folder_id == target_folder_id,
                        Folder.folder_name == child_name,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
            if conflict is not None:
                child_name = await self._next_available_folder_name(
                    user_id=actor_user_id,
                    parent_folder_id=target_folder_id,
                    original_name=child_name,
                )

            new_child = Folder(
                owner_id=actor_user_id,
                parent_folder_id=target_folder_id,
                folder_name=child_name,
                cached_size=child.cached_size or 0,
                status=FolderStatus.ACTIVE,
                folder_type=FolderType.NORMAL,
            )
            self.db.add(new_child)
            await self.db.flush()

            await self._copy_folder_children(
                actor_user_id=actor_user_id,
                source_owner_id=source_owner_id,
                source_folder_id=int(child.folder_id),
                target_folder_id=int(new_child.folder_id),
            )

        child_files = list(
            await self.db.scalars(
                select(File).where(
                    and_(
                        File.owner_id == source_owner_id,
                        File.folder_id == source_folder_id,
                        File.status == FileStatus.ACTIVE,
                    )
                )
            )
        )
        for child in child_files:
            await self._copy_file_to_user_space(
                actor_user_id=actor_user_id,
                source_owner_id=source_owner_id,
                source_file_id=int(child.file_id),
                target_folder_id=target_folder_id,
            )

    async def _resolve_shared_stream_storage_object(
        self,
        *,
        file_row: File,
        prefer_optimized: bool,
    ) -> StorageObject | None:
        source_object = await self.db.get(StorageObject, int(file_row.storage_object_id))
        if source_object is None:
            return None
        if not prefer_optimized:
            return source_object

        metadata_row = await self.db.scalar(
            select(FileMediaMetadata)
            .where(FileMediaMetadata.source_object_id == int(file_row.storage_object_id))
            .limit(1)
        )
        if not isinstance(metadata_row, FileMediaMetadata):
            return source_object
        transcode = (metadata_row.extra_metadata or {}).get("transcode")
        if not isinstance(transcode, dict):
            return source_object
        if str(transcode.get("status") or "").strip().lower() != "ready":
            return source_object

        bucket_name = str(transcode.get("optimizedBucketName") or "").strip()
        object_key = str(transcode.get("optimizedObjectKey") or "").strip()
        if not bucket_name or not object_key:
            return source_object

        optimized_object = await self.db.scalar(
            select(StorageObject)
            .where(
                and_(
                    StorageObject.bucket_name == bucket_name,
                    StorageObject.object_key == object_key,
                )
            )
            .limit(1)
        )
        if isinstance(optimized_object, StorageObject):
            return optimized_object

        exists = await self.storage.object_exists(bucket_name=bucket_name, object_key=object_key)
        if not exists:
            return source_object
        stat = await self.storage.stat_object(bucket_name=bucket_name, object_key=object_key)
        created = StorageObject(
            bucket_name=bucket_name,
            object_key=object_key,
            object_size=int(stat.size),
            etag=stat.etag,
            version_id=stat.version_id,
            content_type=stat.content_type,
        )
        self.db.add(created)
        await self.db.flush()
        return created

    @staticmethod
    def _parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
        if not range_header:
            return None

        value = range_header.strip()
        if not value.lower().startswith("bytes="):
            raise ApiError(status_code=416, code=416, message="Invalid Range header")

        spec = value[6:].strip()
        if "," in spec:
            raise ApiError(status_code=416, code=416, message="Multiple ranges are not supported")

        if spec.startswith("-"):
            suffix_part = spec[1:].strip()
            if not suffix_part.isdigit():
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            suffix = int(suffix_part)
            if suffix <= 0:
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            start = max(file_size - suffix, 0)
            end = file_size - 1
            return start, end

        if "-" not in spec:
            raise ApiError(status_code=416, code=416, message="Invalid Range header")

        start_part, end_part = spec.split("-", 1)
        if not start_part.strip().isdigit():
            raise ApiError(status_code=416, code=416, message="Invalid Range header")
        start = int(start_part.strip())
        end = file_size - 1
        if end_part.strip():
            if not end_part.strip().isdigit():
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            end = int(end_part.strip())

        if start < 0 or start >= file_size or end < start:
            raise ApiError(status_code=416, code=416, message="Requested range is not satisfiable")

        if end >= file_size:
            end = file_size - 1
        return start, end

    async def _log_share_event(
        self,
        *,
        share_id: int,
        user_id: int | None,
        event_type: str,
        ip_address: str | None,
        user_agent: str | None,
        result: str,
    ) -> None:
        self.db.add(
            ShareAccessLog(
                share_id=share_id,
                user_id=user_id,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=user_agent,
                result=result,
            )
        )

    async def _generate_share_code(self) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        for _ in range(12):
            code = "".join(secrets.choice(alphabet) for _ in range(self.SHARE_CODE_LENGTH))
            exists = await self.db.scalar(
                select(Share.share_id).where(or_(Share.share_code == code, Share.share_link == code)).limit(1)
            )
            if exists is None:
                return code
        raise ApiError(status_code=500, code=500, message="Failed to generate unique share link")

    @staticmethod
    def _generate_password() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _parse_int(raw: str, *, field_name: str) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}") from None
        if value <= 0:
            raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}") from None
        return value

    @staticmethod
    def _extract_ext(file_name: str) -> str | None:
        suffix = Path(file_name).suffix.strip(".").lower()
        return suffix or None

    def _share_download_url(self, share_row: Share) -> str:
        return f"{self.settings.api_v1_prefix}/shares/{share_row.share_link}/download"

    def _share_preview_url(self, share_row: Share) -> str:
        return f"{self.settings.api_v1_prefix}/shares/{share_row.share_link}/preview"
