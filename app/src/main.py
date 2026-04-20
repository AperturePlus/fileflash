from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core import api_error_handler, get_settings, http_exception_handler, validation_exception_handler
from .core.deps import get_rate_limiter
from .core.errors import ApiError, api_success
from .core.middleware import EmailVerificationGateMiddleware
from .routers import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
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
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
