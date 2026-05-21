from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import CamelModel


class SystemHealth(CamelModel):
    platform_targets: list[str]
    max_concurrent_uploads: int = Field(ge=0)
    active_upload_sessions: int = Field(ge=0)
    virus_scan_enabled: bool
    thumbnail_generation_enabled: bool
    registration_mail_enabled: bool
    hash_computation_enabled: bool
    last_updated_at: datetime


class RateLimitRule(CamelModel):
    rule_id: str
    scope: str
    window_seconds: int = Field(ge=1)
    limit: int = Field(ge=1)
    current_usage: int = Field(ge=0)
    blocked_requests: int = Field(ge=0)


class RateLimitStatus(CamelModel):
    rules: list[RateLimitRule]
    evaluated_at: datetime
