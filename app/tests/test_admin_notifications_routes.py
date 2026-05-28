from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_notifications_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_notifications import router as n_router
from fileflash.schemas.admin.notifications import BroadcastResponse


class StubService:
    async def list_notifications(self, *, query):  # noqa: ANN001
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

    async def broadcast(self, *, payload, sender_id):  # noqa: ANN001
        _ = payload, sender_id
        return BroadcastResponse(
            broadcast_id="b1",
            recipient_count=2,
            sent_at=datetime.now(UTC),
        )

    async def archive(self, *, notification_id):  # noqa: ANN001
        _ = notification_id
        return None


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(n_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_notifications_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_list() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/notifications")
    assert resp.status_code == 200


def test_broadcast() -> None:
    with _client() as c:
        resp = c.post(
            "/api/v1/admin/notifications/broadcast",
            json={"message": "hello", "type": "system"},
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["broadcastId"] == "b1"


def test_archive() -> None:
    with _client() as c:
        resp = c.delete("/api/v1/admin/notifications/9")
    assert resp.status_code == 200
