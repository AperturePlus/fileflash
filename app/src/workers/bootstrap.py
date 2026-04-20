from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from ..core.settings import Settings, get_settings


@dataclass(slots=True, frozen=True)
class WorkerRuntimeConfig:
    poll_interval_seconds: float
    task_timeout_seconds: int
    worker_slots: int
    default_max_attempts: int
    retry_backoff_seconds: tuple[int, ...]
    queue_stream: str
    queue_group: str
    queue_block_ms: int
    ffmpeg_binary: str
    ffprobe_binary: str


def build_worker_runtime_config(settings: Settings | None = None) -> WorkerRuntimeConfig:
    current = settings or get_settings()
    worker_slots = max(1, current.worker_concurrency)
    return WorkerRuntimeConfig(
        poll_interval_seconds=max(0.1, current.worker_poll_interval_seconds),
        task_timeout_seconds=max(30, current.worker_task_timeout_seconds),
        worker_slots=worker_slots,
        default_max_attempts=max(1, current.worker_default_max_attempts),
        retry_backoff_seconds=current.worker_retry_backoff_schedule,
        queue_stream=current.worker_queue_stream,
        queue_group=current.worker_queue_group,
        queue_block_ms=max(100, current.worker_queue_block_ms),
        ffmpeg_binary=current.ffmpeg_binary,
        ffprobe_binary=current.ffprobe_binary,
    )


def create_process_pool(config: WorkerRuntimeConfig) -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=config.worker_slots)
