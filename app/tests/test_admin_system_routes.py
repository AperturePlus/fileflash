from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_system_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_system import router as sys_router
from fileflash.schemas.admin.system import RateLimitRule, RateLimitStatus, SystemHealth


class StubService:
    async def health(self):  # noqa: ANN201
        return SystemHealth(
            platform_targets=["s3://bkt"],
            max_concurrent_uploads=4,
            active_upload_sessions=0,
            virus_scan_enabled=False,
            thumbnail_generation_enabled=True,
            registration_mail_enabled=False,
            hash_computation_enabled=True,
            last_updated_at=datetime.now(UTC),
        )

    async def rate_limit_status(self):  # noqa: ANN201
        return RateLimitStatus(
            rules=[
                RateLimitRule(
                    rule_id="login",
                    scope="auth.login",
                    window_seconds=60,
                    limit=5,
                    current_usage=0,
                    blocked_requests=0,
                )
            ],
            evaluated_at=datetime.now(UTC),
        )


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(sys_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_system_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_health() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/system/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["activeUploadSessions"] == 0


def test_rate_limit() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/system/rate-limit")
    assert resp.status_code == 200
    assert resp.json()["data"]["rules"][0]["scope"] == "auth.login"
