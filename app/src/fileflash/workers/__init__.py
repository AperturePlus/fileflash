from __future__ import annotations

from typing import Any

__all__ = ["WorkerConsumer", "run_worker"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from .consumer import WorkerConsumer, run_worker

        exports = {
            "WorkerConsumer": WorkerConsumer,
            "run_worker": run_worker,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
