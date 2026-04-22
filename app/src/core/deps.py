from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.deps import get_db
from ..models.tables_identity import User
from ..services.archive import ArchiveService
from ..services.auth import AuthService
from ..services.background_jobs import BackgroundJobService
from ..services.job_queue import RedisStreamJobQueue
from ..services.messaging import InProcessAuthEventPublisher
from ..services.rate_limiter import RedisRateLimiter
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


def get_rate_limiter() -> RedisRateLimiter:
    return _rate_limiter


def get_event_publisher() -> InProcessAuthEventPublisher:
    return _event_publisher


def get_object_storage() -> MinioObjectStorageClient:
    return _object_storage


def get_job_queue_publisher() -> RedisStreamJobQueue:
    return _job_queue_publisher


def get_background_job_service(
    queue_publisher: RedisStreamJobQueue = Depends(get_job_queue_publisher),
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
    )


def get_upload_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    storage: MinioObjectStorageClient = Depends(get_object_storage),
) -> UploadService:
    return UploadService(db=db, settings=settings, storage=storage)


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

