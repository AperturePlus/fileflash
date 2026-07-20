from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core import (
    api_error_handler,
    get_settings,
    http_exception_handler,
    validation_exception_handler,
)
from .core.deps import get_object_storage, get_rate_limiter
from .core.errors import ApiError, api_success
from .core.middleware import EmailVerificationGateMiddleware
from .db.engine import verify_database_connection, verify_schema_compatibility
from .routers import api_router
from .s3 import ObjectStorageError
from .services.dev_seed import initialize_dev_accounts

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.assert_runtime_security()
    mail_issues = list(settings.mail_configuration_issues)
    logger.info(
        "Mail delivery readiness: configured=%s, issues=%s",
        settings.is_mail_configured,
        mail_issues,
    )
    await verify_database_connection()
    await verify_schema_compatibility()
    try:
        await get_object_storage().ensure_bucket()
    except ObjectStorageError:
        logger.exception("Object storage startup check failed")
        raise
    await initialize_dev_accounts(settings=settings, reset_password=False, auto_run=True)
    yield
    await get_rate_limiter().close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(EmailVerificationGateMiddleware, settings=settings)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/health")
async def health():
    return api_success(data={"status": "ok"}, message="Healthy")


def main() -> None:
    uvicorn.run("fileflash.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
