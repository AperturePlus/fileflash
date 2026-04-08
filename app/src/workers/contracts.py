from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class WorkerJobMessage:
    version: int
    message_id: str
    job_id: int
    task_type: str
    idempotency_key: str | None
    attempt: int
    max_attempts: int
    trace_id: str
    requested_by: str | None
    payload: dict[str, Any]
