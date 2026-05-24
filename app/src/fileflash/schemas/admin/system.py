from __future__ import annotations

from datetime import datetime

from ..common import CamelModel


class SystemHealth(CamelModel):
    platform_targets: list[str]
    max_concurrent_uploads: int
    active_upload_sessions: int
    virus_scan_enabled: bool
    thumbnail_generation_enabled: bool
    registration_mail_enabled: bool
    hash_computation_enabled: bool
    last_updated_at: datetime


class RateLimitRule(CamelModel):
    rule_id: str
    scope: str
    window_seconds: int
    limit: int
    current_usage: int
    blocked_requests: int


class RateLimitStatus(CamelModel):
    rules: list[RateLimitRule]
    evaluated_at: datetime


__all__ = ["RateLimitRule", "RateLimitStatus", "SystemHealth"]
