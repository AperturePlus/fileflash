from __future__ import annotations

from typing import Any


class CheckpointStore:
    async def save(self, *args, **kwargs) -> dict[str, Any]:
        raise NotImplementedError("CheckpointStore is scaffolded only in this stage")

    async def load(self, *args, **kwargs) -> dict[str, Any]:
        raise NotImplementedError("CheckpointStore is scaffolded only in this stage")
