from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_logs_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.admin.logs import ListAdminLogsQuery
from ..services.admin.logs import AdminLogsService

router = APIRouter(prefix="/admin/logs", tags=["admin"])


@router.get("")
async def list_admin_logs(
    query: ListAdminLogsQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminLogsService = Depends(get_admin_logs_service),
):
    data = await service.list_logs(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Logs fetched")


__all__ = ["router"]
