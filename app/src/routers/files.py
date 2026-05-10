from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from ..core.deps import get_archive_service, get_current_user, get_file_service
from ..core.errors import ApiError, api_success
from ..models.tables_identity import User
from ..schemas.archive import ArchiveExtractRequest
from ..schemas.file import BatchDownloadRequest, BatchFilesRequest, GetFilesQuery, MoveFileRequest
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
