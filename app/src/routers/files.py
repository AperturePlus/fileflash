from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_archive_service, get_current_user
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.archive import ArchiveExtractRequest
from ..schemas.job import to_background_job_response
from ..services.archive import ArchiveService

router = APIRouter(prefix="/files", tags=["files"])


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

