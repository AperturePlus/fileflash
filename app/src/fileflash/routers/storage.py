from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_auth_service, get_current_user
from ..core.errors import api_success
from ..models.tables_identity import User
from ..services.auth import AuthService

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/summary")
async def get_storage_summary(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    summary = await auth_service.get_storage_summary(user_id=current_user.user_id)
    return api_success(data=summary.model_dump(by_alias=True), message="Storage summary fetched successfully")

