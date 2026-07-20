from __future__ import annotations

import re
import secrets
from math import ceil
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.harness.tool_registry import REGISTRY
from ...core.errors import ApiError
from ...models import AgentSkill
from ...models.enums import AgentSkillVisibility
from ...repositories import AgentSkillRepository
from ...schemas.agent_skill import (
    AgentSkillItem,
    CreateAgentSkillRequest,
    ImportAgentSkillResult,
    ImportAgentSkillsRequest,
    ImportAgentSkillsResponse,
    ListAgentSkillsQuery,
    UpdateAgentSkillRequest,
)
from ...schemas.common import PaginatedData, PaginationMeta


class SkillService:
    def __init__(self, *, db: AsyncSession, skills: AgentSkillRepository) -> None:
        self.db = db
        self.skills = skills

    @staticmethod
    def _slugify(text: str) -> str:
        value = (text or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-{2,}", "-", value).strip("-")
        return value or "skill"

    @classmethod
    def _build_user_skill_key(cls, *, user_id: int, name: str, suffix: str) -> str:
        prefix = f"user:{user_id}:"
        slug = cls._slugify(name)
        separator = "-"
        max_slug_len = 120 - len(prefix) - len(suffix) - len(separator)
        if max_slug_len < 1:
            slug = "skill"
        else:
            slug = slug[:max_slug_len].strip("-") or "skill"
        return f"{prefix}{slug}{separator}{suffix}"

    async def _generate_unique_user_skill_key(self, *, user_id: int, name: str) -> str:
        for _ in range(8):
            suffix = secrets.token_hex(3)
            candidate = self._build_user_skill_key(user_id=user_id, name=name, suffix=suffix)
            exists = await self.db.scalar(
                select(AgentSkill.skill_id).where(AgentSkill.skill_key == candidate).limit(1)
            )
            if exists is None:
                return candidate
        raise ApiError(status_code=500, code=500, message="Failed to allocate unique skillKey")

    @staticmethod
    def _coerce_tool_whitelist(raw: Any) -> list[str]:
        if isinstance(raw, list):
            return [str(item) for item in raw if isinstance(item, (str, int, float))]
        return []

    @staticmethod
    def _validate_tool_whitelist(raw: list[str]) -> list[str]:
        tools = [str(item).strip() for item in raw if str(item).strip()]
        unknown = REGISTRY.unknown_names(tools)
        if unknown:
            raise ApiError(
                status_code=422,
                code=422,
                message="Unknown agent tool in toolWhitelist",
                data={"unknownTools": sorted(unknown)},
            )
        return tools

    @classmethod
    def _to_item(cls, entity: AgentSkill) -> AgentSkillItem:
        visibility_value = (
            entity.visibility.value
            if isinstance(entity.visibility, AgentSkillVisibility)
            else str(entity.visibility or AgentSkillVisibility.GLOBAL.value)
        )
        return AgentSkillItem(
            skill_id=str(entity.skill_id),
            skill_key=str(entity.skill_key),
            name=str(entity.name),
            description=str(entity.description),
            triggers_text=entity.triggers_text,
            tool_whitelist=cls._coerce_tool_whitelist(entity.tool_whitelist_json),
            plan_template=dict(entity.plan_template_json or {}),
            inputs_schema=dict(entity.inputs_schema_json or {}),
            outputs_schema=dict(entity.outputs_schema_json or {}),
            visibility=visibility_value,  # type: ignore[arg-type]
            owner_user_id=str(entity.owner_user_id) if entity.owner_user_id is not None else None,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def list_skills(self, *, user_id: int, query: ListAgentSkillsQuery) -> PaginatedData[AgentSkillItem]:
        page = max(1, query.page)
        per_page = max(1, query.per_page)
        offset = (page - 1) * per_page

        items, total_items = await self.skills.list_catalog_paginated(
            user_id=user_id,
            visibility=query.visibility,
            query_text=query.query_text or "",
            page=page,
            per_page=per_page,
        )

        converted: list[AgentSkillItem] = []
        for row in items:
            converted.append(
                AgentSkillItem(
                    skill_id=str(row.skill_id),
                    skill_key=row.skill_key,
                    name=row.name,
                    description=row.description,
                    triggers_text=row.triggers_text,
                    tool_whitelist=self._coerce_tool_whitelist(row.tool_whitelist_json),
                    plan_template=dict(row.plan_template_json or {}),
                    inputs_schema=dict(row.inputs_schema_json or {}),
                    outputs_schema=dict(row.outputs_schema_json or {}),
                    visibility=str(row.visibility),  # type: ignore[arg-type]
                    owner_user_id=str(row.owner_user_id) if row.owner_user_id is not None else None,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )

        pagination = PaginationMeta(
            total_items=total_items,
            total_pages=max(1, ceil(total_items / per_page)) if per_page else 1,
            per_page=per_page,
            current_page=page,
            has_prev=page > 1,
            has_next=(offset + per_page) < total_items,
        )
        return PaginatedData(items=converted, pagination=pagination)

    async def get_skill(self, *, user_id: int, skill_key: str) -> AgentSkillItem:
        entity = await self.skills.get_by_key(skill_key=skill_key, user_id=user_id)
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Skill not found")
        return self._to_item(entity)

    async def create_custom_skill(self, *, user_id: int, payload: CreateAgentSkillRequest) -> AgentSkillItem:
        skill_key = await self._generate_unique_user_skill_key(user_id=user_id, name=payload.name)
        tool_whitelist = self._validate_tool_whitelist(payload.tool_whitelist)
        entity = await self.skills.create(
            values={
                "skill_key": skill_key,
                "name": payload.name,
                "description": payload.description,
                "triggers_text": payload.triggers_text,
                "tool_whitelist_json": tool_whitelist,
                "plan_template_json": payload.plan_template,
                "inputs_schema_json": payload.inputs_schema,
                "outputs_schema_json": payload.outputs_schema,
                "visibility": AgentSkillVisibility.PRIVATE,
                "owner_user_id": user_id,
            }
        )
        await self.db.commit()
        await self.db.refresh(entity)
        return self._to_item(entity)

    async def update_custom_skill(self, *, user_id: int, skill_key: str, payload: UpdateAgentSkillRequest) -> AgentSkillItem:
        entity = await self.db.scalar(
            select(AgentSkill).where(
                AgentSkill.skill_key == skill_key,
                AgentSkill.visibility == AgentSkillVisibility.PRIVATE,
                AgentSkill.owner_user_id == user_id,
            )
        )
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Skill not found")

        values: dict[str, Any] = {}
        fields_set = payload.model_fields_set
        if "name" in fields_set:
            values["name"] = payload.name
        if "description" in fields_set:
            values["description"] = payload.description
        if "triggers_text" in fields_set:
            values["triggers_text"] = payload.triggers_text
        if "tool_whitelist" in fields_set:
            values["tool_whitelist_json"] = self._validate_tool_whitelist(
                payload.tool_whitelist or []
            )
        if "plan_template" in fields_set:
            values["plan_template_json"] = payload.plan_template or {}
        if "inputs_schema" in fields_set:
            values["inputs_schema_json"] = payload.inputs_schema or {}
        if "outputs_schema" in fields_set:
            values["outputs_schema_json"] = payload.outputs_schema or {}

        if values:
            await self.skills.update(entity, values=values)
            await self.db.commit()
            await self.db.refresh(entity)

        return self._to_item(entity)

    async def delete_custom_skill(self, *, user_id: int, skill_key: str) -> None:
        entity = await self.db.scalar(
            select(AgentSkill).where(
                AgentSkill.skill_key == skill_key,
                AgentSkill.visibility == AgentSkillVisibility.PRIVATE,
                AgentSkill.owner_user_id == user_id,
            )
        )
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Skill not found")
        await self.skills.delete(entity)
        await self.db.commit()

    async def import_global_skills(self, *, payload: ImportAgentSkillsRequest) -> ImportAgentSkillsResponse:
        keys = [item.skill_key for item in payload.items]
        if len(set(keys)) != len(keys):
            raise ApiError(status_code=400, code=400, message="Duplicate skillKey in import payload")

        existing_rows: list[AgentSkill] = []
        if keys:
            existing_rows = list(await self.db.scalars(select(AgentSkill).where(AgentSkill.skill_key.in_(keys))))

        existing_by_key = {row.skill_key: row for row in existing_rows}
        conflicts: list[str] = []
        for key, row in existing_by_key.items():
            if row.visibility != AgentSkillVisibility.GLOBAL:
                conflicts.append(key)
            elif payload.mode == "insertOnly":
                conflicts.append(key)
        if conflicts:
            raise ApiError(
                status_code=409,
                code=409,
                message="Skill key conflict",
                data={"conflicts": sorted(conflicts)},
            )

        results: list[ImportAgentSkillResult] = []
        for item in payload.items:
            tool_whitelist = self._validate_tool_whitelist(item.tool_whitelist)
            existing = existing_by_key.get(item.skill_key)
            values = {
                "name": item.name,
                "description": item.description,
                "triggers_text": item.triggers_text,
                "tool_whitelist_json": tool_whitelist,
                "plan_template_json": item.plan_template,
                "inputs_schema_json": item.inputs_schema,
                "outputs_schema_json": item.outputs_schema,
                "visibility": AgentSkillVisibility.GLOBAL,
                "owner_user_id": None,
            }
            if existing is None:
                await self.skills.create(
                    values={
                        "skill_key": item.skill_key,
                        **values,
                    }
                )
                results.append(ImportAgentSkillResult(skill_key=item.skill_key, action="created"))
            else:
                await self.skills.update(existing, values=values)
                results.append(ImportAgentSkillResult(skill_key=item.skill_key, action="updated"))

        await self.db.commit()
        return ImportAgentSkillsResponse(results=results)
