from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.deps import get_current_user, get_db
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.recycle import GetRecycleBinQuery
from ..services.recycle_bin import RecycleBinService

router = APIRouter(prefix="/recycle-bin", tags=["recycle-bin"])


def get_recycle_bin_service(db=Depends(get_db)) -> RecycleBinService:  # type: ignore[valid-type]
    return RecycleBinService(db=db)


@router.get("")
async def list_recycle_bin(
    query: GetRecycleBinQuery = Depends(),
    current_user: User = Depends(get_current_user),
    recycle_service: RecycleBinService = Depends(get_recycle_bin_service),
):
    data = await recycle_service.list_items(current_user=current_user, query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Recycle bin fetched successfully")

