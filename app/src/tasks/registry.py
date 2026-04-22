from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .archive import run_archive_extract, run_archive_preview
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
    "task.archive_preview": run_archive_preview,
    "archive.preview": run_archive_preview,
    "task.archive_extract": run_archive_extract,
    "archive.extract": run_archive_extract,
}


def dispatch_task(task_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    handler = _TASK_HANDLERS.get(task_type)
    if handler is None:
        supported = ", ".join(sorted(_TASK_HANDLERS))
        raise UnknownTaskTypeError(f"Unsupported taskType: {task_type}. Supported: {supported}")
    return handler(payload)
