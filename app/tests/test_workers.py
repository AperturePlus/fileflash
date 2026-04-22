from __future__ import annotations

import pytest

from src.tasks.registry import UnknownTaskTypeError, dispatch_task
from src.workers.repository import get_retry_delay_seconds


def test_dispatch_task_rejects_unknown_type():
    with pytest.raises(UnknownTaskTypeError):
        dispatch_task("not-supported", {})


def test_retry_delay_uses_last_backoff_when_attempt_exceeds_schedule():
    schedule = (3, 10, 30)
    assert get_retry_delay_seconds(schedule, attempt=1) == 3
    assert get_retry_delay_seconds(schedule, attempt=2) == 10
    assert get_retry_delay_seconds(schedule, attempt=4) == 30
