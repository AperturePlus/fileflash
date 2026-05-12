from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..tasks import dispatch_task


def execute_task(task_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return dispatch_task(task_type=task_type, payload=payload)
