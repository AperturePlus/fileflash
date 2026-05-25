from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_files_service, get_settings_dep, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.core.security import create_admin_file_preview_token
from fileflash.core.settings import Settings
from fileflash.routers.admin_files import router as admin_router
from fileflash.schemas.admin.files import RescanResponse
from fileflash.services.admin.files import AdminFileStreamResult


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

    async def get_file_detail(self, *, file_id):  # noqa: ANN001
        return SimpleNamespace(
            model_dump=lambda **_: {
                "id": str(file_id),
                "objectId": "42",
                "name": "demo.txt",
                "size": 12,
                "mimeType": "text/plain",
                "hash": "abc123",
                "virusStatus": "clean",
                "isShared": False,
                "ownerName": "owner",
                "uploadCount": 2,
                "ownerCount": 1,
                "scannedAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
                "createdAt": "2026-01-01T00:00:00Z",
                "objectHash": "abc123full",
                "hashAlgorithm": "sha256",
                "storageStatus": "active",
                "latestScan": {
                    "scanType": "virus",
                    "scanResult": "clean",
                    "virusStatus": "clean",
                    "scannedAt": "2026-01-01T00:00:00Z",
                    "details": {},
                },
                "owners": [
                    {
                        "userId": "1",
                        "username": "owner",
                        "email": "owner@example.com",
                        "fileCount": 2,
                        "firstUploadedAt": "2026-01-01T00:00:00Z",
                        "lastUploadedAt": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        )

    async def get_preview_stream(self, *, file_id, range_header):  # noqa: ANN001
        _ = file_id

        async def _stream(content: bytes) -> AsyncIterator[bytes]:
            yield content

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": 'inline; filename="demo.txt"',
        }
        if range_header:
            headers["Content-Length"] = "4"
            headers["Content-Range"] = "bytes 0-3/12"
            return AdminFileStreamResult(
                stream=_stream(b"prev"),
                filename="demo.txt",
                content_type="text/plain",
                status_code=206,
                headers=headers,
            )

        headers["Content-Length"] = "12"
        return AdminFileStreamResult(
            stream=_stream(b"preview-bytes"),
            filename="demo.txt",
            content_type="text/plain",
            status_code=200,
            headers=headers,
        )

    async def request_rescan(self, *, file_id, requested_by):  # noqa: ANN001
        _ = requested_by
        return RescanResponse(
            file_id=str(file_id),
            virus_status="pending",
            scanned_at=datetime.now(UTC),
        )


def _client(*, admin: bool = True, settings: Settings | None = None) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_files_service] = lambda: StubService()

    def _admin_override():
        if not admin:
            raise ApiError(status_code=403, code=403, message="Admin access required")
        return SimpleNamespace(user_id=99)

    resolved_settings = settings or Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )

    app.dependency_overrides[require_admin] = _admin_override
    app.dependency_overrides[get_settings_dep] = lambda: resolved_settings
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


def test_get_file_detail_returns_owner_and_upload_counts() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/files/7")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["uploadCount"] == 2
    assert data["ownerCount"] == 1
    assert data["owners"][0]["email"] == "owner@example.com"


def test_preview_route_returns_inline_stream() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/files/7/preview", headers={"Range": "bytes=0-3"})
    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 0-3/12"
    assert resp.content == b"prev"


def test_create_preview_url_returns_admin_stream_url() -> None:
    with _client() as c:
        resp = c.post("/api/v1/admin/files/7/preview-url")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["url"].startswith("http://testserver/api/v1/admin/files/7/preview-stream?token=")
    assert data["expiresAt"]


def test_admin_preview_requires_admin() -> None:
    with _client(admin=False) as c:
        resp = c.get("/api/v1/admin/files/7/preview")
    assert resp.status_code == 403
    assert resp.json()["message"] == "Admin access required"


def test_preview_stream_supports_range_with_valid_token() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_admin_file_preview_token(
        admin_user_id=99,
        file_id=7,
        settings=settings,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    with _client(settings=settings) as c:
        resp = c.get(f"/api/v1/admin/files/7/preview-stream?token={token}", headers={"Range": "bytes=0-3"})

    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 0-3/12"
    assert resp.content == b"prev"


def test_preview_stream_rejects_mismatched_token_file_id() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_admin_file_preview_token(
        admin_user_id=99,
        file_id=8,
        settings=settings,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    with _client(settings=settings) as c:
        resp = c.get(f"/api/v1/admin/files/7/preview-stream?token={token}")

    assert resp.status_code == 403
    assert resp.json()["message"] == "Preview token does not match file"


def test_preview_stream_rejects_expired_token() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_admin_file_preview_token(
        admin_user_id=99,
        file_id=7,
        settings=settings,
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )

    with _client(settings=settings) as c:
        resp = c.get(f"/api/v1/admin/files/7/preview-stream?token={token}")

    assert resp.status_code == 401
    assert resp.json()["message"] == "Invalid or expired preview token"
