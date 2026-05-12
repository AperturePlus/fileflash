from __future__ import annotations
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..core.deps import get_auth_service, get_client_ip, get_current_user, get_settings_dep, get_user_agent
from ..core.errors import ApiError, api_success
from ..core.settings import Settings
from ..models.tables_identity import User
from ..schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from ..services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

CookieSameSite = Literal["strict", "lax", "none"]
COOKIE_SAMESITE_MAP: dict[str, CookieSameSite] = {
    "strict": "strict",
    "lax": "lax",
    "none": "none",
}


def _set_refresh_cookie(response: JSONResponse, refresh_token: str, settings: Settings) -> None:
    samesite = COOKIE_SAMESITE_MAP.get(settings.refresh_cookie_samesite.strip().lower())
    if samesite is None:
        raise ValueError(f"Invalid samesite value: {settings.refresh_cookie_samesite}")
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=samesite,
        path=settings.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: JSONResponse, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
    )


@router.post("/register")
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
):
    data = await auth_service.register(payload, client_ip=client_ip, user_agent=user_agent)
    return api_success(
        data=data.model_dump(by_alias=True),
        code=201,
        message="Registration successful",
        status_code=201,
    )


@router.post("/login")
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings_dep),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
):
    token_response, refresh_token = await auth_service.login(
        username=payload.username,
        password=payload.password,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    response = api_success(
        data=token_response.model_dump(by_alias=True),
        message="Login successful",
    )
    _set_refresh_cookie(response, refresh_token, settings)
    return response


@router.post("/refresh")
async def refresh(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings_dep),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
):
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise ApiError(status_code=401, code=401, message="Refresh token not found")

    token_response, next_refresh_token = await auth_service.refresh(
        refresh_token=refresh_token,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    response = api_success(
        data=token_response.model_dump(by_alias=True),
        message="Token refreshed successfully",
    )
    _set_refresh_cookie(response, next_refresh_token, settings)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings_dep),
):
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    await auth_service.logout(refresh_token=refresh_token)
    response = api_success(data=None, message="Logout successful")
    _clear_refresh_cookie(response, settings)
    return response


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
):
    data = await auth_service.forgot_password(
        email=payload.email,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return api_success(
        data=data.model_dump(by_alias=True),
        message="If this email exists, a reset link has been sent",
    )


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.reset_password(token=payload.token, new_password=payload.new_password)
    return api_success(data=None, message="Password has been reset successfully")


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.verify_email(token=payload.token)
    return api_success(data=None, message="Email verified successfully")


@router.post("/resend-verification")
async def resend_verification(
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
):
    await auth_service.resend_verification(
        user_id=current_user.user_id,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return api_success(data=None, message="Verification email sent")

