from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_files_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_files import router as admin_router
from fileflash.schemas.admin.files import RescanResponse


class StubService:
    async def list_files(self, *, query):  # noqa: ANN001
        return SimpleNamespace(
            model_dump=lambda **_: {
                "items": [],
                "pagination": {
                    "totalItems": 0,
                    "totalPages": 1,
                    "perPage": query.per_page,
                    "currentPage": query.page,
                    "hasPrev": False,
                    "hasNext": False,
                },
            }
        )

    async def request_rescan(self, *, file_id, requested_by):  # noqa: ANN001
        _ = requested_by
        return RescanResponse(
            file_id=str(file_id),
            virus_status="pending",
            scanned_at=datetime.now(UTC),
        )


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_files_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=99)
    return TestClient(app)


def test_list_files_returns_empty() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/files")
    assert resp.status_code == 200


def test_rescan_returns_pending() -> None:
    with _client() as c:
        resp = c.post("/api/v1/admin/files/7/rescan")
    assert resp.status_code == 200
    assert resp.json()["data"]["virusStatus"] == "pending"
