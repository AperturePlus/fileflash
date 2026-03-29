from __future__ import annotations

from pydantic import Field

from .common import CamelModel
from .user import User


class RegisterRequest(CamelModel):
    username: str = Field(min_length=2, max_length=100)
    email: str
    password: str = Field(min_length=6, max_length=255)


class LoginRequest(CamelModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class ForgotPasswordRequest(CamelModel):
    email: str


class ForgotPasswordResponse(CamelModel):
    request_id: str
    expires_in_minutes: int = Field(ge=1)


class ResetPasswordRequest(CamelModel):
    token: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=6, max_length=255)


class TokenResponse(CamelModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int = Field(ge=1)
    refresh_token: str
    user: User
