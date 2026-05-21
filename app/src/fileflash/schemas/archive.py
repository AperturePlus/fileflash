from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import CamelModel

ArchiveConflictStrategy = Literal["rename", "overwrite", "skip"]


class ArchiveExtractRequest(CamelModel):
    target_folder_id: str = Field(min_length=1, max_length=64)
    create_subfolder: bool = True
    subfolder_name: str | None = Field(default=None, min_length=1, max_length=255)
    conflict_strategy: ArchiveConflictStrategy | None = None

