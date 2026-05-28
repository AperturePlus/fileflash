from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.settings import Settings
from ...models.enums import UploadTaskStatus
from ...models.tables_storage import UploadTask
from ...schemas.admin.system import RateLimitRule, RateLimitStatus, SystemHealth


class AdminSystemService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def health(self) -> SystemHealth:
        active_uploads = int(
            await self.db.scalar(
                select(func.count(UploadTask.task_id)).where(
                    UploadTask.status.in_([UploadTaskStatus.INIT, UploadTaskStatus.UPLOADING])
                )
            )
            or 0
        )

        platform_targets: list[str] = []
        if self.settings.object_storage_bucket:
            platform_targets.append(f"s3://{self.settings.object_storage_bucket}")
        if self.settings.redis_url:
            platform_targets.append("redis")

        return SystemHealth(
            platform_targets=platform_targets,
            max_concurrent_uploads=getattr(self.settings, "max_concurrent_uploads", 4),
            active_upload_sessions=active_uploads,
            virus_scan_enabled=bool(getattr(self.settings, "virus_scan_enabled", False)),
            thumbnail_generation_enabled=bool(getattr(self.settings, "thumbnail_generation_enabled", True)),
            registration_mail_enabled=bool(self.settings.mail_server and self.settings.mail_from),
            hash_computation_enabled=bool(self.settings.upload_verify_merged_object_hash),
            last_updated_at=datetime.now(UTC),
        )

    async def rate_limit_status(self) -> RateLimitStatus:
        rules = [
            RateLimitRule(
                rule_id="login",
                scope="auth.login",
                window_seconds=self.settings.login_rate_window_seconds,
                limit=self.settings.login_rate_limit,
                current_usage=0,
                blocked_requests=0,
            ),
            RateLimitRule(
                rule_id="register",
                scope="auth.register",
                window_seconds=self.settings.register_rate_window_seconds,
                limit=self.settings.register_rate_limit,
                current_usage=0,
                blocked_requests=0,
            ),
            RateLimitRule(
                rule_id="forgot_password",
                scope="auth.forgot_password",
                window_seconds=self.settings.forgot_password_rate_window_seconds,
                limit=self.settings.forgot_password_rate_limit,
                current_usage=0,
                blocked_requests=0,
            ),
            RateLimitRule(
                rule_id="resend_verification",
                scope="auth.resend_verification",
                window_seconds=self.settings.resend_verification_rate_window_seconds,
                limit=self.settings.resend_verification_rate_limit,
                current_usage=0,
                blocked_requests=0,
            ),
        ]
        return RateLimitStatus(rules=rules, evaluated_at=datetime.now(UTC))


__all__ = ["AdminSystemService"]
