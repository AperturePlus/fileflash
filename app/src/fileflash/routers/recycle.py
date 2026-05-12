from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..core.deps import get_current_user, get_file_service
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.recycle import GetRecycleBinQuery, RestoreRecycleItemRequest
from ..services.file import FileService

router = APIRouter(prefix="/recycle-bin", tags=["recycle-bin"])


@router.get("")
async def list_recycle_bin(
    item_type: str | None = Query(default=None, alias="itemType"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200, alias="perPage"),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    query = GetRecycleBinQuery(item_type=item_type, page=page, per_page=per_page)
    result = await file_service.list_recycle_bin(user_id=current_user.user_id, query=query)
    return api_success(data=result.model_dump(by_alias=True), message="Recycle bin fetched successfully")


@router.post("/{item_id}/restore")
async def restore_recycle_item(
    item_id: str,
    payload: RestoreRecycleItemRequest,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.restore_recycle_item(
        user_id=current_user.user_id,
        item_id=item_id,
        payload=payload,
    )
    return api_success(data=result.model_dump(by_alias=True), message="Item restored successfully")


@router.delete("/{item_id}")
async def permanent_delete_recycle_item(
    item_id: str,
    item_type: str = Query(alias="itemType"),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.permanent_delete_recycle_item(
        user_id=current_user.user_id,
        item_id=item_id,
        item_type=item_type,
    )
    return api_success(data=result.model_dump(by_alias=True), message="Item permanently deleted")


@router.delete("")
async def clear_recycle_bin(
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    result = await file_service.clear_recycle_bin(user_id=current_user.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Recycle bin cleared successfully")
