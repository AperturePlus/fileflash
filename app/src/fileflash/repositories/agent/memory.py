from __future__ import annotations

from typing import Any

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentMemory
from .contracts import AgentMemoryActiveEntry


class AgentMemoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(
        self,
        *,
        user_id: int,
        scope: str | None = None,
        scope_key: str | None = None,
        limit: int = 100,
    ) -> list[AgentMemoryActiveEntry]:
        query = text(
            """
            SELECT
                memory_id,
                user_id,
                scope,
                scope_key,
                kind,
                title,
                content,
                source_job_id,
                created_at,
                updated_at,
                expires_at
            FROM v_agent_memory_active
            WHERE user_id = :user_id
              AND (:scope IS NULL OR scope = :scope)
              AND (:scope_key IS NULL OR scope_key = :scope_key)
            ORDER BY updated_at DESC, memory_id DESC
            LIMIT :limit
            """
        )
        result = await self.db.execute(
            query,
            {"user_id": user_id, "scope": scope, "scope_key": scope_key, "limit": limit},
        )
        return [AgentMemoryActiveEntry(**row) for row in result.mappings()]

    async def search_active(
        self,
        *,
        user_id: int,
        query_text: str,
        scope: str | None = None,
        scope_key: str | None = None,
        limit: int = 20,
    ) -> list[AgentMemoryActiveEntry]:
        query = text(
            """
            SELECT
                memory_id,
                user_id,
                scope,
                scope_key,
                kind,
                title,
                content,
                source_job_id,
                created_at,
                updated_at,
                expires_at
            FROM v_agent_memory_active
            WHERE user_id = :user_id
              AND (:scope IS NULL OR scope = :scope)
              AND (:scope_key IS NULL OR scope_key = :scope_key)
              AND (
                    :query_text = ''
                 OR title ILIKE '%' || :query_text || '%'
                 OR content ILIKE '%' || :query_text || '%'
              )
            ORDER BY updated_at DESC, memory_id DESC
            LIMIT :limit
            """
        )
        result = await self.db.execute(
            query,
            {
                "user_id": user_id,
                "scope": scope,
                "scope_key": scope_key,
                "query_text": query_text.strip(),
                "limit": limit,
            },
        )
        return [AgentMemoryActiveEntry(**row) for row in result.mappings()]

    async def create(self, *, values: dict[str, Any]) -> AgentMemory:
        entity = AgentMemory(**values)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def delete(self, *, memory_id: int, user_id: int) -> int:
        result = await self.db.execute(
            delete(AgentMemory).where(
                AgentMemory.memory_id == memory_id,
                AgentMemory.user_id == user_id,
            )
        )
        await self.db.flush()
        return int(result.rowcount or 0)
