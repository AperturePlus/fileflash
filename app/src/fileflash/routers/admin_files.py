from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse
from jwt import InvalidTokenError

from ..core.deps import get_admin_files_service, get_settings_dep, require_admin
from ..core.errors import ApiError, api_success
from ..core.security import create_admin_file_preview_token, decode_admin_file_preview_token
from ..core.settings import Settings
from ..models.tables_identity import User
from ..schemas.admin.files import ListAdminFilesQuery
from ..schemas.file import FilePreviewUrlResponse
from ..services.admin.files import AdminFilesService

router = APIRouter(prefix="/admin/files", tags=["admin"])


@router.get("")
async def list_admin_files(
    query: ListAdminFilesQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    data = await service.list_files(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Files fetched")


@router.get("/{file_id}")
async def get_admin_file_detail(
    file_id: int,
    _: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    result = await service.get_file_detail(file_id=file_id)
    return api_success(data=result.model_dump(by_alias=True), message="File audit detail fetched")


@router.get("/{file_id}/preview")
async def preview_admin_file(
    file_id: int,
    range_header: str | None = Header(default=None, alias="Range"),
    _: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    result = await service.get_preview_stream(file_id=file_id, range_header=range_header)
    return StreamingResponse(
        result.stream,
        media_type=result.content_type,
        headers=result.headers,
        status_code=result.status_code,
    )


@router.post("/{file_id}/preview-url")
async def create_admin_file_preview_url(
    file_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
    settings: Settings = Depends(get_settings_dep),
):
    await service.get_file_detail(file_id=file_id)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.file_preview_url_ttl_seconds)
    token = create_admin_file_preview_token(
        admin_user_id=int(admin.user_id),
        file_id=file_id,
        settings=settings,
        expires_at=expires_at,
    )
    stream_url = str(request.url_for("admin_preview_file_stream", file_id=str(file_id)))
    result = FilePreviewUrlResponse(
        url=f"{stream_url}?{urlencode({'token': token})}",
        expires_at=expires_at,
    )
    return api_success(data=result.model_dump(by_alias=True), message="Preview URL created")


@router.get("/{file_id}/preview-stream", name="admin_preview_file_stream")
async def preview_admin_file_stream(
    file_id: int,
    token: str = Query(..., min_length=1),
    range_header: str | None = Header(default=None, alias="Range"),
    service: AdminFilesService = Depends(get_admin_files_service),
    settings: Settings = Depends(get_settings_dep),
):
    try:
        payload = decode_admin_file_preview_token(token, settings)
        token_file_id = str(payload["fileId"])
    except (InvalidTokenError, KeyError, ValueError):
        raise ApiError(status_code=401, code=401, message="Invalid or expired preview token") from None

    if token_file_id != str(file_id):
        raise ApiError(status_code=403, code=403, message="Preview token does not match file")

    result = await service.get_preview_stream(file_id=file_id, range_header=range_header)
    return StreamingResponse(
        result.stream,
        media_type=result.content_type,
        headers=result.headers,
        status_code=result.status_code,
    )


@router.post("/{file_id}/rescan")
async def rescan_admin_file(
    file_id: int,
    admin: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    result = await service.request_rescan(file_id=file_id, requested_by=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Rescan requested")


__all__ = ["router"]
