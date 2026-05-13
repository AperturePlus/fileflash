from __future__ import annotations

import asyncio
import pickle
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.core.errors import ApiError
from fileflash.tasks.registry import UnknownTaskTypeError, dispatch_task
from fileflash.workers.consumer import WorkerConsumer, _is_retryable_error
from fileflash.workers.contracts import WorkerJobMessage
from fileflash.workers.dispatcher import PicklableRemoteTaskError, execute_task
from fileflash.workers.bootstrap import WorkerRuntimeConfig
from fileflash.workers.repository import get_retry_delay_seconds


class _AsyncContextManager:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_dispatch_task_rejects_unknown_type():
    with pytest.raises(UnknownTaskTypeError):
        dispatch_task("not-supported", {})


def test_retry_delay_uses_last_backoff_when_attempt_exceeds_schedule():
    schedule = (3, 10, 30)
    assert get_retry_delay_seconds(schedule, attempt=1) == 3
    assert get_retry_delay_seconds(schedule, attempt=2) == 10
    assert get_retry_delay_seconds(schedule, attempt=4) == 30


def test_picklable_remote_task_error_can_be_pickled():
    error = PicklableRemoteTaskError(
        original_type="TypeError",
        message="cannot pickle '_thread.lock' object",
        retryable_hint=True,
    )
    restored = pickle.loads(pickle.dumps(error))
    assert isinstance(restored, PicklableRemoteTaskError)
    assert restored.original_type == "TypeError"
    assert restored.message == "cannot pickle '_thread.lock' object"
    assert restored.retryable_hint is True


def test_retryable_error_uses_remote_hint_when_present():
    retryable = PicklableRemoteTaskError(original_type="RuntimeError", message="x", retryable_hint=True)
    non_retryable = PicklableRemoteTaskError(original_type="RuntimeError", message="x", retryable_hint=False)

    assert _is_retryable_error(retryable) is True
    assert _is_retryable_error(non_retryable) is False


def test_retryable_error_uses_remote_original_type_mapping():
    wrapped_value_error = PicklableRemoteTaskError(
        original_type="ValueError",
        message="bad payload",
        retryable_hint=None,
    )
    wrapped_runtime_error = PicklableRemoteTaskError(
        original_type="RuntimeError",
        message="temporary upstream",
        retryable_hint=None,
    )

    assert _is_retryable_error(wrapped_value_error) is False
    assert _is_retryable_error(wrapped_runtime_error) is True


def test_retryable_error_for_api_error():
    non_retryable = ApiError(status_code=400, code=400, message="bad request")
    retryable_500 = ApiError(status_code=503, code=503, message="queue down")
    retryable_409 = ApiError(
        status_code=409,
        code=409,
        message="retry",
        data={"retryable": True},
    )

    assert _is_retryable_error(non_retryable) is False
    assert _is_retryable_error(retryable_500) is True
    assert _is_retryable_error(retryable_409) is True


def test_execute_task_wraps_non_picklable_exception(monkeypatch):
    class _NonPicklableError(Exception):
        def __init__(self):
            self.lock = threading.Lock()
            super().__init__("cannot pickle lock")

    def raise_non_picklable(*_args, **_kwargs):
        raise _NonPicklableError()

    monkeypatch.setattr("fileflash.workers.dispatcher.dispatch_task", raise_non_picklable)

    with pytest.raises(PicklableRemoteTaskError) as exc_info:
        execute_task("task.archive_preview", {})

    wrapped = exc_info.value
    assert wrapped.original_type == "_NonPicklableError"
    assert wrapped.message == "cannot pickle lock"


@pytest.mark.asyncio
async def test_process_message_backfills_missing_job_id_in_payload(monkeypatch):
    config = WorkerRuntimeConfig(
        poll_interval_seconds=1.0,
        task_timeout_seconds=30,
        worker_slots=1,
        default_max_attempts=5,
        retry_backoff_seconds=(1, 2, 3),
        queue_stream="fileflash:tasks",
        queue_group="fileflash-workers",
        queue_block_ms=1000,
        ffmpeg_binary="ffmpeg",
        ffprobe_binary="ffprobe",
    )
    queue = SimpleNamespace()
    session = SimpleNamespace(begin=lambda: _AsyncContextManager(SimpleNamespace()))
    session_factory = lambda: _AsyncContextManager(session)
    consumer = WorkerConsumer(
        config=config,
        executor=None,  # type: ignore[arg-type]
        queue=queue,  # type: ignore[arg-type]
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    message = WorkerJobMessage(
        version=1,
        message_id="job-123-attempt-0",
        job_id=123,
        task_type="task.archive_extract",
        idempotency_key=None,
        attempt=0,
        max_attempts=5,
        trace_id="trace-1",
        requested_by="9",
        payload={"targetFolderId": "root", "jobId": None},
    )

    loop = asyncio.get_running_loop()
    captured_payload: dict[str, object] = {}

    async def fake_wait_for(awaitable, timeout):
        return await awaitable

    def fake_run_in_executor(_executor, _fn, _task_type, payload):
        captured_payload.update(payload)
        fut = loop.create_future()
        fut.set_result({"summary": {}})
        return fut

    monkeypatch.setattr("fileflash.workers.consumer.apply_task_effects", AsyncMock(return_value={}))
    monkeypatch.setattr("fileflash.workers.consumer.mark_job_succeeded", AsyncMock())
    monkeypatch.setattr("fileflash.workers.consumer.asyncio.wait_for", fake_wait_for)
    monkeypatch.setattr(loop, "run_in_executor", fake_run_in_executor)

    await consumer._process_message(slot=0, message=message)

    assert captured_payload["jobId"] == 123


@pytest.mark.asyncio
async def test_process_message_backfills_empty_job_id_in_payload(monkeypatch):
    config = WorkerRuntimeConfig(
        poll_interval_seconds=1.0,
        task_timeout_seconds=30,
        worker_slots=1,
        default_max_attempts=5,
        retry_backoff_seconds=(1, 2, 3),
        queue_stream="fileflash:tasks",
        queue_group="fileflash-workers",
        queue_block_ms=1000,
        ffmpeg_binary="ffmpeg",
        ffprobe_binary="ffprobe",
    )
    queue = SimpleNamespace()
    session = SimpleNamespace(begin=lambda: _AsyncContextManager(SimpleNamespace()))
    session_factory = lambda: _AsyncContextManager(session)
    consumer = WorkerConsumer(
        config=config,
        executor=None,  # type: ignore[arg-type]
        queue=queue,  # type: ignore[arg-type]
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    message = WorkerJobMessage(
        version=1,
        message_id="job-321-attempt-0",
        job_id=321,
        task_type="task.archive_extract",
        idempotency_key=None,
        attempt=0,
        max_attempts=5,
        trace_id="trace-2",
        requested_by="9",
        payload={"targetFolderId": "root", "jobId": ""},
    )

    loop = asyncio.get_running_loop()
    captured_payload: dict[str, object] = {}

    async def fake_wait_for(awaitable, timeout):
        return await awaitable

    def fake_run_in_executor(_executor, _fn, _task_type, payload):
        captured_payload.update(payload)
        fut = loop.create_future()
        fut.set_result({"summary": {}})
        return fut

    monkeypatch.setattr("fileflash.workers.consumer.apply_task_effects", AsyncMock(return_value={}))
    monkeypatch.setattr("fileflash.workers.consumer.mark_job_succeeded", AsyncMock())
    monkeypatch.setattr("fileflash.workers.consumer.asyncio.wait_for", fake_wait_for)
    monkeypatch.setattr(loop, "run_in_executor", fake_run_in_executor)

    await consumer._process_message(slot=0, message=message)

    assert captured_payload["jobId"] == 321


@pytest.mark.asyncio
async def test_process_transcode_message_marks_running(monkeypatch):
    config = WorkerRuntimeConfig(
        poll_interval_seconds=1.0,
        task_timeout_seconds=30,
        worker_slots=1,
        default_max_attempts=5,
        retry_backoff_seconds=(1, 2, 3),
        queue_stream="fileflash:tasks",
        queue_group="fileflash-workers",
        queue_block_ms=1000,
        ffmpeg_binary="ffmpeg",
        ffprobe_binary="ffprobe",
    )
    queue = SimpleNamespace()
    session = SimpleNamespace(begin=lambda: _AsyncContextManager(SimpleNamespace()))
    session_factory = lambda: _AsyncContextManager(session)
    consumer = WorkerConsumer(
        config=config,
        executor=None,  # type: ignore[arg-type]
        queue=queue,  # type: ignore[arg-type]
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    message = WorkerJobMessage(
        version=1,
        message_id="job-666-attempt-0",
        job_id=666,
        task_type="task.transcode",
        idempotency_key=None,
        attempt=0,
        max_attempts=5,
        trace_id="trace-666",
        requested_by="9",
        payload={
            "sourceObjectId": 99,
            "sourceBucketName": "fileflash",
            "sourceObjectKey": "objects/u1/source",
            "outputBucketName": "fileflash",
            "outputObjectKey": "optimized/transcode/v1/object-99/source-mp4-v1.mp4",
        },
    )

    loop = asyncio.get_running_loop()

    async def fake_wait_for(awaitable, timeout):
        return await awaitable

    def fake_run_in_executor(_executor, _fn, _task_type, payload):
        _ = payload
        fut = loop.create_future()
        fut.set_result({"summary": {}})
        return fut

    mark_running_mock = AsyncMock()
    monkeypatch.setattr(consumer, "_mark_transcode_running", mark_running_mock)
    monkeypatch.setattr("fileflash.workers.consumer.apply_task_effects", AsyncMock(return_value={}))
    monkeypatch.setattr("fileflash.workers.consumer.mark_job_succeeded", AsyncMock())
    monkeypatch.setattr("fileflash.workers.consumer.asyncio.wait_for", fake_wait_for)
    monkeypatch.setattr(loop, "run_in_executor", fake_run_in_executor)

    await consumer._process_message(slot=0, message=message)
    mark_running_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_failure_marks_transcode_failed_on_terminal_state(monkeypatch):
    config = WorkerRuntimeConfig(
        poll_interval_seconds=1.0,
        task_timeout_seconds=30,
        worker_slots=1,
        default_max_attempts=5,
        retry_backoff_seconds=(1, 2, 3),
        queue_stream="fileflash:tasks",
        queue_group="fileflash-workers",
        queue_block_ms=1000,
        ffmpeg_binary="ffmpeg",
        ffprobe_binary="ffprobe",
    )
    queue = SimpleNamespace()
    session = SimpleNamespace(begin=lambda: _AsyncContextManager(SimpleNamespace()))
    session_factory = lambda: _AsyncContextManager(session)
    consumer = WorkerConsumer(
        config=config,
        executor=None,  # type: ignore[arg-type]
        queue=queue,  # type: ignore[arg-type]
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    message = WorkerJobMessage(
        version=1,
        message_id="job-777-attempt-0",
        job_id=777,
        task_type="task.transcode",
        idempotency_key=None,
        attempt=0,
        max_attempts=1,
        trace_id="trace-777",
        requested_by="9",
        payload={"sourceObjectId": 77, "outputObjectKey": "optimized/x.mp4"},
    )

    monkeypatch.setattr("fileflash.workers.consumer.mark_job_failed_or_retrying", AsyncMock(return_value="failed"))
    failed_mock = AsyncMock()
    monkeypatch.setattr("fileflash.workers.consumer.mark_transcode_failed", failed_mock)
    monkeypatch.setattr("fileflash.workers.consumer.asyncio.create_task", lambda _task: None)

    await consumer._handle_failure(slot=0, message=message, error=RuntimeError("boom"))
    failed_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_upload_merge_message_uses_upload_service_path(monkeypatch):
    config = WorkerRuntimeConfig(
        poll_interval_seconds=1.0,
        task_timeout_seconds=30,
        worker_slots=1,
        default_max_attempts=5,
        retry_backoff_seconds=(1, 2, 3),
        queue_stream="fileflash:tasks",
        queue_group="fileflash-workers",
        queue_block_ms=1000,
        ffmpeg_binary="ffmpeg",
        ffprobe_binary="ffprobe",
    )
    queue = SimpleNamespace()
    session = SimpleNamespace(begin=lambda: _AsyncContextManager(SimpleNamespace()))
    session_factory = lambda: _AsyncContextManager(session)
    consumer = WorkerConsumer(
        config=config,
        executor=None,  # type: ignore[arg-type]
        queue=queue,  # type: ignore[arg-type]
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    message = WorkerJobMessage(
        version=1,
        message_id="job-999-attempt-0",
        job_id=999,
        task_type="task.upload_merge",
        idempotency_key=None,
        attempt=0,
        max_attempts=5,
        trace_id="trace-999",
        requested_by="9",
        payload={"userId": 9, "uploadId": "upload-1", "mergeRequest": {"fileHash": "a" * 64}},
    )

    async def fake_wait_for(awaitable, timeout):
        return await awaitable

    loop = asyncio.get_running_loop()
    run_in_executor_called = False

    def fake_run_in_executor(*_args, **_kwargs):
        nonlocal run_in_executor_called
        run_in_executor_called = True
        fut = loop.create_future()
        fut.set_result({})
        return fut

    monkeypatch.setattr(consumer, "_run_upload_merge", AsyncMock(return_value={"fileId": "f1"}))
    monkeypatch.setattr("fileflash.workers.consumer.mark_job_succeeded", AsyncMock())
    monkeypatch.setattr("fileflash.workers.consumer.asyncio.wait_for", fake_wait_for)
    monkeypatch.setattr(loop, "run_in_executor", fake_run_in_executor)

    await consumer._process_message(slot=0, message=message)

    consumer._run_upload_merge.assert_awaited_once()  # type: ignore[attr-defined]
    assert run_in_executor_called is False
