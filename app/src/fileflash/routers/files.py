from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from jwt import InvalidTokenError
from starlette.background import BackgroundTask

from ..core.deps import get_archive_service, get_current_user, get_file_service, get_settings_dep
from ..core.errors import ApiError, api_success
from ..core.security import create_file_preview_token, decode_file_preview_token
from ..core.settings import Settings
from ..models.tables_identity import User
from ..schemas.archive import ArchiveExtractRequest
from ..schemas.file import (
    BatchDownloadRequest,
    BatchFilesRequest,
    FilePreviewUrlResponse,
    GetFilesQuery,
    MoveFileRequest,
    RenameFileRequest,
    ToggleFileStarRequest,
)
from ..schemas.job import to_background_job_response
from ..services.archive import ArchiveService
from ..services.file import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
async def list_files(
    folder_id: str | None = Query(None, alias="folderId"),
    sort: str | None = None,
    order: str | None = None,
    search: str | None = None,
    mime_type: str | None = Query(None, alias="mimeType"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200, alias="perPage"),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    query = GetFilesQuery(
        folder_id=folder_id, sort=sort, order=order,
        search=search, mime_type=mime_type, page=page, per_page=per_page,
    )
    result = await file_service.list_files(user_id=current_user.user_id, query=query)
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/starred")
async def list_starred(
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.list_starred(user_id=current_user.user_id)
    return api_success(data=result.model_dump(by_alias=True))


@router.patch("/{file_id}")
async def rename_file(
    file_id: str,
    payload: RenameFileRequest,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.rename_file(user_id=current_user.user_id, file_id=file_id, payload=payload)
    return api_success(data=result.model_dump(by_alias=True), message="File renamed successfully")


@router.patch("/{file_id}/star")
async def toggle_file_star(
    file_id: str,
    payload: ToggleFileStarRequest,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.toggle_file_star(
        user_id=current_user.user_id,
        file_id=file_id,
        is_starred=payload.is_starred,
    )
    return api_success(data=result.model_dump(by_alias=True), message="File star updated successfully")


@router.patch("/{file_id}/move")
async def move_file(
    file_id: str,
    payload: MoveFileRequest,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.move_file(user_id=current_user.user_id, file_id=file_id, payload=payload)
    return api_success(data=result.model_dump(by_alias=True), message="File moved successfully")


@router.post("/batch")
async def batch_files(
    payload: BatchFilesRequest,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.batch_files(user_id=current_user.user_id, payload=payload)
    return api_success(data=result.model_dump(by_alias=True), message="Batch operation completed successfully")


@router.post("/batch-download")
async def batch_download_files(
    payload: BatchDownloadRequest,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    archive_path, archive_name = await file_service.create_batch_download_archive(
        user_id=current_user.user_id,
        payload=payload,
    )
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=archive_name,
        background=BackgroundTask(lambda p: os.path.exists(p) and os.remove(p), archive_path),
    )


@router.get("/{file_id}")
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    try:
        fid = int(file_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid fileId") from exc

    result = await file_service.get_file(user_id=current_user.user_id, file_id=fid)
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    range_header: str | None = Header(default=None, alias="Range"),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.get_download_stream(
        user_id=current_user.user_id,
        file_id=file_id,
        range_header=range_header,
    )
    return StreamingResponse(
        result.stream,
        media_type=result.content_type,
        headers=result.headers,
        status_code=result.status_code,
    )


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    range_header: str | None = Header(default=None, alias="Range"),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.get_preview_stream(
        user_id=current_user.user_id,
        file_id=file_id,
        range_header=range_header,
    )
    return StreamingResponse(
        result.stream,
        media_type=result.content_type,
        headers=result.headers,
        status_code=result.status_code,
    )


@router.post("/{file_id}/preview-url")
async def create_file_preview_url(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
    settings: Settings = Depends(get_settings_dep),
):
    try:
        fid = int(file_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid fileId") from exc

    await file_service.get_file(user_id=current_user.user_id, file_id=fid)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.file_preview_url_ttl_seconds)
    token = create_file_preview_token(
        user_id=int(current_user.user_id),
        file_id=fid,
        settings=settings,
        expires_at=expires_at,
    )
    stream_url = str(request.url_for("preview_file_stream", file_id=str(fid)))
    result = FilePreviewUrlResponse(
        url=f"{stream_url}?{urlencode({'token': token})}",
        expires_at=expires_at,
    )
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/{file_id}/preview-stream", name="preview_file_stream")
async def preview_file_stream(
    file_id: str,
    token: str = Query(..., min_length=1),
    range_header: str | None = Header(default=None, alias="Range"),
    file_service: FileService = Depends(get_file_service),
    settings: Settings = Depends(get_settings_dep),
):
    try:
        payload = decode_file_preview_token(token, settings)
        user_id = int(payload["sub"])
        token_file_id = str(payload["fileId"])
    except (InvalidTokenError, KeyError, ValueError):
        raise ApiError(status_code=401, code=401, message="Invalid or expired preview token") from None

    if token_file_id != str(file_id):
        raise ApiError(status_code=403, code=403, message="Preview token does not match file")

    result = await file_service.get_preview_stream(
        user_id=user_id,
        file_id=file_id,
        range_header=range_header,
    )
    return StreamingResponse(
        result.stream,
        media_type=result.content_type,
        headers=result.headers,
        status_code=result.status_code,
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.delete_file(user_id=current_user.user_id, file_id=file_id)
    return api_success(
        data=result.model_dump(by_alias=True),
        message="File moved to recycle bin successfully",
    )


@router.post("/{file_id}/archive/preview")
async def create_archive_preview_job(
    file_id: str,
    current_user: User = Depends(get_current_user),
    archive_service: ArchiveService = Depends(get_archive_service),
):
    job = await archive_service.create_preview_job(user_id=current_user.user_id, file_id=file_id)
    return api_success(
        data=to_background_job_response(job).model_dump(by_alias=True),
        message="Archive preview job created",
        code=201,
        status_code=201,
    )


@router.post("/{file_id}/archive/extract")
async def create_archive_extract_job(
    file_id: str,
    payload: ArchiveExtractRequest,
    current_user: User = Depends(get_current_user),
    archive_service: ArchiveService = Depends(get_archive_service),
):
    job = await archive_service.create_extract_job(
        user_id=current_user.user_id,
        file_id=file_id,
        payload=payload,
    )
    return api_success(
        data=to_background_job_response(job).model_dump(by_alias=True),
        message="Archive extract job created",
        code=201,
        status_code=201,
    )
