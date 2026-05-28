from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fileflash.core.security import (
    create_admin_file_preview_token,
    create_access_token,
    create_file_preview_token,
    create_refresh_token,
    decode_admin_file_preview_token,
    decode_access_token,
    decode_file_preview_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from fileflash.core.settings import Settings


def test_password_hash_and_verify():
    raw_password = "P@ssword123"
    hashed = get_password_hash(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_round_trip():
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_access_token(user_id=42, settings=settings)
    payload = decode_access_token(token=token, settings=settings)
    assert payload["sub"] == "42"
    assert payload["typ"] == "access"
    assert "exp" in payload


def test_file_preview_token_round_trip():
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_file_preview_token(
        user_id=42,
        file_id=99,
        settings=settings,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    payload = decode_file_preview_token(token=token, settings=settings)
    assert payload["sub"] == "42"
    assert payload["fileId"] == "99"
    assert payload["scope"] == "file.preview"
    assert payload["typ"] == "file_preview"


def test_admin_file_preview_token_round_trip():
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_admin_file_preview_token(
        admin_user_id=7,
        file_id=99,
        settings=settings,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    payload = decode_admin_file_preview_token(token=token, settings=settings)
    assert payload["sub"] == "7"
    assert payload["fileId"] == "99"
    assert payload["scope"] == "admin.file.preview"
    assert payload["typ"] == "admin_file_preview"


def test_refresh_token_hash_is_deterministic():
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    refresh_token = create_refresh_token()
    token_hash_1 = hash_token(refresh_token, settings)
    token_hash_2 = hash_token(refresh_token, settings)
    assert token_hash_1 == token_hash_2
    assert len(token_hash_1) == 64


def test_refresh_token_hash_changes_with_different_secret():
    token = "same-token-value"
    settings_a = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        TOKEN_HASH_SECRET="token-secret-A",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    settings_b = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        TOKEN_HASH_SECRET="token-secret-B",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )

    hash_a = hash_token(token, settings_a)
    hash_b = hash_token(token, settings_b)

    assert hash_a != hash_b
