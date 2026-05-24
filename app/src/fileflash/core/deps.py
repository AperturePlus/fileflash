from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.deps import get_db
from ..models.tables_identity import User
from ..models.enums import UserRole
from ..repositories import (
    AgentActionLogRepository,
    AgentMcpRepository,
    AgentMemoryRepository,
    AgentPlanRepository,
    AgentSettingsRepository,
    AgentSkillRepository,
    AgentWorkSessionRepository,
)
from ..services.archive import ArchiveService
from ..services.agent import ExecuteService, McpService, MemoryService, PlanService, SessionService, SettingsService, SkillService
from ..services.admin.users import AdminUsersService
from ..services.admin.storage import AdminStorageService
from ..services.auth import AuthService
from ..services.background_jobs import BackgroundJobService
from ..services.email_delivery import VerificationEmailDeliveryService
from ..services.file import FileService
from ..services.folder import FolderService
from ..services.job_queue import RedisStreamJobQueue
from ..services.messaging import InProcessAuthEventPublisher
from ..services.rate_limiter import RedisRateLimiter
from ..services.registration_email_domain_rule import RegistrationEmailDomainRuleService
from ..services.share import ShareService
from ..services.upload import UploadService
from ..s3 import MinioObjectStorageClient
from .errors import ApiError
from .security import decode_access_token
from .settings import Settings, get_settings

http_bearer = HTTPBearer(auto_error=False)
_settings = get_settings()
_rate_limiter = RedisRateLimiter(_settings.redis_url)
_event_publisher = InProcessAuthEventPublisher()
_object_storage = MinioObjectStorageClient.from_settings(_settings)
_job_queue_publisher = RedisStreamJobQueue(
    redis_url=_settings.redis_url,
    stream_key=_settings.worker_queue_stream,
)
_agent_job_queue_publisher = RedisStreamJobQueue(
    redis_url=_settings.redis_url,
    stream_key=_settings.agent_queue_stream,
)


def get_rate_limiter() -> RedisRateLimiter:
    return _rate_limiter


def get_event_publisher() -> InProcessAuthEventPublisher:
    return _event_publisher


def get_object_storage() -> MinioObjectStorageClient:
    return _object_storage


def get_job_queue_publisher() -> RedisStreamJobQueue:
    return _job_queue_publisher


def get_agent_job_queue_publisher() -> RedisStreamJobQueue:
    return _agent_job_queue_publisher


def get_background_job_service(
    queue_publisher: RedisStreamJobQueue = Depends(get_job_queue_publisher),
) -> BackgroundJobService:
    return BackgroundJobService(queue_publisher=queue_publisher)


def get_agent_background_job_service(
    queue_publisher: RedisStreamJobQueue = Depends(get_agent_job_queue_publisher),
) -> BackgroundJobService:
    return BackgroundJobService(queue_publisher=queue_publisher)


def get_settings_dep() -> Settings:
    return _settings


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    rate_limiter: RedisRateLimiter = Depends(get_rate_limiter),
    event_publisher: InProcessAuthEventPublisher = Depends(get_event_publisher),
) -> AuthService:
    return AuthService(
        db=db,
        settings=settings,
        rate_limiter=rate_limiter,
        event_publisher=event_publisher,
        verification_email_delivery=VerificationEmailDeliveryService(settings=settings),
    )


def get_registration_email_domain_rule_service(
    db: AsyncSession = Depends(get_db),
) -> RegistrationEmailDomainRuleService:
    return RegistrationEmailDomainRuleService(db=db)


def get_admin_users_service(
    db: AsyncSession = Depends(get_db),
) -> AdminUsersService:
    return AdminUsersService(db=db)


def get_admin_storage_service(
    db: AsyncSession = Depends(get_db),
    rate_limiter: RedisRateLimiter = Depends(get_rate_limiter),
) -> AdminStorageService:
    return AdminStorageService(db=db, redis=getattr(rate_limiter, "_redis", None))


def get_upload_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    storage: MinioObjectStorageClient = Depends(get_object_storage),
    jobs: BackgroundJobService = Depends(get_background_job_service),
) -> UploadService:
    return UploadService(db=db, settings=settings, storage=storage, jobs=jobs)


def get_share_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    storage: MinioObjectStorageClient = Depends(get_object_storage),
) -> ShareService:
    return ShareService(db=db, settings=settings, storage=storage)


def get_archive_service(
    db: AsyncSession = Depends(get_db),
    jobs: BackgroundJobService = Depends(get_background_job_service),
) -> ArchiveService:
    return ArchiveService(db=db, jobs=jobs)



def get_file_service(
    db: AsyncSession = Depends(get_db),
    storage: MinioObjectStorageClient = Depends(get_object_storage),
    settings: Settings = Depends(get_settings_dep),
) -> FileService:
    return FileService(
        db=db,
        storage=storage,
        starred_items_limit=settings.starred_items_limit,
    )


def get_folder_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> FolderService:
    return FolderService(
        db=db,
        starred_items_limit=settings.starred_items_limit,
    )



def get_agent_settings_repository(db: AsyncSession = Depends(get_db)) -> AgentSettingsRepository:
    return AgentSettingsRepository(db)


def get_agent_mcp_repository(db: AsyncSession = Depends(get_db)) -> AgentMcpRepository:
    return AgentMcpRepository(db)


def get_agent_skill_repository(db: AsyncSession = Depends(get_db)) -> AgentSkillRepository:
    return AgentSkillRepository(db)


def get_agent_memory_repository(db: AsyncSession = Depends(get_db)) -> AgentMemoryRepository:
    return AgentMemoryRepository(db)


def get_agent_plan_repository(db: AsyncSession = Depends(get_db)) -> AgentPlanRepository:
    return AgentPlanRepository(db)


def get_agent_action_log_repository(db: AsyncSession = Depends(get_db)) -> AgentActionLogRepository:
    return AgentActionLogRepository(db)


def get_agent_work_session_repository(db: AsyncSession = Depends(get_db)) -> AgentWorkSessionRepository:
    return AgentWorkSessionRepository(db)


def get_agent_plan_service(
    db: AsyncSession = Depends(get_db),
    jobs: BackgroundJobService = Depends(get_agent_background_job_service),
    plans: AgentPlanRepository = Depends(get_agent_plan_repository),
    settings_repo: AgentSettingsRepository = Depends(get_agent_settings_repository),
    work_sessions: AgentWorkSessionRepository = Depends(get_agent_work_session_repository),
) -> PlanService:
    return PlanService(
        db=db,
        jobs=jobs,
        plans=plans,
        settings=settings_repo,
        work_sessions=work_sessions,
    )


def get_agent_execute_service(
    db: AsyncSession = Depends(get_db),
    jobs: BackgroundJobService = Depends(get_agent_background_job_service),
    plans: AgentPlanRepository = Depends(get_agent_plan_repository),
    work_sessions: AgentWorkSessionRepository = Depends(get_agent_work_session_repository),
) -> ExecuteService:
    return ExecuteService(
        db=db,
        jobs=jobs,
        plans=plans,
        work_sessions=work_sessions,
    )


def get_agent_skill_service(
    db: AsyncSession = Depends(get_db),
    skills: AgentSkillRepository = Depends(get_agent_skill_repository),
) -> SkillService:
    return SkillService(db=db, skills=skills)


def get_agent_memory_service(
    memory: AgentMemoryRepository = Depends(get_agent_memory_repository),
) -> MemoryService:
    return MemoryService(memory=memory)


def get_agent_settings_service(
    settings_repo: AgentSettingsRepository = Depends(get_agent_settings_repository),
) -> SettingsService:
    return SettingsService(settings_repo=settings_repo)


def get_agent_mcp_service(
    mcp: AgentMcpRepository = Depends(get_agent_mcp_repository),
) -> McpService:
    return McpService(mcp=mcp)


def get_agent_session_service(
    action_logs: AgentActionLogRepository = Depends(get_agent_action_log_repository),
    work_sessions: AgentWorkSessionRepository = Depends(get_agent_work_session_repository),
) -> SessionService:
    return SessionService(action_logs=action_logs, work_sessions=work_sessions)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(status_code=401, code=401, message="Missing authorization token")

    try:
        payload = decode_access_token(credentials.credentials, settings)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise ApiError(status_code=401, code=401, message="Invalid access token") from None

    user = await db.get(User, user_id)
    if user is None:
        raise ApiError(status_code=401, code=401, message="User not found")
    return user


async def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.email_verified:
        raise ApiError(status_code=403, code=403, message="Email verification required")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ApiError(status_code=403, code=403, message="Admin access required")
    return current_user

