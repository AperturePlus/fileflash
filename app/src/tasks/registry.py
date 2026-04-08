from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .scan import run_dangerous_file_scan
from .transcode import run_media_transcode

TaskHandler = Callable[[Mapping[str, Any]], dict[str, Any]]


class UnknownTaskTypeError(ValueError):
    pass


_TASK_HANDLERS: dict[str, TaskHandler] = {
    "task.scan": run_dangerous_file_scan,
    "scan.dangerous_file": run_dangerous_file_scan,
    "task.transcode": run_media_transcode,
    "media.transcode": run_media_transcode,
}


def dispatch_task(task_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    handler = _TASK_HANDLERS.get(task_type)
    if handler is None:
        supported = ", ".join(sorted(_TASK_HANDLERS))
        raise UnknownTaskTypeError(f"Unsupported taskType: {task_type}. Supported: {supported}")
    return handler(payload)
