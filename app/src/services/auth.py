from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.security import create_access_token, create_refresh_token, get_password_hash, hash_token, verify_password
from ..core.settings import Settings
from ..db.transaction import (
    apply_local_lock_timeout,
    is_retryable_database_error,
    run_with_transaction_retry,
    to_retryable_concurrency_error,
)
from ..models.enums import FileStatus, FolderStatus, FolderType, UiLanguage, UserRole, UserStatus
from ..models.tables_audit_security import Log
from ..models.tables_identity import EmailVerificationToken, PasswordResetToken, User, UserPreference, UserSession
from ..models.tables_storage import File, Folder
from ..schemas.auth import ForgotPasswordResponse, RegisterRequest, RegisterResponseData, TokenResponse
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.user import ActivityItem, BreakdownDetail
from ..schemas.user import User as UserSchema
from ..schemas.user import ChangePasswordRequest, GetActivityLogQuery, StorageStats
from ..schemas.user import UserPreference as UserPreferenceSchema
from ..schemas.user import UpdateProfileRequest, UpdateUserPreferenceRequest, UserProfile
from .messaging import AuthEventPublisher
from .rate_limiter import RedisRateLimiter


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        rate_limiter: RedisRateLimiter,
        event_publisher: AuthEventPublisher,
    ) -> None:
        self.db = db
        self.settings = settings
        self.rate_limiter = rate_limiter
        self.event_publisher = event_publisher

    async def register(
        self,
        payload: RegisterRequest,
        *,
        client_ip: str,
        user_agent: str | None,
    ) -> RegisterResponseData:
        await self._ensure_rate_limit(
            key=f"rl:auth:register:{client_ip}",
            limit=self.settings.register_rate_limit,
            window_seconds=self.settings.register_rate_window_seconds,
            message="Too many registration attempts, please try again later",
        )

        existing_user = await self.db.scalar(
            select(User).where(
                or_(
                    func.lower(User.username) == payload.username.lower(),
                    func.lower(User.email) == payload.email.lower(),
                )
            )
        )
        if existing_user:
            raise ApiError(status_code=409, code=409, message="Username or email already exists")

        now = datetime.now(UTC)
        user = User(
            username=payload.username,
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            email_verified=False,
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        await self.db.flush()

        preference = UserPreference(user_id=user.user_id, ui_language=UiLanguage.ZH_CN)
        self.db.add(preference)

        verification_token = await self._create_email_verification_token(
            user_id=user.user_id,
            now=now,
        )
        await self.db.commit()

        await self.event_publisher.publish(
            "auth.email_verification_requested",
            {
                "userId": str(user.user_id),
                "email": user.email,
                "token": verification_token,
                "expiresInMinutes": self.settings.email_verification_expire_minutes,
                "userAgent": user_agent or "",
            },
        )

        user_schema = self._to_user_schema(user=user, preference=preference)
        return RegisterResponseData(user=user_schema)

    async def login(
        self,
        *,
        username: str,
        password: str,
        client_ip: str,
        user_agent: str | None,
    ) -> tuple[TokenResponse, str]:
        await self._ensure_rate_limit(
            key=f"rl:auth:login:{client_ip}:{username.lower()}",
            limit=self.settings.login_rate_limit,
            window_seconds=self.settings.login_rate_window_seconds,
            message="Too many login attempts, please try again later",
        )

        async def _operation() -> tuple[TokenResponse, str]:
            await apply_local_lock_timeout(self.db)
            user = await self.db.scalar(
                select(User)
                .where(
                    or_(
                        func.lower(User.username) == username.lower(),
                        func.lower(User.email) == username.lower(),
                    )
                )
                .with_for_update()
            )

            if user is None:
                raise ApiError(status_code=401, code=401, message="Invalid username or password")

            now = datetime.now(UTC)
            if user.locked_until and user.locked_until > now:
                raise ApiError(status_code=423, code=423, message="Account is temporarily locked")

            if not verify_password(password, user.password_hash):
                user.failed_login_count += 1
                if user.failed_login_count >= self.settings.max_failed_login_attempts:
                    user.locked_until = now + timedelta(minutes=self.settings.account_lock_minutes)
                    user.failed_login_count = 0
                user.updated_at = now
                await self.db.commit()
                raise ApiError(status_code=401, code=401, message="Invalid username or password")

            if user.status in {UserStatus.DISABLED, UserStatus.LOCKED}:
                raise ApiError(status_code=403, code=403, message="Account is suspended")

            user.failed_login_count = 0
            user.locked_until = None
            user.last_login_at = now
            user.updated_at = now

            preference = await self._get_user_preference(user.user_id)
            access_token = create_access_token(user.user_id, self.settings)
            refresh_token = create_refresh_token()

            self.db.add(
                UserSession(
                    user_id=user.user_id,
                    refresh_token_hash=hash_token(refresh_token),
                    client_type="web",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    expire_at=now + timedelta(days=self.settings.refresh_token_expire_days),
                    last_seen_at=now,
                )
            )
            await self.db.commit()

            token_response = TokenResponse(
                token=access_token,
                token_type="Bearer",
                expires_in=self.settings.access_token_ttl_seconds,
                user=self._to_user_schema(user=user, preference=preference),
            )
            return token_response, refresh_token

        try:
            token_response, refresh_token = await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

        await self.event_publisher.publish(
            "auth.user_logged_in",
            {
                "userId": str(token_response.user.user_id),
                "ipAddress": client_ip,
            },
        )

        return token_response, refresh_token

    async def refresh(
        self,
        *,
        refresh_token: str,
        client_ip: str,
        user_agent: str | None,
    ) -> tuple[TokenResponse, str]:
        async def _operation() -> tuple[TokenResponse, str]:
            now = datetime.now(UTC)
            token_hash = hash_token(refresh_token)
            await apply_local_lock_timeout(self.db)
            session = await self.db.scalar(
                select(UserSession)
                .where(
                    and_(
                        UserSession.refresh_token_hash == token_hash,
                        UserSession.revoked_at.is_(None),
                        UserSession.expire_at > now,
                    )
                )
                .with_for_update()
            )
            if session is None:
                raise ApiError(status_code=401, code=401, message="Invalid or expired refresh token")

            user = await self.db.get(User, session.user_id)
            if user is None:
                raise ApiError(status_code=401, code=401, message="Invalid user session")

            session.revoked_at = now
            session.last_seen_at = now

            next_refresh_token = create_refresh_token()
            next_session = UserSession(
                user_id=user.user_id,
                refresh_token_hash=hash_token(next_refresh_token),
                client_type=session.client_type,
                device_id=session.device_id,
                device_name=session.device_name,
                ip_address=client_ip or session.ip_address,
                user_agent=user_agent or session.user_agent,
                expire_at=now + timedelta(days=self.settings.refresh_token_expire_days),
                last_seen_at=now,
            )
            self.db.add(next_session)

            preference = await self._get_user_preference(user.user_id)
            await self.db.commit()

            token_response = TokenResponse(
                token=create_access_token(user.user_id, self.settings),
                token_type="Bearer",
                expires_in=self.settings.access_token_ttl_seconds,
                user=self._to_user_schema(user=user, preference=preference),
            )
            return token_response, next_refresh_token

        try:
            return await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def logout(self, *, refresh_token: str | None) -> None:
        if not refresh_token:
            return

        now = datetime.now(UTC)
        token_hash = hash_token(refresh_token)
        session = await self.db.scalar(
            select(UserSession).where(
                and_(
                    UserSession.refresh_token_hash == token_hash,
                    UserSession.revoked_at.is_(None),
                )
            )
        )
        if session:
            session.revoked_at = now
            session.last_seen_at = now
            await self.db.commit()

    async def forgot_password(
        self,
        *,
        email: str,
        client_ip: str,
        user_agent: str | None,
    ) -> ForgotPasswordResponse:
        await self._ensure_rate_limit(
            key=f"rl:auth:forgot:{client_ip}:{email.lower()}",
            limit=self.settings.forgot_password_rate_limit,
            window_seconds=self.settings.forgot_password_rate_window_seconds,
            message="Too many password reset requests, please try again later",
        )

        request_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        user = await self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if user:
            reset_token = await self._create_password_reset_token(
                user_id=user.user_id,
                now=now,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            await self.db.commit()
            await self.event_publisher.publish(
                "auth.password_reset_requested",
                {
                    "requestId": request_id,
                    "userId": str(user.user_id),
                    "email": user.email,
                    "token": reset_token,
                    "expiresInMinutes": self.settings.password_reset_expire_minutes,
                },
            )

        return ForgotPasswordResponse(
            request_id=request_id,
            expires_in_minutes=self.settings.password_reset_expire_minutes,
        )

    async def reset_password(self, *, token: str, new_password: str) -> None:
        async def _operation() -> None:
            now = datetime.now(UTC)
            token_hash_value = hash_token(token)
            await apply_local_lock_timeout(self.db)
            reset_record = await self.db.scalar(
                select(PasswordResetToken)
                .where(
                    and_(
                        PasswordResetToken.token_hash == token_hash_value,
                        PasswordResetToken.used_at.is_(None),
                        PasswordResetToken.expire_at > now,
                    )
                )
                .with_for_update()
            )
            if reset_record is None:
                raise ApiError(status_code=400, code=400, message="Invalid or expired reset token")

            user = await self.db.get(User, reset_record.user_id)
            if user is None:
                raise ApiError(status_code=400, code=400, message="Invalid user for reset token")

            user.password_hash = get_password_hash(new_password)
            user.password_changed_at = now
            user.failed_login_count = 0
            user.locked_until = None
            user.updated_at = now
            reset_record.used_at = now

            sessions = await self.db.scalars(
                select(UserSession)
                .where(
                    and_(
                        UserSession.user_id == user.user_id,
                        UserSession.revoked_at.is_(None),
                    )
                )
                .with_for_update()
            )
            for session in sessions:
                session.revoked_at = now
                session.last_seen_at = now

            await self.db.commit()

        try:
            await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def verify_email(self, *, token: str) -> None:
        async def _operation() -> None:
            now = datetime.now(UTC)
            token_hash_value = hash_token(token)
            await apply_local_lock_timeout(self.db)
            verification_record = await self.db.scalar(
                select(EmailVerificationToken)
                .where(
                    and_(
                        EmailVerificationToken.token_hash == token_hash_value,
                        EmailVerificationToken.verified_at.is_(None),
                        EmailVerificationToken.expire_at > now,
                    )
                )
                .with_for_update()
            )
            if verification_record is None:
                raise ApiError(status_code=400, code=400, message="Invalid or expired verification token")

            user = await self.db.get(User, verification_record.user_id)
            if user is None:
                raise ApiError(status_code=400, code=400, message="Invalid verification token")

            verification_record.verified_at = now
            user.email_verified = True
            user.email_verified_at = now
            user.updated_at = now
            await self.db.commit()

        try:
            await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def resend_verification(
        self,
        *,
        user_id: int,
        client_ip: str,
        user_agent: str | None,
    ) -> None:
        await self._ensure_rate_limit(
            key=f"rl:auth:resend:{client_ip}:{user_id}",
            limit=self.settings.resend_verification_rate_limit,
            window_seconds=self.settings.resend_verification_rate_window_seconds,
            message="Too many verification resend attempts, please try again later",
        )

        user = await self.db.get(User, user_id)
        if user is None:
            raise ApiError(status_code=404, code=404, message="User not found")
        if user.email_verified:
            return

        token = await self._create_email_verification_token(
            user_id=user.user_id,
            now=datetime.now(UTC),
        )
        await self.db.commit()

        await self.event_publisher.publish(
            "auth.email_verification_resent",
            {
                "userId": str(user.user_id),
                "email": user.email,
                "token": token,
                "expiresInMinutes": self.settings.email_verification_expire_minutes,
                "userAgent": user_agent or "",
            },
        )

    async def get_profile(self, *, user_id: int) -> UserProfile:
        user = await self.db.get(User, user_id)
        if user is None:
            raise ApiError(status_code=404, code=404, message="User not found")
        preference = await self._get_user_preference(user.user_id)
        user_schema = self._to_user_schema(user=user, preference=preference)
        return UserProfile(
            **user_schema.model_dump(),
            groups=[],
            updated_at=user.updated_at,
            last_login=user.last_login_at,
        )

    async def update_profile(
        self,
        *,
        user_id: int,
        payload: UpdateProfileRequest,
        user_agent: str | None,
    ) -> UserProfile:
        async def _operation() -> tuple[UserProfile, str | None]:
            await apply_local_lock_timeout(self.db)
            user = await self.db.scalar(select(User).where(User.user_id == user_id).with_for_update())
            if user is None:
                raise ApiError(status_code=404, code=404, message="User not found")

            now = datetime.now(UTC)
            email_verification_token: str | None = None
            changed = False

            if payload.username is not None:
                username = payload.username.strip()
                if not username:
                    raise ApiError(status_code=400, code=400, message="username cannot be empty")
                if username.lower() != user.username.lower():
                    username_exists = await self.db.scalar(
                        select(User.user_id).where(
                            and_(
                                func.lower(User.username) == username.lower(),
                                User.user_id != user.user_id,
                            )
                        )
                    )
                    if username_exists is not None:
                        raise ApiError(status_code=409, code=409, message="Username already exists")
                    user.username = username
                    changed = True

            if payload.email is not None:
                email = payload.email.strip()
                if not email:
                    raise ApiError(status_code=400, code=400, message="email cannot be empty")
                if email.lower() != user.email.lower():
                    email_exists = await self.db.scalar(
                        select(User.user_id).where(
                            and_(
                                func.lower(User.email) == email.lower(),
                                User.user_id != user.user_id,
                            )
                        )
                    )
                    if email_exists is not None:
                        raise ApiError(status_code=409, code=409, message="Email already exists")
                    user.email = email
                    user.email_verified = False
                    user.email_verified_at = None
                    email_verification_token = await self._create_email_verification_token(
                        user_id=user.user_id,
                        now=now,
                    )
                    changed = True

            if changed:
                user.updated_at = now
                await self.db.commit()

            preference = await self._get_user_preference(user.user_id)
            user_schema = self._to_user_schema(user=user, preference=preference)
            profile = UserProfile(
                **user_schema.model_dump(),
                groups=[],
                updated_at=user.updated_at,
                last_login=user.last_login_at,
            )
            return profile, email_verification_token

        try:
            profile, verification_token = await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

        if verification_token:
            await self.event_publisher.publish(
                "auth.email_verification_requested",
                {
                    "userId": str(profile.user_id),
                    "email": profile.email,
                    "token": verification_token,
                    "expiresInMinutes": self.settings.email_verification_expire_minutes,
                    "userAgent": user_agent or "",
                },
            )

        return profile

    async def get_preference(self, *, user_id: int) -> UserPreferenceSchema:
        preference = await self._get_or_create_user_preference(user_id=user_id)
        return UserPreferenceSchema(language=preference.ui_language.value)

    async def update_preference(
        self,
        *,
        user_id: int,
        payload: UpdateUserPreferenceRequest,
    ) -> UserPreferenceSchema:
        preference = await self._get_or_create_user_preference(user_id=user_id)

        if payload.language is not None:
            preference.ui_language = UiLanguage(payload.language)
            preference.updated_at = datetime.now(UTC)
            await self.db.commit()

        return UserPreferenceSchema(language=preference.ui_language.value)

    async def change_password(
        self,
        *,
        user_id: int,
        payload: ChangePasswordRequest,
        current_refresh_token: str | None,
    ) -> None:
        if not payload.old_password:
            raise ApiError(status_code=400, code=400, message="oldPassword is required")
        if not payload.new_password:
            raise ApiError(status_code=400, code=400, message="newPassword is required")
        if payload.old_password == payload.new_password:
            raise ApiError(status_code=400, code=400, message="newPassword must be different from oldPassword")

        token_hash = hash_token(current_refresh_token) if current_refresh_token else None

        async def _operation() -> None:
            await apply_local_lock_timeout(self.db)
            user = await self.db.scalar(select(User).where(User.user_id == user_id).with_for_update())
            if user is None:
                raise ApiError(status_code=404, code=404, message="User not found")
            if not verify_password(payload.old_password or "", user.password_hash):
                raise ApiError(status_code=400, code=400, message="Old password is incorrect")

            now = datetime.now(UTC)
            user.password_hash = get_password_hash(payload.new_password)
            user.password_changed_at = now
            user.updated_at = now
            user.failed_login_count = 0
            user.locked_until = None

            active_sessions = list(
                await self.db.scalars(
                    select(UserSession)
                    .where(
                        and_(
                            UserSession.user_id == user.user_id,
                            UserSession.revoked_at.is_(None),
                        )
                    )
                    .with_for_update()
                )
            )
            for session in active_sessions:
                if token_hash and session.refresh_token_hash == token_hash:
                    continue
                session.revoked_at = now
                session.last_seen_at = now

            await self.db.commit()

        try:
            await run_with_transaction_retry(self.db, _operation)
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def get_activity_log(
        self,
        *,
        user_id: int,
        query: GetActivityLogQuery,
    ) -> PaginatedData[ActivityItem]:
        base = select(Log).where(Log.user_id == user_id)
        if query.operation:
            base = base.where(Log.operation == query.operation)

        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        total_items = int(total or 0)

        offset = (query.page - 1) * query.per_page
        rows = list(
            await self.db.scalars(
                base.order_by(Log.performed_at.desc(), Log.id.desc()).offset(offset).limit(query.per_page)
            )
        )

        items: list[ActivityItem] = []
        for row in rows:
            raw_details = dict(row.metadata_payload or {})
            if row.details and "message" not in raw_details:
                raw_details["message"] = row.details
            if row.user_agent and "user_agent" not in raw_details:
                raw_details["user_agent"] = row.user_agent

            details: dict[str, str | int] = {}
            for key, value in raw_details.items():
                if isinstance(value, bool):
                    details[key] = int(value)
                elif isinstance(value, (str, int)):
                    details[key] = value
                elif value is not None:
                    details[key] = str(value)

            items.append(
                ActivityItem(
                    id=int(row.id),
                    operation=row.operation,
                    details=details,
                    ip_address=row.ip_address or "",
                    performed_at=row.performed_at or datetime.now(UTC),
                )
            )

        total_pages = max(1, -(-total_items // query.per_page))
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total_items,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def get_storage_summary(self, *, user_id: int) -> StorageStats:
        user = await self.db.get(User, user_id)
        if user is None:
            raise ApiError(status_code=404, code=404, message="User not found")

        file_rows = (
            await self.db.execute(
                select(File.file_size, File.mime_type, File.file_ext).where(
                    and_(
                        File.owner_id == user_id,
                        File.status == FileStatus.ACTIVE,
                        File.is_latest.is_(True),
                    )
                )
            )
        ).all()

        breakdown = {
            "documents": {"size": 0, "count": 0},
            "images": {"size": 0, "count": 0},
            "videos": {"size": 0, "count": 0},
            "audio": {"size": 0, "count": 0},
            "archives": {"size": 0, "count": 0},
            "others": {"size": 0, "count": 0},
        }

        storage_used = 0
        for size, mime_type, file_ext in file_rows:
            current_size = int(size or 0)
            storage_used += current_size
            category = self._categorize_file(mime_type=mime_type, file_ext=file_ext)
            breakdown[category]["size"] += current_size
            breakdown[category]["count"] += 1

        file_count = len(file_rows)
        folder_count = await self.db.scalar(
            select(func.count()).select_from(Folder).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                    Folder.folder_type != FolderType.ROOT,
                )
            )
        )
        folder_count_value = int(folder_count or 0)

        storage_limit = int(user.storage_limit or 0)
        storage_available = max(0, storage_limit - storage_used)
        storage_percentage = round((storage_used / storage_limit) * 100, 2) if storage_limit > 0 else 0.0

        return StorageStats(
            storage_limit=storage_limit,
            storage_used=storage_used,
            storage_available=storage_available,
            storage_percentage=storage_percentage,
            file_count=file_count,
            folder_count=folder_count_value,
            breakdown={key: BreakdownDetail(size=value["size"], count=value["count"]) for key, value in breakdown.items()},
        )

    async def get_user_by_id(self, *, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def _ensure_rate_limit(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        message: str,
    ) -> None:
        allowed = await self.rate_limiter.allow(key=key, limit=limit, window_seconds=window_seconds)
        if not allowed:
            raise ApiError(status_code=429, code=429, message=message)

    async def _create_email_verification_token(self, *, user_id: int, now: datetime) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add(
            EmailVerificationToken(
                user_id=user_id,
                token_hash=hash_token(token),
                expire_at=now + timedelta(minutes=self.settings.email_verification_expire_minutes),
            )
        )
        return token

    async def _create_password_reset_token(
        self,
        *,
        user_id: int,
        now: datetime,
        client_ip: str,
        user_agent: str | None,
    ) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=hash_token(token),
                expire_at=now + timedelta(minutes=self.settings.password_reset_expire_minutes),
                requester_ip=client_ip,
                user_agent=user_agent,
            )
        )
        return token

    async def _get_user_preference(self, user_id: int) -> UserPreference | None:
        statement: Select[tuple[UserPreference]] = select(UserPreference).where(UserPreference.user_id == user_id)
        return await self.db.scalar(statement)

    async def _get_or_create_user_preference(self, *, user_id: int) -> UserPreference:
        preference = await self._get_user_preference(user_id)
        if preference is not None:
            return preference

        preference = UserPreference(
            user_id=user_id,
            ui_language=UiLanguage.ZH_CN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.db.add(preference)
        await self.db.commit()
        return preference

    @staticmethod
    def _categorize_file(*, mime_type: str | None, file_ext: str | None) -> str:
        mime = (mime_type or "").lower()
        ext = (file_ext or "").lower()

        if mime.startswith("image/") or ext in {"jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "heic"}:
            return "images"
        if mime.startswith("video/") or ext in {"mp4", "mov", "avi", "mkv", "webm"}:
            return "videos"
        if mime.startswith("audio/") or ext in {"mp3", "wav", "flac", "aac", "ogg"}:
            return "audio"
        if mime in {
            "application/zip",
            "application/x-7z-compressed",
            "application/x-rar-compressed",
            "application/x-tar",
            "application/gzip",
        } or ext in {"zip", "7z", "rar", "tar", "gz"}:
            return "archives"
        if mime.startswith("text/") or mime in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }:
            return "documents"
        return "others"

    def _to_user_schema(self, *, user: User, preference: UserPreference | None) -> UserSchema:
        user_status = "active" if user.status == UserStatus.ACTIVE else "suspended"
        role: Literal["user", "admin"] = "admin" if user.role == UserRole.ADMIN else "user"
        preference_schema = None
        if preference is not None:
            preference_schema = UserPreferenceSchema(language=preference.ui_language.value)
        return UserSchema(
            user_id=str(user.user_id),
            username=user.username,
            email=user.email,
            storage_limit=user.storage_limit,
            storage_used=user.storage_used,
            created_at=user.created_at,
            role=role,
            status=user_status,
            email_verified=user.email_verified,
            email_verified_at=user.email_verified_at,
            preference=preference_schema,
        )

