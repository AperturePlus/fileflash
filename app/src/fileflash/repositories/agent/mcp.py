from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentMcpServer
from ...models.enums import AgentMcpVisibility
from .contracts import AgentMcpCatalogEntry


class AgentMcpRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_visible(self, *, user_id: int | None, enabled_only: bool = False) -> list[AgentMcpCatalogEntry]:
        query = text(
            """
            SELECT
                mcp_server_id,
                name,
                description,
                endpoint,
                transport,
                auth_type,
                headers_json,
                tool_namespace,
                enabled,
                metadata_json,
                visibility,
                owner_user_id,
                created_at,
                updated_at
            FROM v_agent_mcp_catalog
            WHERE (
                    visibility = 'system'
                 OR (:user_id IS NOT NULL AND owner_user_id = :user_id)
                  )
              AND (:enabled_only = FALSE OR enabled = TRUE)
            ORDER BY CASE WHEN visibility = 'system' THEN 0 ELSE 1 END, created_at DESC
            """
        )
        result = await self.db.execute(query, {"user_id": user_id, "enabled_only": enabled_only})
        return [AgentMcpCatalogEntry(**row) for row in result.mappings()]

    async def get_visible_by_id(self, *, mcp_server_id: int, user_id: int | None) -> AgentMcpServer | None:
        visibility_filter = AgentMcpServer.visibility == AgentMcpVisibility.SYSTEM
        if user_id is not None:
            visibility_filter = or_(visibility_filter, AgentMcpServer.owner_user_id == user_id)
        statement = select(AgentMcpServer).where(
            AgentMcpServer.mcp_server_id == mcp_server_id,
            visibility_filter,
        )
        return await self.db.scalar(statement)

    async def create(self, *, values: dict[str, Any]) -> AgentMcpServer:
        entity = AgentMcpServer(**values)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update(self, entity: AgentMcpServer, *, values: dict[str, Any]) -> AgentMcpServer:
        for key, value in values.items():
            setattr(entity, key, value)
        await self.db.flush()
        return entity

    async def delete(self, entity: AgentMcpServer) -> None:
        await self.db.delete(entity)
        await self.db.flush()
