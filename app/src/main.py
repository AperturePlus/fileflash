from __future__ import annotations

from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core import api_error_handler, get_settings, http_exception_handler, validation_exception_handler
from .core.openapi import configure_openapi
from .core.deps import get_object_storage, get_rate_limiter
from .core.errors import ApiError, api_success
from .core.agent_middleware import AgentAccessLogMiddleware
from .core.middleware import EmailVerificationGateMiddleware
from .core.settings import _settings_env_files
from .db.engine import verify_database_connection
from .db.session import SessionLocal
from .services.agent.startup import log_agent_database_readiness
from .routers import api_router
from .s3 import ObjectStorageError
from .services.agent.guard import AGENT_API_BUILD
from .services.dev_seed import initialize_dev_accounts

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("src").setLevel(logging.INFO)
logging.getLogger("src.routers.agent").setLevel(logging.INFO)
logging.getLogger("src.services.agent").setLevel(logging.INFO)
logging.getLogger("src.agents").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await verify_database_connection()
    try:
        await get_object_storage().ensure_bucket()
    except ObjectStorageError:
        logger.exception("Object storage startup check failed")
        raise
    await initialize_dev_accounts(settings=settings, reset_password=False, auto_run=True)
    env_files = _settings_env_files()
    logger.info(
        "Startup config: build=2026-05-18-r2 env_files=%s APP_ENV=%s agent_enabled=%s "
        "agent_api_active=%s agent_inline=%s redis=%s docs=http://127.0.0.1:8000/docs",
        env_files,
        settings.app_env,
        settings.agent_enabled,
        settings.agent_is_api_active,
        settings.agent_inline_processing,
        bool(settings.redis_url),
    )
    async with SessionLocal() as db:
        await log_agent_database_readiness(db)
    yield
    await get_rate_limiter().close()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
configure_openapi(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(EmailVerificationGateMiddleware, settings=settings)
app.add_middleware(AgentAccessLogMiddleware, settings=settings)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/health")
async def health():
    return api_success(data={"status": "ok"}, message="Healthy")


@app.get(f"{settings.api_v1_prefix}/agent/ping")
async def agent_ping():
    """No auth. Use to verify Apifox/Swagger hit THIS uvicorn process (build id must match startup log)."""
    return api_success(
        data={
            "build": AGENT_API_BUILD,
            "agentEnabled": settings.agent_enabled,
            "appEnv": settings.app_env,
        },
        message="Agent ping",
    )


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
