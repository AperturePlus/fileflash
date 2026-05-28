from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_moderation_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.admin.moderation import ListViolationsQuery
from ..services.admin.moderation import AdminModerationService

router = APIRouter(prefix="/admin/violations", tags=["admin"])


@router.get("")
async def list_violations(
    query: ListViolationsQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminModerationService = Depends(get_admin_moderation_service),
):
    data = await service.list_violations(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Violations fetched")


@router.post("/{case_id}/resolve")
async def resolve_violation(
    case_id: int,
    admin: User = Depends(require_admin),
    service: AdminModerationService = Depends(get_admin_moderation_service),
):
    result = await service.resolve_case(case_id=case_id, handled_by=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Violation resolved")


__all__ = ["router"]
