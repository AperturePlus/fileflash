from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


class ApiResponse(CamelModel, Generic[T]):
    success: bool = True
    code: int = 200
    message: str = "OK"
    data: T | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaginationMeta(CamelModel):
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=1)
    per_page: int = Field(ge=1)
    current_page: int = Field(ge=1)
    has_prev: bool
    has_next: bool


class PaginatedData(CamelModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


class PageQuery(CamelModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=200)
