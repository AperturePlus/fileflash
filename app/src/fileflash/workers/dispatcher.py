from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..tasks import dispatch_task


class PicklableRemoteTaskError(Exception):
    def __init__(
        self,
        *,
        original_type: str,
        message: str,
        retryable_hint: bool | None = None,
    ) -> None:
        self.original_type = original_type
        self.message = message
        self.retryable_hint = retryable_hint
        super().__init__(f"{original_type}: {message}")

    def __reduce__(self):
        return (
            self.__class__._reconstruct,
            (self.original_type, self.message, self.retryable_hint),
        )

    @classmethod
    def _reconstruct(
        cls,
        original_type: str,
        message: str,
        retryable_hint: bool | None,
    ) -> "PicklableRemoteTaskError":
        return cls(
            original_type=original_type,
            message=message,
            retryable_hint=retryable_hint,
        )


def _is_picklable_exception(exc: Exception) -> bool:
    try:
        import pickle

        pickle.dumps(exc)
    except Exception:
        return False
    return True


def execute_task(task_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return dispatch_task(task_type=task_type, payload=payload)
    except Exception as exc:
        if _is_picklable_exception(exc):
            raise

        original_type = type(exc).__name__
        message = str(exc) or repr(exc)
        retryable_hint = None
        if isinstance(exc, (FileNotFoundError, PermissionError, ValueError)):
            retryable_hint = False
        raise PicklableRemoteTaskError(
            original_type=original_type,
            message=message,
            retryable_hint=retryable_hint,
        ) from None
