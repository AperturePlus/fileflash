from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from ..core.deps import get_auth_service, get_current_user, get_settings_dep
from ..core.errors import api_success
from ..core.settings import Settings
from ..models.tables_identity import User
from ..schemas.user import (
    ChangePasswordRequest,
    GetActivityLogQuery,
    UpdateAvatarRequest,
    UpdateProfileRequest,
    UpdateUserPreferenceRequest,
)
from ..services.auth import AuthService

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    profile = await auth_service.get_profile(user_id=current_user.user_id)
    return api_success(data=profile.model_dump(by_alias=True), message="Profile fetched successfully")


@router.put("/update-profile")
async def update_profile(
    payload: UpdateProfileRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    profile = await auth_service.update_profile(
        user_id=current_user.user_id,
        payload=payload,
        user_agent=request.headers.get("user-agent"),
    )
    return api_success(data=profile.model_dump(by_alias=True), message="Profile updated successfully")


@router.put("/avatar")
async def update_avatar(
    payload: UpdateAvatarRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    user_schema = await auth_service.update_avatar(
        user_id=current_user.user_id,
        payload=payload,
    )
    return api_success(data=user_schema.model_dump(by_alias=True), message="Avatar updated successfully")


@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    preference = await auth_service.get_preference(user_id=current_user.user_id)
    return api_success(data=preference.model_dump(by_alias=True), message="Preference fetched successfully")


@router.put("/preferences")
async def update_preferences(
    payload: UpdateUserPreferenceRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    preference = await auth_service.update_preference(user_id=current_user.user_id, payload=payload)
    return api_success(data=preference.model_dump(by_alias=True), message="Preference updated successfully")


@router.put("/password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings_dep),
):
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    await auth_service.change_password(
        user_id=current_user.user_id,
        payload=payload,
        current_refresh_token=refresh_token,
    )
    return api_success(data=None, message="Password changed successfully")


@router.get("/activity-log")
async def get_activity_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200, alias="perPage"),
    operation: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    query = GetActivityLogQuery(page=page, per_page=per_page, operation=operation)
    result = await auth_service.get_activity_log(user_id=current_user.user_id, query=query)
    return api_success(data=result.model_dump(by_alias=True), message="Activity log fetched successfully")

