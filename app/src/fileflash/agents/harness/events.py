from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AgentEvent:
    event_type: str
    payload: dict[str, Any]


class EventBus:
    async def publish(self, event: AgentEvent) -> None:
        raise NotImplementedError("EventBus is scaffolded only in this stage")
