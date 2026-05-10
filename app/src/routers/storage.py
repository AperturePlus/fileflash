from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_current_user, get_db
from ..core.errors import api_success
from ..models.tables_identity import User
from ..services.storage_summary import StorageService

router = APIRouter(prefix="/storage", tags=["storage"])


def get_storage_service(db=Depends(get_db)) -> StorageService:  # type: ignore[valid-type]
    return StorageService(db=db)


@router.get("/summary")
async def get_storage_summary(
    current_user: User = Depends(get_current_user),
    storage_service: StorageService = Depends(get_storage_service),
):
    stats = await storage_service.get_summary(current_user=current_user)
    return api_success(data=stats.model_dump(by_alias=True), message="Storage summary fetched successfully")

