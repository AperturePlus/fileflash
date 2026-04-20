from fastapi import APIRouter

from .auth import router as auth_router
from .me import router as me_router
from .shares import router as shares_router
from .uploads import router as uploads_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(shares_router)
api_router.include_router(uploads_router)

__all__ = ["api_router"]
