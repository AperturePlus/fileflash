from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_files_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.admin.files import ListAdminFilesQuery
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


@router.post("/{file_id}/rescan")
async def rescan_admin_file(
    file_id: int,
    admin: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    result = await service.request_rescan(file_id=file_id, requested_by=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Rescan requested")


__all__ = ["router"]
