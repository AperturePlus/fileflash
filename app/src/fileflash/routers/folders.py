from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..core.deps import get_current_user, get_folder_service
from ..core.errors import ApiError, api_success
from ..models.tables_identity import User
from ..schemas.file import (
    CreateFolderRequest,
    GetFolderContentsQuery,
    MoveFolderRequest,
    RenameFolderRequest,
    ToggleFolderStarRequest,
)
from ..services.folder import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("")
async def list_folders(
    parent_id: str | None = Query(None, alias="parentId"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200, alias="perPage"),
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    result = await folder_service.list_folders(
        user_id=current_user.user_id,
        parent_id=parent_id,
        page=page,
        per_page=per_page,
    )
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/root")
async def get_root_contents(
    sort: str | None = None,
    order: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200, alias="perPage"),
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    query = GetFolderContentsQuery(
        folder_id="0",
        sort=sort,
        order=order,
        search=search,
        page=page,
        per_page=per_page,
    )
    result = await folder_service.get_root_contents(user_id=current_user.user_id, query=query)
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/{folder_id}")
async def get_folder_contents(
    folder_id: str,
    sort: str | None = None,
    order: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200, alias="perPage"),
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    query = GetFolderContentsQuery(
        folder_id=folder_id,
        sort=sort,
        order=order,
        search=search,
        page=page,
        per_page=per_page,
    )
    result = await folder_service.get_folder_contents(user_id=current_user.user_id, query=query)
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/{folder_id}/path")
async def get_folder_path(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    if folder_id == "root":
        root_id = await folder_service.get_root_folder_id(user_id=current_user.user_id)
        result = await folder_service.get_folder_path(user_id=current_user.user_id, folder_id=root_id)
        return api_success(data=result.model_dump(by_alias=True))

    try:
        fid = int(folder_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid folderId") from exc

    result = await folder_service.get_folder_path(user_id=current_user.user_id, folder_id=fid)
    return api_success(data=result.model_dump(by_alias=True))


@router.get("/{folder_id}/size")
async def get_folder_size(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    try:
        fid = int(folder_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid folderId") from exc

    result = await folder_service.get_folder_size(user_id=current_user.user_id, folder_id=fid)
    return api_success(data=result.model_dump(by_alias=True))


@router.post("")
async def create_folder(
    payload: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    result = await folder_service.create_folder(user_id=current_user.user_id, payload=payload)
    return api_success(
        data=result.model_dump(by_alias=True),
        message="Folder created successfully",
        code=201,
        status_code=201,
    )


@router.patch("/{folder_id}")
async def rename_folder(
    folder_id: str,
    payload: RenameFolderRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    result = await folder_service.rename_folder(user_id=current_user.user_id, folder_id=folder_id, payload=payload)
    return api_success(data=result.model_dump(by_alias=True), message="Folder renamed successfully")


@router.patch("/{folder_id}/move")
async def move_folder(
    folder_id: str,
    payload: MoveFolderRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    result = await folder_service.move_folder(user_id=current_user.user_id, folder_id=folder_id, payload=payload)
    return api_success(data=result.model_dump(by_alias=True), message="Folder moved successfully")


@router.patch("/{folder_id}/star")
async def toggle_folder_star(
    folder_id: str,
    payload: ToggleFolderStarRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    result = await folder_service.toggle_folder_star(
        user_id=current_user.user_id,
        folder_id=folder_id,
        is_starred=payload.is_starred,
    )
    return api_success(data=result.model_dump(by_alias=True), message="Folder star updated successfully")


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    result = await folder_service.delete_folder(user_id=current_user.user_id, folder_id=folder_id)
    return api_success(
        data=result.model_dump(by_alias=True),
        message="Folder moved to recycle bin successfully",
    )
