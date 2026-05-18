from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..services.agent.guard import AGENT_API_BUILD
from .settings import Settings

logger = logging.getLogger(__name__)


class AgentAccessLogMiddleware(BaseHTTPMiddleware):
    """Always log /agent/* HTTP traffic (before route handlers)."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._prefix = f"{settings.api_v1_prefix}/agent"

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path.startswith(self._prefix):
            auth = request.headers.get("authorization")
            logger.info(
                "agent.access incoming method=%s path=%s has_auth=%s",
                request.method,
                path,
                bool(auth),
            )
        response = await call_next(request)
        if path.startswith(self._prefix):
            response.headers["X-FileFlash-Build"] = AGENT_API_BUILD
            logger.info(
                "agent.access outgoing method=%s path=%s status=%s build=%s",
                request.method,
                path,
                response.status_code,
                AGENT_API_BUILD,
            )
        return response
