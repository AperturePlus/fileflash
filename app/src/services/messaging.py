from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AuthEvent:
    name: str
    payload: Mapping[str, object]
    created_at: datetime


class AuthEventPublisher(Protocol):
    async def publish(self, event_name: str, payload: Mapping[str, object]) -> None: ...


class InProcessAuthEventPublisher:
    async def publish(self, event_name: str, payload: Mapping[str, object]) -> None:
        event = AuthEvent(name=event_name, payload=payload, created_at=datetime.now(UTC))
        logger.info("Auth event published in-process: %s %s", event.name, dict(event.payload))

