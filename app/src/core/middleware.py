from __future__ import annotations

from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..db.session import SessionLocal
from ..models.tables_identity import User
from .errors import build_api_payload
from .security import decode_access_token
from .settings import Settings


class EmailVerificationGateMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.allow_prefixes = (
            f"{settings.api_v1_prefix}/auth",
            f"{settings.api_v1_prefix}/me/profile",
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(self.settings.api_v1_prefix):
            return await call_next(request)

        if any(path.startswith(prefix) for prefix in self.allow_prefixes):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return await call_next(request)

        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token, self.settings)
            user_id = int(payload["sub"])
        except (InvalidTokenError, KeyError, ValueError):
            return await call_next(request)

        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            if user and not user.email_verified:
                return JSONResponse(
                    status_code=403,
                    content=build_api_payload(
                        success=False,
                        code=403,
                        message="Email verification required",
                        data=None,
                    ),
                )

        return await call_next(request)

