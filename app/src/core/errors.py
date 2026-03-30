from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def build_api_payload(*, success: bool, code: int, message: str, data: Any = None) -> dict[str, Any]:
    return {
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def api_success(data: Any = None, *, code: int = 200, message: str = "OK", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_api_payload(success=True, code=code, message=message, data=data),
    )


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=build_api_payload(success=False, code=exc.code, message=exc.message, data=None),
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    message = str(exc.detail) if exc.detail else "HTTP error"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_api_payload(success=False, code=exc.status_code, message=message, data=None),
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=build_api_payload(
            success=False,
            code=422,
            message="Validation failed",
            data={"errors": exc.errors()},
        ),
    )

