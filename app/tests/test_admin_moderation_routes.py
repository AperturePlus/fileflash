from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_moderation_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_moderation import router as mod_router
from fileflash.schemas.admin.moderation import ResolveViolationResponse


class StubService:
    async def list_violations(self, *, query):  # noqa: ANN001
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

    async def resolve_case(self, *, case_id, handled_by):  # noqa: ANN001
        _ = handled_by
        return ResolveViolationResponse(violation_id=str(case_id), resolved_at=datetime.now(UTC))


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(mod_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_moderation_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_list_violations() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/violations")
    assert resp.status_code == 200


def test_resolve_violation() -> None:
    with _client() as c:
        resp = c.post("/api/v1/admin/violations/3/resolve")
    assert resp.status_code == 200
    assert resp.json()["data"]["violationId"] == "3"
