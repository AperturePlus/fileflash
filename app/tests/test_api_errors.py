from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from starlette.requests import Request

from src.core.errors import ApiError, api_error_handler, api_success


def _new_request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def test_api_success_serializes_datetime_to_iso8601() -> None:
    created_at = datetime(2026, 5, 10, 14, 13, 41, tzinfo=UTC)
    response = api_success(data={"createdAt": created_at}, message="Login successful")

    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["message"] == "Login successful"
    assert payload["data"]["createdAt"] == created_at.isoformat()


def test_api_error_handler_serializes_datetime_to_iso8601() -> None:
    revoked_at = datetime(2026, 5, 10, 15, 0, 0, tzinfo=UTC)
    exc = ApiError(
        status_code=401,
        code=401,
        message="Invalid token",
        data={"revokedAt": revoked_at},
    )
    response = asyncio.run(api_error_handler(_new_request(), exc))

    payload = json.loads(response.body)
    assert response.status_code == 401
    assert payload["success"] is False
    assert payload["message"] == "Invalid token"
    assert payload["data"]["revokedAt"] == revoked_at.isoformat()
