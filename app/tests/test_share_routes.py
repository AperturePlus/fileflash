from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import (
    get_client_ip,
    get_download_rate_limit_service,
    get_share_service,
    get_user_agent,
)
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.shares import router as shares_router


class StubShareService:
    async def get_shared_file_download_stream_response(
        self,
        *,
        share_link: str,  # noqa: ARG002
        share_access_token: str,  # noqa: ARG002
        action: str,  # noqa: ARG002
        range_header: str | None,  # noqa: ARG002
        ip_address: str,  # noqa: ARG002
        user_agent: str | None,  # noqa: ARG002
        rate_limit_check=None,  # noqa: ANN001
    ) -> tuple[AsyncIterator[bytes], str, str, int, dict[str, str]]:
        async def _stream() -> AsyncIterator[bytes]:
            yield b"data"

        headers = {
            "Content-Disposition": (
                'inline; filename="测试文档.pdf"; filename*=UTF-8\'\'%E6%B5%8B%E8%AF%95%E6%96%87%E6%A1%A3.pdf'
                if action == "preview"
                else 'attachment; filename="测试文档.pdf"; filename*=UTF-8\'\'%E6%B5%8B%E8%AF%95%E6%96%87%E6%A1%A3.pdf'
            ),
            "Accept-Ranges": "bytes",
            "Content-Length": "4",
        }
        if rate_limit_check is not None:
            await rate_limit_check(4)
        return _stream(), "测试文档.pdf", "application/pdf", 200, headers


class StubDownloadLimiter:
    def __init__(self, *, deny: bool = False) -> None:
        self.deny = deny
        self.calls: list[tuple[str, int]] = []

    async def enforce_share_ip(self, *, client_ip: str, bytes_count: int) -> None:
        self.calls.append((client_ip, bytes_count))
        if self.deny:
            raise ApiError(status_code=429, code=429, message="Download rate limit exceeded")


def _build_client(limiter: StubDownloadLimiter | None = None) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(shares_router, prefix="/api/v1")
    app.dependency_overrides[get_share_service] = lambda: StubShareService()
    app.dependency_overrides[get_client_ip] = lambda: "127.0.0.1"
    app.dependency_overrides[get_user_agent] = lambda: "pytest"
    app.dependency_overrides[get_download_rate_limit_service] = lambda: limiter or StubDownloadLimiter()
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


def test_shared_download_returns_429_when_ip_limited() -> None:
    limiter = StubDownloadLimiter(deny=True)
    with _build_client(limiter) as client:
        response = client.get(
            "/api/v1/shares/ABCD/download",
            headers={"Authorization": "Bearer test-share-token"},
        )

    assert response.status_code == 429
    assert limiter.calls == [("127.0.0.1", 4)]


def test_shared_preview_returns_429_when_ip_limited() -> None:
    limiter = StubDownloadLimiter(deny=True)
    with _build_client(limiter) as client:
        response = client.get(
            "/api/v1/shares/ABCD/preview",
            headers={"Authorization": "Bearer test-share-token"},
        )

    assert response.status_code == 429
    assert limiter.calls == [("127.0.0.1", 4)]
