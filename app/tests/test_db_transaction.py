from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.db.transaction import (
    is_retryable_database_error,
    is_unique_violation_error,
    run_with_transaction_retry,
    sqlstate_from_error,
    to_retryable_concurrency_error,
)


class _SqlStateError(Exception):
    def __init__(self, sqlstate: str):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def test_sqlstate_from_error_walks_nested_orig():
    inner = _SqlStateError("55P03")
    wrapped = RuntimeError("wrapped")
    wrapped.orig = inner  # type: ignore[attr-defined]

    assert sqlstate_from_error(wrapped) == "55P03"
    assert is_retryable_database_error(wrapped) is True


def test_is_unique_violation_error_false_for_non_integrity_error():
    assert is_unique_violation_error(_SqlStateError("23505")) is False


@pytest.mark.asyncio
async def test_run_with_transaction_retry_retries_retryable_error():
    db = SimpleNamespace(rollback=AsyncMock())
    attempts = {"count": 0}

    async def _operation() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise _SqlStateError("55P03")
        return "ok"

    result = await run_with_transaction_retry(db, _operation, max_attempts=3)
    assert result == "ok"
    assert attempts["count"] == 2
    db.rollback.assert_awaited_once()


def test_to_retryable_concurrency_error_contains_retryable_data():
    err = to_retryable_concurrency_error(_SqlStateError("40P01"))
    assert err.status_code == 409
    assert err.code == 409
    assert err.data["retryable"] is True
    assert err.data["sqlState"] == "40P01"

