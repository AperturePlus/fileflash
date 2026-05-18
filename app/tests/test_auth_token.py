from __future__ import annotations

from src.core.security import normalize_access_token


def test_normalize_accepts_raw_jwt() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.payload.sig"
    assert normalize_access_token(jwt) == jwt


def test_normalize_accepts_bearer_prefix() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.payload.sig"
    assert normalize_access_token(f"Bearer {jwt}") == jwt


def test_normalize_strips_newlines_from_pasted_token() -> None:
    broken = "eyJhbGciOiJIUzI1NiJ9.\neyJzdWIiOiIxIn0.\nsignature"
    normalized = normalize_access_token(broken)
    assert normalized == "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"


def test_normalize_empty_returns_none() -> None:
    assert normalize_access_token(None) is None
    assert normalize_access_token("   ") is None
    assert normalize_access_token("Bearer") is None
