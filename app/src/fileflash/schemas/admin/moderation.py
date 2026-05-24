from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..common import CamelModel, PageQuery

ViolationLevel = Literal["low", "medium", "high"]
ViolationStatus = Literal["pending", "under_review", "resolved"]


class ViolationItem(CamelModel):
    id: str
    file_id: str | None
    file_name: str | None
    type: str
    level: ViolationLevel
    reported_at: datetime
    status: ViolationStatus


class ListViolationsQuery(PageQuery):
    status: ViolationStatus | None = None


class ResolveViolationResponse(CamelModel):
    violation_id: str
    resolved_at: datetime


__all__ = [
    "ListViolationsQuery",
    "ResolveViolationResponse",
    "ViolationItem",
    "ViolationLevel",
    "ViolationStatus",
]
