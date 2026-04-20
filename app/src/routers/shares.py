from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from ..core.deps import get_client_ip, get_share_service, get_user_agent, get_current_user, require_verified_user
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.share import (
    AccessShareRequest,
    CreateShareRequest,
    GetSharesQuery,
    SaveShareRequest,
    UpdateShareSettingsRequest,
)
from ..services.share import ShareService

router = APIRouter(prefix="/shares", tags=["shares"])


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None


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
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    share_service: ShareService = Depends(get_share_service),
):
    token = _extract_bearer_token(authorization)
    if not token:
        from ..core.errors import ApiError

        raise ApiError(status_code=401, code=401, message="Missing share access token")

    stream, filename, content_type = await share_service.get_shared_file_stream(
        share_link=share_link,
        share_access_token=token,
        action="download",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(stream, media_type=content_type, headers=headers)


@router.get("/{share_link}/preview")
async def preview_shared_file(
    share_link: str,
    authorization: str | None = Header(default=None),
    client_ip: str = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    share_service: ShareService = Depends(get_share_service),
):
    token = _extract_bearer_token(authorization)
    if not token:
        from ..core.errors import ApiError

        raise ApiError(status_code=401, code=401, message="Missing share access token")

    stream, filename, content_type = await share_service.get_shared_file_stream(
        share_link=share_link,
        share_access_token=token,
        action="preview",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(stream, media_type=content_type, headers=headers)

