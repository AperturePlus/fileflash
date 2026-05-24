from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_admin_notifications_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.admin.notifications import BroadcastRequest, ListAdminNotificationsQuery
from ..services.admin.notifications import AdminNotificationsService

router = APIRouter(prefix="/admin/notifications", tags=["admin"])


@router.get("")
async def list_admin_notifications(
    query: ListAdminNotificationsQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminNotificationsService = Depends(get_admin_notifications_service),
):
    data = await service.list_notifications(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Notifications fetched")


@router.post("/broadcast")
async def broadcast_notification(
    payload: BroadcastRequest,
    admin: User = Depends(require_admin),
    service: AdminNotificationsService = Depends(get_admin_notifications_service),
):
    result = await service.broadcast(payload=payload, sender_id=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Broadcast sent")


@router.delete("/{notification_id}")
async def archive_admin_notification(
    notification_id: int,
    _: User = Depends(require_admin),
    service: AdminNotificationsService = Depends(get_admin_notifications_service),
):
    await service.archive(notification_id=notification_id)
    return api_success(
        data={"notificationId": str(notification_id), "status": "archived"},
        message="Notification archived",
    )


__all__ = ["router"]
