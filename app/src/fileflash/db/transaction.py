from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError

T = TypeVar("T")

LOCK_TIMEOUT_SQL = "SET LOCAL lock_timeout = '3s'"
RETRY_DELAYS_SECONDS = (0.05, 0.2, 0.5)

SQLSTATE_LOCK_NOT_AVAILABLE = "55P03"
SQLSTATE_DEADLOCK_DETECTED = "40P01"
SQLSTATE_SERIALIZATION_FAILURE = "40001"
SQLSTATE_UNIQUE_VIOLATION = "23505"

RETRYABLE_SQLSTATES = {
    SQLSTATE_LOCK_NOT_AVAILABLE,
    SQLSTATE_DEADLOCK_DETECTED,
    SQLSTATE_SERIALIZATION_FAILURE,
}


async def apply_local_lock_timeout(db: AsyncSession) -> None:
    execute = getattr(db, "execute", None)
    if not callable(execute):
        return
    await execute(text(LOCK_TIMEOUT_SQL))


def sqlstate_from_error(exc: BaseException) -> str | None:
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))

        sqlstate = getattr(current, "sqlstate", None)
        if isinstance(sqlstate, str) and sqlstate:
            return sqlstate

        pgcode = getattr(current, "pgcode", None)
        if isinstance(pgcode, str) and pgcode:
            return pgcode

        orig = getattr(current, "orig", None)
        if isinstance(orig, BaseException) and id(orig) not in visited:
            current = orig
            continue

        cause = current.__cause__
        if isinstance(cause, BaseException) and id(cause) not in visited:
            current = cause
            continue

        context = current.__context__
        if isinstance(context, BaseException) and id(context) not in visited:
            current = context
            continue

        return None
    return None


def is_retryable_database_error(exc: BaseException) -> bool:
    return sqlstate_from_error(exc) in RETRYABLE_SQLSTATES


def is_unique_violation_error(exc: BaseException) -> bool:
    if isinstance(exc, IntegrityError):
        return sqlstate_from_error(exc) == SQLSTATE_UNIQUE_VIOLATION
    return False


async def run_with_transaction_retry(
    db: AsyncSession,
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    retry_on_unique_violation: bool = False,
) -> T:
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001
            should_retry = is_retryable_database_error(exc) or (
                retry_on_unique_violation and is_unique_violation_error(exc)
            )
            if attempt >= attempts or not should_retry:
                raise
            rollback = getattr(db, "rollback", None)
            if callable(rollback):
                await rollback()
            delay = RETRY_DELAYS_SECONDS[min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)]
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")


def to_retryable_concurrency_error(exc: BaseException) -> ApiError:
    sqlstate = sqlstate_from_error(exc)
    data = {"retryable": True}
    if sqlstate:
        data["sqlState"] = sqlstate
    return ApiError(
        status_code=409,
        code=409,
        message="Concurrent modification detected, please retry",
        data=data,
    )
