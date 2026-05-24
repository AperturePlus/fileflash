from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_users_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.admin.users import ListAdminUsersQuery, UpdateUserStatusRequest
from ..services.admin.users import AdminUsersService

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("")
async def list_admin_users(
    query: ListAdminUsersQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminUsersService = Depends(get_admin_users_service),
):
    data = await service.list_users(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Users fetched")


@router.patch("/{user_id}/status")
async def update_admin_user_status(
    user_id: int,
    payload: UpdateUserStatusRequest,
    _: User = Depends(require_admin),
    service: AdminUsersService = Depends(get_admin_users_service),
):
    result = await service.set_status(user_id=user_id, external_status=payload.status)
    return api_success(data=result.model_dump(by_alias=True), message="Status updated")


__all__ = ["router"]
