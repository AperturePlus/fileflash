from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from ..core.deps import (
    get_client_ip,
    get_current_user,
    get_download_rate_limit_service,
    get_share_service,
    get_user_agent,
    require_verified_user,
)
from ..core.errors import api_success
from ..core.http_headers import build_content_disposition
from ..models.tables_identity import User
from ..schemas.share import (
    AccessShareRequest,
    CreateShareRequest,
    GetSharesQuery,
    SaveShareRequest,
    UpdateShareSettingsRequest,
)
from ..services.download_rate_limit import DownloadRateLimitService
from ..services.share import ShareService

router = APIRouter(prefix="/shares", tags=["shares"])


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None


def _extract_share_stream(
    value: tuple[object, ...],
) -> tuple[object, str, str, int, dict[str, str] | None]:
    if len(value) == 5:
        stream, filename, content_type, status_code, headers = value
        if isinstance(filename, str) and isinstance(content_type, str) and isinstance(status_code, int) and isinstance(headers, dict):
            return stream, filename, content_type, status_code, headers
    if len(value) == 4:
        stream, filename, content_type, status_code = value
        if isinstance(filename, str) and isinstance(content_type, str) and isinstance(status_code, int):
            return stream, filename, content_type, status_code, None
    if len(value) == 3:
        stream, filename, content_type = value
        if isinstance(filename, str) and isinstance(content_type, str):
            return stream, filename, content_type, 200, None

    from ..core.errors import ApiError

    raise ApiError(status_code=500, code=500, message="Invalid shared stream response")


def _sanitize_stream_headers(
    *,
    headers: dict[str, str] | None,
    filename: str,
    disposition: str,
) -> dict[str, str]:
    fallback_content_disposition = build_content_disposition(filename, disposition=disposition)
    if headers is None:
        return {"Content-Disposition": fallback_content_disposition}

    sanitized: dict[str, str] = {}
    has_content_disposition = False
    for key, value in headers.items():
        key_text = str(key)
        value_text = str(value)
        header_name = key_text.strip().lower()

        if header_name == "content-disposition":
            has_content_disposition = True
            try:
                value_text.encode("latin-1")
                sanitized[key_text] = value_text
            except UnicodeEncodeError:
                sanitized[key_text] = fallback_content_disposition
            continue

        try:
            value_text.encode("latin-1")
        except UnicodeEncodeError:
            continue
        sanitized[key_text] = value_text

    if not has_content_disposition:
        sanitized["Content-Disposition"] = fallback_content_disposition
    return sanitized


def _content_length(headers: dict[str, str] | None) -> int:
    if not headers:
        return 0
    for key, value in headers.items():
        if key.lower() != "content-length":
            continue
        try:
            return max(0, int(value))
        except ValueError:
            return 0
    return 0


@router.post("")
async def create_share(
    payload: CreateShareRequest,
    current_user: User = Depends(require_verified_user),
    share_service: ShareService = Depends(get_share_service),
):
    share = await share_service.create_share(user_id=current_user.user_id, payload=payload)
    return api_success(
        data=share.model_dump(by_alias=True),
        message="Share created",
        code=201,
        status_code=201,
    )


@router.get("")
async def list_shares(
    query: GetSharesQuery = Depends(),
    current_user: User = Depends(get_current_user),
    share_service: ShareService = Depends(get_share_service),
):
    data = await share_service.list_shares(user_id=current_user.user_id, query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Shares fetched successfully")


@router.get("/{share_link}")
async def get_share_details(
    share_link: str,
    share_service: ShareService = Depends(get_share_service),
):
    share = await share_service.get_share_details(share_link=share_link)
    return api_success(data=share.model_dump(by_alias=True), message="Share fetched successfully")


@router.post("/{share_link}/access")
async def access_share(
    share_link: str,
    payload: AccessShareRequest,
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    share_service: ShareService = Depends(get_share_service),
):
    data = await share_service.access_share(
        share_link=share_link,
        password=payload.password,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return api_success(data=data.model_dump(by_alias=True), message="Share accessed successfully")


@router.patch("/{share_link}/settings")
async def update_share_settings(
    share_link: str,
    payload: UpdateShareSettingsRequest,
    current_user: User = Depends(require_verified_user),
    share_service: ShareService = Depends(get_share_service),
):
    share = await share_service.update_settings(
        user_id=current_user.user_id,
        share_link=share_link,
        payload=payload,
    )
    return api_success(data=share.model_dump(by_alias=True), message="Share settings updated successfully")


@router.delete("/{share_link}")
async def delete_share(
    share_link: str,
    current_user: User = Depends(require_verified_user),
    share_service: ShareService = Depends(get_share_service),
):
    share_id, share_code, deleted_at = await share_service.delete_share(user_id=current_user.user_id, share_link=share_link)
    return api_success(
        data={
            "shareId": share_id,
            "shareLink": share_code,
            "deletedAt": deleted_at.isoformat(),
        },
        message="Share deleted successfully",
    )


@router.post("/{share_link}/save")
async def save_share_to_my_space(
    share_link: str,
    payload: SaveShareRequest,
    current_user: User = Depends(require_verified_user),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    share_service: ShareService = Depends(get_share_service),
):
    data = await share_service.save_to_my_space(
        user_id=current_user.user_id,
        share_link=share_link,
        payload=payload,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return api_success(data=data.model_dump(by_alias=True), message="Saved to your space successfully", code=201, status_code=201)


@router.get("/{share_link}/download")
async def download_shared_file(
    share_link: str,
    authorization: str | None = Header(default=None),
    range_header: str | None = Header(default=None, alias="Range"),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    share_service: ShareService = Depends(get_share_service),
    download_limiter: DownloadRateLimitService = Depends(get_download_rate_limit_service),
):
    token = _extract_bearer_token(authorization)
    if not token:
        from ..core.errors import ApiError

        raise ApiError(status_code=401, code=401, message="Missing share access token")

    if hasattr(share_service, "get_shared_file_download_stream_response"):
        raw = await share_service.get_shared_file_download_stream_response(
            share_link=share_link,
            share_access_token=token,
            action="download",
            range_header=range_header,
            ip_address=client_ip,
            user_agent=user_agent,
            rate_limit_check=lambda bytes_count: download_limiter.enforce_share_ip(
                client_ip=client_ip,
                bytes_count=bytes_count,
            ),
        )
    else:
        raw = await share_service.get_shared_file_stream(
            share_link=share_link,
            share_access_token=token,
            action="download",
            ip_address=client_ip,
            user_agent=user_agent,
        )
    stream, filename, content_type, status_code, headers = _extract_share_stream(tuple(raw))
    if not hasattr(share_service, "get_shared_file_download_stream_response"):
        await download_limiter.enforce_share_ip(client_ip=client_ip, bytes_count=_content_length(headers))
    response_headers = _sanitize_stream_headers(headers=headers, filename=filename, disposition="attachment")
    return StreamingResponse(stream, media_type=content_type, headers=response_headers, status_code=status_code)


@router.get("/{share_link}/preview")
async def preview_shared_file(
    share_link: str,
    authorization: str | None = Header(default=None),
    range_header: str | None = Header(default=None, alias="Range"),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    share_service: ShareService = Depends(get_share_service),
    download_limiter: DownloadRateLimitService = Depends(get_download_rate_limit_service),
):
    token = _extract_bearer_token(authorization)
    if not token:
        from ..core.errors import ApiError

        raise ApiError(status_code=401, code=401, message="Missing share access token")

    if hasattr(share_service, "get_shared_file_download_stream_response"):
        raw = await share_service.get_shared_file_download_stream_response(
            share_link=share_link,
            share_access_token=token,
            action="preview",
            range_header=range_header,
            ip_address=client_ip,
            user_agent=user_agent,
            rate_limit_check=lambda bytes_count: download_limiter.enforce_share_ip(
                client_ip=client_ip,
                bytes_count=bytes_count,
            ),
        )
    else:
        raw = await share_service.get_shared_file_stream(
            share_link=share_link,
            share_access_token=token,
            action="preview",
            ip_address=client_ip,
            user_agent=user_agent,
        )
    stream, filename, content_type, status_code, headers = _extract_share_stream(tuple(raw))
    if not hasattr(share_service, "get_shared_file_download_stream_response"):
        await download_limiter.enforce_share_ip(client_ip=client_ip, bytes_count=_content_length(headers))
    response_headers = _sanitize_stream_headers(headers=headers, filename=filename, disposition="inline")
    return StreamingResponse(stream, media_type=content_type, headers=response_headers, status_code=status_code)

