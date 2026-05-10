from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_current_user
from ..core.errors import ApiError, api_success
from ..db.deps import get_db
from ..models import BackgroundJob
from ..models.tables_identity import User
from ..schemas.job import to_background_job_response

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed = int(job_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid jobId") from exc

    job = await db.scalar(
        select(BackgroundJob).where(
            and_(
                BackgroundJob.job_id == parsed,
                BackgroundJob.requested_by == current_user.user_id,
            )
        )
    )
    if job is None:
        raise ApiError(status_code=404, code=404, message="Job not found")

    return api_success(
        data=to_background_job_response(job).model_dump(by_alias=True),
        message="Job fetched successfully",
    )

