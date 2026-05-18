from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.deps import get_client_ip, get_share_service, get_user_agent
from src.routers.shares import router as shares_router


class StubShareService:
    async def get_shared_file_stream(
        self,
        *,
        share_link: str,  # noqa: ARG002
        share_access_token: str,  # noqa: ARG002
        action: str,  # noqa: ARG002
        ip_address: str,  # noqa: ARG002
        user_agent: str | None,  # noqa: ARG002
    ) -> tuple[AsyncIterator[bytes], str, str]:
        async def _stream() -> AsyncIterator[bytes]:
            yield b"data"

        return _stream(), "测试文档.pdf", "application/pdf"


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(shares_router, prefix="/api/v1")
    app.dependency_overrides[get_share_service] = lambda: StubShareService()
    app.dependency_overrides[get_client_ip] = lambda: "127.0.0.1"
    app.dependency_overrides[get_user_agent] = lambda: "pytest"
    return TestClient(app)


def test_shared_download_handles_unicode_filename_header() -> None:
    with _build_client() as client:
        response = client.get(
            "/api/v1/shares/ABCD/download",
            headers={"Authorization": "Bearer test-share-token"},
        )

    assert response.status_code == 200
    header = response.headers["content-disposition"]
    assert 'filename*=UTF-8\'\'' in header
    header.encode("latin-1")
    assert response.content == b"data"


def test_shared_preview_handles_unicode_filename_header() -> None:
    with _build_client() as client:
        response = client.get(
            "/api/v1/shares/ABCD/preview",
            headers={"Authorization": "Bearer test-share-token"},
        )

    assert response.status_code == 200
    header = response.headers["content-disposition"]
    assert header.startswith("inline;")
    assert 'filename*=UTF-8\'\'' in header
    header.encode("latin-1")
    assert response.content == b"data"

