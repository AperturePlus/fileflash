from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_current_user, get_db
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.file import CreateFolderRequest, FolderContentsQuery, FolderPathResponse, PathItem
from ..services.folders import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


def get_folder_service(db=Depends(get_db)) -> FolderService:  # type: ignore[valid-type]
    return FolderService(db=db)

@router.post("")
async def create_folder(
    payload: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    folder = await folder_service.create_folder(current_user=current_user, payload=payload)
    return api_success(data=folder.model_dump(by_alias=True), message="Folder created successfully", code=201, status_code=201)


@router.get("/root")
async def get_root_contents(
    query: FolderContentsQuery = Depends(),
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    root_id = await folder_service.get_or_create_root_folder_id(owner_id=current_user.user_id)
    data = await folder_service.list_folder_contents(current_user=current_user, folder_id=root_id, query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Folder contents fetched successfully")


@router.get("/{folder_id}")
async def get_folder_contents(
    folder_id: int,
    query: FolderContentsQuery = Depends(),
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    data = await folder_service.list_folder_contents(current_user=current_user, folder_id=folder_id, query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Folder contents fetched successfully")


@router.get("/{folder_id}/path")
async def get_folder_path(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    # Minimal breadcrumb path. For root, return a single item.
    if folder_id == "root":
        root_id = await folder_service.get_or_create_root_folder_id(owner_id=current_user.user_id)
        return api_success(
            data=FolderPathResponse(
                full_path="/My Files",
                path_items=[PathItem(folder_id=None, name="My Files")],
            ).model_dump(by_alias=True),
            message="Folder path fetched successfully",
        )

    # For non-root, build a simple path chain up to root.
    path = await folder_service.get_folder_path(current_user_id=current_user.user_id, folder_id=int(folder_id))
    return api_success(data=path.model_dump(by_alias=True), message="Folder path fetched successfully")

