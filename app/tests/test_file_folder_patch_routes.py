from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import (
    get_current_user,
    get_file_service,
    get_folder_service,
    get_settings_dep,
)
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.core.security import create_file_preview_token
from fileflash.core.settings import Settings
from fileflash.models.tables_identity import User
from fileflash.routers.files import router as files_router
from fileflash.routers.folders import router as folders_router
from fileflash.schemas.file import FileDetails, FolderItem, RenameFileRequest
from fileflash.services.file import DownloadStreamResult


def _make_file_details(*, name: str, is_starred: bool) -> FileDetails:
    now = datetime.now(UTC)
    return FileDetails(
        id="1",
        name=name,
        size=256,
        mime_type="text/plain",
        owner_name="owner",
        updated_at=now,
        created_at=now,
        folder_id="10",
        permission="owner",
        is_starred=is_starred,
        status=True,
    )


def _make_folder_item(*, is_starred: bool) -> FolderItem:
    now = datetime.now(UTC)
    return FolderItem(
        id="10",
        name="Docs",
        size=0,
        owner_name="owner",
        updated_at=now,
        created_at=now,
        parent_folder_id="1",
        permission="owner",
        is_starred=is_starred,
    )


class StubFileService:
    async def get_file(self, *, user_id: int, file_id: int) -> FileDetails:  # noqa: ARG002
        return _make_file_details(name="demo.txt", is_starred=False)

    async def rename_file(self, *, user_id: int, file_id: str, payload: RenameFileRequest) -> FileDetails:  # noqa: ARG002
        return _make_file_details(name=payload.file_name, is_starred=False)

    async def toggle_file_star(self, *, user_id: int, file_id: str, is_starred: bool) -> FileDetails:  # noqa: ARG002
        return _make_file_details(name="demo.txt", is_starred=is_starred)

    async def get_preview_stream(
        self,
        *,
        user_id: int,  # noqa: ARG002
        file_id: str,  # noqa: ARG002
        range_header: str | None,
    ) -> DownloadStreamResult:
        async def _stream(content: bytes) -> AsyncIterator[bytes]:
            yield content

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": 'inline; filename="demo.txt"',
        }
        if range_header:
            headers["Content-Length"] = "4"
            headers["Content-Range"] = "bytes 0-3/12"
            return DownloadStreamResult(
                stream=_stream(b"prev"),
                filename="demo.txt",
                content_type="text/plain",
                status_code=206,
                headers=headers,
            )

        headers["Content-Length"] = "12"
        return DownloadStreamResult(
            stream=_stream(b"preview-bytes"),
            filename="demo.txt",
            content_type="text/plain",
            status_code=200,
            headers=headers,
        )


class StubFolderService:
    async def toggle_folder_star(self, *, user_id: int, folder_id: str, is_starred: bool) -> FolderItem:  # noqa: ARG002
        return _make_folder_item(is_starred=is_starred)


def _build_client(*, authenticated: bool = True, settings: Settings | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(folders_router, prefix="/api/v1")
    app.add_exception_handler(ApiError, api_error_handler)

    async def _current_user_override() -> User:
        if not authenticated:
            raise ApiError(status_code=401, code=401, message="Missing authorization token")
        return User(user_id=1, username="owner", email="owner@example.com", password_hash="hash")

    resolved_settings = settings or Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )

    app.dependency_overrides[get_current_user] = _current_user_override
    app.dependency_overrides[get_file_service] = lambda: StubFileService()
    app.dependency_overrides[get_folder_service] = lambda: StubFolderService()
    app.dependency_overrides[get_settings_dep] = lambda: resolved_settings
    return TestClient(app)


def test_patch_file_rename_route_returns_success() -> None:
    with _build_client() as client:
        response = client.patch("/api/v1/files/1", json={"fileName": "report.txt"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["name"] == "report.txt"


def test_patch_file_star_route_returns_success() -> None:
    with _build_client() as client:
        response = client.patch("/api/v1/files/1/star", json={"isStarred": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["isStarred"] is True


def test_patch_folder_star_route_returns_success() -> None:
    with _build_client() as client:
        response = client.patch("/api/v1/folders/10/star", json={"isStarred": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["isStarred"] is True


def test_get_file_preview_route_returns_stream() -> None:
    with _build_client() as client:
        response = client.get("/api/v1/files/1/preview", headers={"Range": "bytes=0-3"})
    assert response.status_code == 206
    assert response.headers["content-disposition"] == 'inline; filename="demo.txt"'
    assert response.headers["content-range"] == "bytes 0-3/12"
    assert response.headers["content-type"].startswith("text/plain")
    assert response.content == b"prev"


def test_create_file_preview_url_route_returns_signed_stream_url() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    with _build_client(settings=settings) as client:
        response = client.post("/api/v1/files/1/preview-url")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["url"].startswith("http://testserver/api/v1/files/1/preview-stream?token=")
    assert payload["data"]["expiresAt"]


def test_create_file_preview_url_route_requires_authentication() -> None:
    with _build_client(authenticated=False) as client:
        response = client.post("/api/v1/files/1/preview-url")

    assert response.status_code == 401
    assert response.json()["message"] == "Missing authorization token"


def test_get_file_preview_stream_route_supports_range_with_valid_token() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_file_preview_token(
        user_id=1,
        file_id=1,
        settings=settings,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    with _build_client(settings=settings) as client:
        response = client.get(
            f"/api/v1/files/1/preview-stream?token={token}",
            headers={"Range": "bytes=0-3"},
        )

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-3/12"
    assert response.headers["content-length"] == "4"
    assert response.content == b"prev"


def test_get_file_preview_stream_route_rejects_mismatched_token_file_id() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_file_preview_token(
        user_id=1,
        file_id=2,
        settings=settings,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    with _build_client(settings=settings) as client:
        response = client.get(f"/api/v1/files/1/preview-stream?token={token}")

    assert response.status_code == 403
    assert response.json()["message"] == "Preview token does not match file"


def test_get_file_preview_stream_route_rejects_expired_token() -> None:
    settings = Settings(
        JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        FF_DB_URI="postgresql://u:p@localhost:5432/db",
    )
    token = create_file_preview_token(
        user_id=1,
        file_id=1,
        settings=settings,
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )

    with _build_client(settings=settings) as client:
        response = client.get(f"/api/v1/files/1/preview-stream?token={token}")

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid or expired preview token"
