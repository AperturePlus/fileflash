from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentSkill
from ...models.enums import AgentSkillVisibility
from .contracts import AgentSkillCatalogEntry


class AgentSkillRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_visible(self, *, user_id: int | None, limit: int = 50) -> list[AgentSkillCatalogEntry]:
        query = text(
            """
            SELECT
                skill_id,
                skill_key,
                name,
                description,
                triggers_text,
                tool_whitelist_json,
                plan_template_json,
                inputs_schema_json,
                outputs_schema_json,
                visibility,
                owner_user_id,
                created_at,
                updated_at,
                search_text
            FROM v_agent_skill_catalog
            WHERE visibility = 'global'
               OR owner_user_id = CAST(:user_id AS BIGINT)
            ORDER BY CASE WHEN visibility = 'global' THEN 0 ELSE 1 END, created_at DESC
            LIMIT :limit
            """
        )
        result = await self.db.execute(query, {"user_id": user_id, "limit": limit})
        return [AgentSkillCatalogEntry(**row) for row in result.mappings()]

    async def search_visible(self, *, user_id: int | None, query_text: str, limit: int = 20) -> list[AgentSkillCatalogEntry]:
        query = text(
            """
            SELECT
                skill_id,
                skill_key,
                name,
                description,
                triggers_text,
                tool_whitelist_json,
                plan_template_json,
                inputs_schema_json,
                outputs_schema_json,
                visibility,
                owner_user_id,
                created_at,
                updated_at,
                search_text
            FROM v_agent_skill_catalog
            WHERE (visibility = 'global' OR owner_user_id = CAST(:user_id AS BIGINT))
              AND (
                    :query_text = ''
                 OR search_text ILIKE '%' || :query_text || '%'
              )
            ORDER BY CASE WHEN visibility = 'global' THEN 0 ELSE 1 END, created_at DESC
            LIMIT :limit
            """
        )
        result = await self.db.execute(query, {"user_id": user_id, "query_text": query_text.strip(), "limit": limit})
        return [AgentSkillCatalogEntry(**row) for row in result.mappings()]

    async def get_by_key(self, *, skill_key: str, user_id: int | None) -> AgentSkill | None:
        visibility_filter = AgentSkill.visibility == AgentSkillVisibility.GLOBAL
        if user_id is not None:
            visibility_filter = or_(visibility_filter, AgentSkill.owner_user_id == user_id)
        statement = select(AgentSkill).where(
            AgentSkill.skill_key == skill_key,
            visibility_filter,
        )
        return await self.db.scalar(statement)

    async def create(self, *, values: dict[str, Any]) -> AgentSkill:
        entity = AgentSkill(**values)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update(self, entity: AgentSkill, *, values: dict[str, Any]) -> AgentSkill:
        for key, value in values.items():
            setattr(entity, key, value)
        await self.db.flush()
        return entity

    async def delete(self, entity: AgentSkill) -> None:
        await self.db.delete(entity)
        await self.db.flush()

    async def list_catalog_paginated(
        self,
        *,
        user_id: int | None,
        visibility: str = "all",
        query_text: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[AgentSkillCatalogEntry], int]:
        normalized_page = max(1, int(page or 1))
        normalized_per_page = max(1, int(per_page or 20))
        offset = (normalized_page - 1) * normalized_per_page
        query_text = (query_text or "").strip()
        visibility = (visibility or "all").strip() or "all"

        # CAST user_id — asyncpg 无法在「$n IS NOT NULL」分支里推断参数类型
        where_clause = """
            (
                (:visibility = 'global' AND visibility = 'global')
                OR (
                    :visibility = 'private'
                    AND visibility = 'private'
                    AND owner_user_id = CAST(:user_id AS BIGINT)
                )
                OR (
                    :visibility = 'all'
                    AND (
                        visibility = 'global'
                        OR owner_user_id = CAST(:user_id AS BIGINT)
                    )
                )
            )
            AND (
                :query_text = ''
                OR search_text ILIKE '%' || :query_text || '%'
            )
        """

        count_query = text(
            f"""
            SELECT COUNT(*) AS total_items
            FROM v_agent_skill_catalog
            WHERE {where_clause}
            """
        )
        params = {
            "user_id": user_id,
            "visibility": visibility,
            "query_text": query_text,
            "limit": normalized_per_page,
            "offset": offset,
        }
        count_result = await self.db.execute(count_query, params)
        total_items = int(count_result.scalar() or 0)

        list_query = text(
            f"""
            SELECT
                skill_id,
                skill_key,
                name,
                description,
                triggers_text,
                tool_whitelist_json,
                plan_template_json,
                inputs_schema_json,
                outputs_schema_json,
                visibility,
                owner_user_id,
                created_at,
                updated_at,
                search_text
            FROM v_agent_skill_catalog
            WHERE {where_clause}
            ORDER BY CASE WHEN visibility = 'global' THEN 0 ELSE 1 END, created_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        )
        result = await self.db.execute(list_query, params)
        items = [AgentSkillCatalogEntry(**row) for row in result.mappings()]
        return items, total_items
