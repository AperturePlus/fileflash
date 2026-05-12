from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import get_password_hash
from ..core.settings import Settings
from ..db.session import SessionLocal
from ..models.enums import FolderStatus, FolderType, UiLanguage, UserRole, UserStatus
from ..models.tables_identity import User, UserPreference
from ..models.tables_storage import Folder

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DevSeedAccount:
    username: str
    email: str
    password: str
    role: UserRole
    language: UiLanguage


@dataclass(slots=True)
class DevSeedSummary:
    created_users: int = 0
    updated_users: int = 0
    reset_password_users: int = 0
    created_preferences: int = 0
    created_roots: int = 0


DEV_SEED_ACCOUNTS: tuple[DevSeedAccount, ...] = (
    DevSeedAccount(
        username="admin",
        email="admin@fileflash.local",
        password="admin123",
        role=UserRole.ADMIN,
        language=UiLanguage.ZH_CN,
    ),
    DevSeedAccount(
        username="demo",
        email="demo@fileflash.local",
        password="demo123",
        role=UserRole.USER,
        language=UiLanguage.EN_US,
    ),
)


async def initialize_dev_accounts(
    *,
    settings: Settings,
    reset_password: bool = False,
    auto_run: bool = False,
) -> bool:
    if auto_run and not settings.is_development_env:
        if settings.is_production_env:
            logger.info("Skip dev account auto-initialization in production environment: %s", settings.app_env)
        else:
            logger.info("Skip dev account auto-initialization for non-dev APP_ENV=%s", settings.app_env)
        return False

    async with SessionLocal() as db:
        seeder = DevAccountSeeder(db=db)
        summary = await seeder.seed(reset_password=reset_password)

    logger.info(
        "Dev accounts initialized: createdUsers=%s updatedUsers=%s resetPasswordUsers=%s createdPreferences=%s createdRoots=%s",
        summary.created_users,
        summary.updated_users,
        summary.reset_password_users,
        summary.created_preferences,
        summary.created_roots,
    )
    return True


class DevAccountSeeder:
    def __init__(self, *, db: AsyncSession) -> None:
        self.db = db

    async def seed(self, *, reset_password: bool = False) -> DevSeedSummary:
        summary = DevSeedSummary()
        now = datetime.now(UTC)

        for spec in DEV_SEED_ACCOUNTS:
            user = await self._find_existing_user(spec=spec)
            created = user is None

            if user is None:
                user = User(
                    username=spec.username,
                    email=spec.email,
                    password_hash=get_password_hash(spec.password),
                    role=spec.role,
                    status=UserStatus.ACTIVE,
                    email_verified=True,
                    email_verified_at=now,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(user)
                await self.db.flush()
                summary.created_users += 1
            else:
                user.username = spec.username
                user.email = spec.email
                user.role = spec.role
                user.status = UserStatus.ACTIVE
                user.email_verified = True
                user.email_verified_at = user.email_verified_at or now
                user.deleted_at = None
                user.failed_login_count = 0
                user.locked_until = None
                user.updated_at = now
                summary.updated_users += 1

                if reset_password:
                    user.password_hash = get_password_hash(spec.password)
                    user.password_changed_at = now
                    summary.reset_password_users += 1

            if created:
                user.password_changed_at = now

            await self._ensure_preference(user=user, language=spec.language, now=now, summary=summary)
            await self._ensure_root_folder(user=user, now=now, summary=summary)

        await self.db.commit()
        return summary

    async def _find_existing_user(self, *, spec: DevSeedAccount) -> User | None:
        return await self.db.scalar(
            select(User)
            .where(
                or_(
                    func.lower(User.username) == spec.username.lower(),
                    func.lower(User.email) == spec.email.lower(),
                )
            )
            .order_by(User.user_id.asc())
            .limit(1)
        )

    async def _ensure_preference(
        self,
        *,
        user: User,
        language: UiLanguage,
        now: datetime,
        summary: DevSeedSummary,
    ) -> None:
        preference = await self.db.scalar(select(UserPreference).where(UserPreference.user_id == user.user_id))
        if preference is None:
            self.db.add(
                UserPreference(
                    user_id=user.user_id,
                    ui_language=language,
                    created_at=now,
                    updated_at=now,
                )
            )
            summary.created_preferences += 1
            return

        preference.ui_language = language
        preference.updated_at = now

    async def _ensure_root_folder(
        self,
        *,
        user: User,
        now: datetime,
        summary: DevSeedSummary,
    ) -> None:
        root = await self.db.scalar(
            select(Folder).where(
                and_(
                    Folder.owner_id == user.user_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_type == FolderType.ROOT,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if root is not None:
            return

        self.db.add(
            Folder(
                owner_id=user.user_id,
                parent_folder_id=None,
                folder_name="My Files",
                cached_size=0,
                status=FolderStatus.ACTIVE,
                folder_type=FolderType.ROOT,
                created_at=now,
                updated_at=now,
            )
        )
        summary.created_roots += 1
