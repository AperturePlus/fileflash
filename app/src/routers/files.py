from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_current_user, get_db
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.file import GetFilesQuery
from ..services.files import FileService

router = APIRouter(prefix="/files", tags=["files"])


def get_file_service(db=Depends(get_db)) -> FileService:  # type: ignore[valid-type]
    return FileService(db=db)


@router.get("")
async def list_files(
    query: GetFilesQuery = Depends(),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    data = await file_service.list_files(current_user=current_user, query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Files fetched successfully")

