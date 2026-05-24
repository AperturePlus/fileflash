from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_storage_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.admin.storage import ListStorageUsersQuery, UpdateQuotaRequest, UsageTrendQuery
from ..services.admin.storage import AdminStorageService

router = APIRouter(prefix="/admin/storage", tags=["admin"])


@router.get("/summary")
async def get_admin_storage_summary(
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    data = await service.summary()
    return api_success(data=data.model_dump(by_alias=True), message="Storage summary fetched")


@router.get("/users")
async def list_admin_storage_users(
    query: ListStorageUsersQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    data = await service.list_storage_users(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Storage users fetched")


@router.patch("/users/{user_id}/quota")
async def update_admin_user_quota(
    user_id: int,
    payload: UpdateQuotaRequest,
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    result = await service.update_quota(user_id=user_id, new_limit=payload.storage_limit)
    return api_success(data=result.model_dump(by_alias=True), message="Quota updated")


@router.get("/usage-trend")
async def get_storage_usage_trend(
    query: UsageTrendQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    result = await service.usage_trend(query=query)
    return api_success(data=result.model_dump(by_alias=True), message="Usage trend fetched")


__all__ = ["router"]
