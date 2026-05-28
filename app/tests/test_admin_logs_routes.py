from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_logs_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_logs import router as logs_router
from fileflash.schemas.admin.logs import AdminLogsResponse


class StubService:
    async def list_logs(self, *, query):  # noqa: ANN001
        return AdminLogsResponse(
            logs=[],
            pagination={
                "totalItems": 0,
                "totalPages": 1,
                "perPage": query.per_page,
                "currentPage": query.page,
                "hasPrev": False,
                "hasNext": False,
            },
        )


def test_admin_can_list_logs() -> None:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(logs_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_logs_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    with TestClient(app) as c:
        resp = c.get("/api/v1/admin/logs")
    assert resp.status_code == 200
    assert resp.json()["data"]["logs"] == []
