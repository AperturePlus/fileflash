from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from .settings import Settings

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str, settings: Settings) -> str:
    secret = settings.effective_token_hash_secret.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    token_type = payload.get("typ")
    if token_type != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def create_share_access_token(*, share_id: int, settings: Settings, ttl_seconds: int = 30 * 60) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(share_id),
        "typ": "share",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_share_access_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    token_type = payload.get("typ")
    if token_type != "share":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def create_file_preview_token(
    *,
    user_id: int,
    file_id: int,
    settings: Settings,
    expires_at: datetime,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "typ": "file_preview",
        "scope": "file.preview",
        "fileId": str(file_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_file_preview_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    token_type = payload.get("typ")
    scope = payload.get("scope")
    if token_type != "file_preview" or scope != "file.preview":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def create_admin_file_preview_token(
    *,
    admin_user_id: int,
    file_id: int,
    settings: Settings,
    expires_at: datetime,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(admin_user_id),
        "typ": "admin_file_preview",
        "scope": "admin.file.preview",
        "fileId": str(file_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_admin_file_preview_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    token_type = payload.get("typ")
    scope = payload.get("scope")
    if token_type != "admin_file_preview" or scope != "admin.file.preview":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload
