from __future__ import annotations

from fastapi import APIRouter

# The agent router is intentionally scaffold-only for this stage.
# Do not include it in api_router until runtime/services are implemented.
router = APIRouter(prefix="/agent", tags=["agent"])

__all__ = ["router"]
