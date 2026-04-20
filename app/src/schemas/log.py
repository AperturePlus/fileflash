from __future__ import annotations

from datetime import datetime

from .common import CamelModel, PageQuery


class LogItem(CamelModel):
    id: str
    operation: str
    operation_name: str
    details: dict[str, str | int]
    ip_address: str
    performed_at: datetime


class FilterSummary(CamelModel):
    operation: str | None = None
    date_range: str | None = None
    matched_records: int


class LogsList(CamelModel):
    logs: list[LogItem]
    total_count: int
    returned_count: int
    has_more: bool
    filter_summary: FilterSummary


class GetLogsQuery(PageQuery):
    operation: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
