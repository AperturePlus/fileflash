from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories import AgentInboxMessageRepository
from .event_bus import AgentEventBus, AgentEventEnvelope, AgentEventStream


class AskTimedOut(Exception):
    def __init__(self, *, ask_id: int) -> None:
        super().__init__(f"Ask {ask_id} timed out")
        self.ask_id = ask_id


class AskProtocol:
    def __init__(
        self,
        *,
        db: AsyncSession,
        event_bus: AgentEventBus,
        job_id: int,
    ) -> None:
        self._db = db
        self._bus = event_bus
        self._job_id = job_id
        self._repo = AgentInboxMessageRepository(db)
        self._waiters: dict[int, asyncio.Future[Any]] = {}
        self._sub_ctx = None
        self._sub_stream: AgentEventStream | None = None
        self._sub_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._sub_ctx = self._bus.subscribe(job_id=self._job_id)
        self._sub_stream = await self._sub_ctx.__aenter__()
        self._sub_task = asyncio.create_task(self._listen())

    async def aclose(self) -> None:
        if self._sub_task is not None:
            self._sub_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sub_task
        if self._sub_ctx is not None:
            await self._sub_ctx.__aexit__(None, None, None)
        for future in self._waiters.values():
            if not future.done():
                future.cancel()

    async def ask(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        timeout_sec: float,
    ) -> Any:
        msg = await self._repo.create_ask(
            job_id=self._job_id,
            payload={"prompt": prompt, "schema": schema, "timeoutSec": timeout_sec},
        )
        await self._db.commit()

        ask_id = int(msg.inbox_message_id)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._waiters[ask_id] = future

        await self._bus.publish(
            AgentEventEnvelope(
                job_id=self._job_id,
                event_type="agent.ask",
                payload={
                    "messageId": str(ask_id),
                    "prompt": prompt,
                    "schema": schema,
                    "timeoutSec": timeout_sec,
                },
                emitted_at=datetime.now(UTC),
            )
        )

        try:
            value = await asyncio.wait_for(future, timeout=timeout_sec)
        except TimeoutError as exc:
            await self._repo.mark_timed_out(
                inbox_message_id=ask_id,
                answered_at=datetime.now(UTC),
            )
            await self._db.commit()
            raise AskTimedOut(ask_id=ask_id) from exc
        finally:
            self._waiters.pop(ask_id, None)

        await self._repo.mark_answered(
            inbox_message_id=ask_id,
            answered_at=datetime.now(UTC),
        )
        await self._db.commit()
        return value

    async def _listen(self) -> None:
        assert self._sub_stream is not None
        while True:
            try:
                envelope = await self._sub_stream.next(timeout=None)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue
            if envelope.event_type != "agent.inbox.reply":
                continue
            reply_to = envelope.payload.get("replyTo")
            if reply_to is None:
                continue
            try:
                ask_id = int(reply_to)
            except (TypeError, ValueError):
                continue
            future = self._waiters.get(ask_id)
            if future is None or future.done():
                continue
            future.set_result(envelope.payload.get("value"))


__all__ = ["AskProtocol", "AskTimedOut"]
