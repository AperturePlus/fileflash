from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_system_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..services.admin.system import AdminSystemService

router = APIRouter(prefix="/admin/system", tags=["admin"])


@router.get("/health")
async def get_system_health(
    _: User = Depends(require_admin),
    service: AdminSystemService = Depends(get_admin_system_service),
):
    data = await service.health()
    return api_success(data=data.model_dump(by_alias=True), message="System health fetched")


@router.get("/rate-limit")
async def get_rate_limit_status(
    _: User = Depends(require_admin),
    service: AdminSystemService = Depends(get_admin_system_service),
):
    data = await service.rate_limit_status()
    return api_success(data=data.model_dump(by_alias=True), message="Rate limit fetched")


__all__ = ["router"]
