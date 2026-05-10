from fastapi import APIRouter

from .auth import router as auth_router
from .files import router as files_router
from .folders import router as folders_router
from .jobs import router as jobs_router
from .me import router as me_router
from .recycle import router as recycle_router
from .shares import router as shares_router
from .uploads import router as uploads_router
from .agent_skills import router as agent_skills_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(files_router)
api_router.include_router(folders_router)
api_router.include_router(jobs_router)
api_router.include_router(me_router)
api_router.include_router(recycle_router)
api_router.include_router(shares_router)
api_router.include_router(uploads_router)
api_router.include_router(agent_skills_router)

__all__ = ["api_router"]
