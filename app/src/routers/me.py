from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_auth_service, get_current_user
from ..core.errors import api_success
from ..models.tables_identity import User
from ..services.auth import AuthService

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    profile = await auth_service.get_profile(user_id=current_user.user_id)
    return api_success(data=profile.model_dump(by_alias=True), message="Profile fetched successfully")

