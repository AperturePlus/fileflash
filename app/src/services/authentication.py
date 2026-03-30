from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.security import create_access_token, create_refresh_token, get_password_hash, hash_token, verify_password
from ..core.settings import Settings
from ..models.enums import UiLanguage, UserStatus
from ..models.tables_identity import EmailVerificationToken, PasswordResetToken, User, UserPreference, UserSession
from ..schemas.auth import ForgotPasswordResponse, RegisterRequest, RegisterResponseData, TokenResponse
from ..schemas.user import User as UserSchema
from ..schemas.user import UserPreference as UserPreferenceSchema
from ..schemas.user import UserProfile
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
            role="user",
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

        user = await self.db.scalar(
            select(User).where(
                or_(
                    func.lower(User.username) == username.lower(),
                    func.lower(User.email) == username.lower(),
                )
            )
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

        await self.event_publisher.publish(
            "auth.user_logged_in",
            {
                "userId": str(user.user_id),
                "ipAddress": client_ip,
            },
        )

        token_response = TokenResponse(
            token=access_token,
            token_type="Bearer",
            expires_in=self.settings.access_token_ttl_seconds,
            user=self._to_user_schema(user=user, preference=preference),
        )
        return token_response, refresh_token

    async def refresh(
        self,
        *,
        refresh_token: str,
        client_ip: str,
        user_agent: str | None,
    ) -> tuple[TokenResponse, str]:
        now = datetime.now(UTC)
        token_hash = hash_token(refresh_token)
        session = await self.db.scalar(
            select(UserSession).where(
                and_(
                    UserSession.refresh_token_hash == token_hash,
                    UserSession.revoked_at.is_(None),
                    UserSession.expire_at > now,
                )
            )
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
        now = datetime.now(UTC)
        token_hash_value = hash_token(token)
        reset_record = await self.db.scalar(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token_hash == token_hash_value,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expire_at > now,
                )
            )
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
            select(UserSession).where(
                and_(
                    UserSession.user_id == user.user_id,
                    UserSession.revoked_at.is_(None),
                )
            )
        )
        for session in sessions:
            session.revoked_at = now
            session.last_seen_at = now

        await self.db.commit()

    async def verify_email(self, *, token: str) -> None:
        now = datetime.now(UTC)
        token_hash_value = hash_token(token)
        verification_record = await self.db.scalar(
            select(EmailVerificationToken).where(
                and_(
                    EmailVerificationToken.token_hash == token_hash_value,
                    EmailVerificationToken.verified_at.is_(None),
                    EmailVerificationToken.expire_at > now,
                )
            )
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

    def _to_user_schema(self, *, user: User, preference: UserPreference | None) -> UserSchema:
        user_status = "active" if user.status == UserStatus.ACTIVE else "suspended"
        role = str(user.role).lower() if user.role else "user"
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

