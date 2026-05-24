from __future__ import annotations

from fastapi import APIRouter, Depends, File as FileParam, Form, UploadFile

from ..core.deps import get_current_user, get_upload_service
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.file import MergeChunksRequest, UploadPreflightRequest
from ..schemas.job import to_background_job_response
from ..services.upload import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/preflight")
async def preflight_upload(
    payload: UploadPreflightRequest,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service),
):
    response = await upload_service.preflight(user_id=current_user.user_id, payload=payload)
    return api_success(data=response.model_dump(by_alias=True), message="Ready for upload")


@router.post("/{upload_id}/chunk")
async def upload_chunk(
    upload_id: str,
    chunk: UploadFile = FileParam(...),
    chunk_index: int = Form(..., alias="chunkIndex"),
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service),
):
    chunk_bytes = await chunk.read()
    await chunk.close()
    await upload_service.upload_chunk(
        user_id=current_user.user_id,
        upload_id=upload_id,
        chunk_index=chunk_index,
        chunk_bytes=chunk_bytes,
    )
    return api_success(data=None, message=f"Chunk {chunk_index} uploaded")


@router.post("/{upload_id}/merge")
async def merge_chunks(
    upload_id: str,
    payload: MergeChunksRequest,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service),
):
    job = await upload_service.enqueue_merge_job(
        user_id=current_user.user_id,
        upload_id=upload_id,
        payload=payload,
    )
    return api_success(
        data=to_background_job_response(job).model_dump(by_alias=True),
        message="Upload merge job created",
        code=201,
        status_code=201,
    )


@router.post("/{upload_id}/cancel")
async def cancel_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service),
):
    response = await upload_service.cancel_upload_session(
        user_id=current_user.user_id,
        upload_id=upload_id,
    )
    return api_success(
        data=response.model_dump(by_alias=True),
        message="Upload session canceled",
    )
