from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_current_user, get_upload_service
from fileflash.models.tables_identity import User
from fileflash.routers.uploads import router as uploads_router
from fileflash.schemas.file import RecoverableUploadSession, UploadCancelResponse


class StubUploadService:
    async def cancel_upload_session(self, *, user_id: int, upload_id: str) -> UploadCancelResponse:  # noqa: ARG002
        return UploadCancelResponse(
            upload_id=upload_id,
            canceled_at=datetime(2026, 5, 24, 9, 0, 0, tzinfo=UTC),
        )

    async def list_recoverable_sessions(self, *, user_id: int) -> list[RecoverableUploadSession]:  # noqa: ARG002
        return [
            RecoverableUploadSession(
                upload_id="upload-1",
                file_name="demo.mp4",
                file_size=1024,
                uploaded_bytes=512,
                chunk_size=256,
                file_hash="a" * 64,
                mime_type="video/mp4",
                parent_id="root",
                updated_at=datetime(2026, 5, 24, 8, 0, 0, tzinfo=UTC),
                expired_at=datetime(2026, 5, 25, 8, 0, 0, tzinfo=UTC),
                status="uploading",
            )
        ]


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(uploads_router, prefix="/api/v1")

    async def _current_user_override() -> User:
        return User(user_id=1, username="owner", email="owner@example.com", password_hash="hash")

    app.dependency_overrides[get_current_user] = _current_user_override
    app.dependency_overrides[get_upload_service] = lambda: StubUploadService()
    return TestClient(app)


def test_post_upload_cancel_route_returns_success_shell() -> None:
    with _build_client() as client:
        response = client.post("/api/v1/uploads/upload-123/cancel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Upload session canceled"
    assert payload["data"]["uploadId"] == "upload-123"
    assert str(payload["data"]["canceledAt"]).startswith("2026-05-24T09:00:00")


def test_get_recoverable_uploads_route_returns_success_shell() -> None:
    with _build_client() as client:
        response = client.get("/api/v1/uploads/recoverable")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Recoverable upload sessions fetched"
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["uploadId"] == "upload-1"
    assert payload["data"][0]["uploadedBytes"] == 512
