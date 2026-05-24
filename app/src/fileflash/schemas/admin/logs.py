from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from ..common import CamelModel, PageQuery


class LogItem(CamelModel):
    id: str
    user_id: str | None
    operation: str
    operation_name: str
    target_type: str | None
    target_id: str | None
    result: str
    ip_address: str | None
    user_agent: str | None
    performed_at: datetime
    details: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ListAdminLogsQuery(PageQuery):
    user_id: str | None = None
    operation: str | None = None
    result: Literal["success", "failure"] | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None


class AdminLogsResponse(CamelModel):
    logs: list[LogItem]
    pagination: dict[str, Any]


__all__ = ["AdminLogsResponse", "ListAdminLogsQuery", "LogItem"]
