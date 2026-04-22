from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .common import CamelModel, PageQuery

AgentSkillVisibility = Literal["global", "private"]
AgentSkillListVisibility = Literal["all", "global", "private"]
ImportAgentSkillMode = Literal["upsert", "insertOnly"]


class AgentSkillItem(CamelModel):
    skill_id: str
    skill_key: str
    name: str
    description: str
    triggers_text: str | None = None
    tool_whitelist: list[str] = Field(default_factory=list)
    plan_template: dict[str, Any] = Field(default_factory=dict)
    inputs_schema: dict[str, Any] = Field(default_factory=dict)
    outputs_schema: dict[str, Any] = Field(default_factory=dict)
    visibility: AgentSkillVisibility
    owner_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ListAgentSkillsQuery(PageQuery):
    visibility: AgentSkillListVisibility = "all"
    query_text: str | None = None


class CreateAgentSkillRequest(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    triggers_text: str | None = None
    tool_whitelist: list[str] = Field(default_factory=list)
    plan_template: dict[str, Any] = Field(default_factory=dict)
    inputs_schema: dict[str, Any] = Field(default_factory=dict)
    outputs_schema: dict[str, Any] = Field(default_factory=dict)


class UpdateAgentSkillRequest(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1)
    triggers_text: str | None = None
    tool_whitelist: list[str] | None = None
    plan_template: dict[str, Any] | None = None
    inputs_schema: dict[str, Any] | None = None
    outputs_schema: dict[str, Any] | None = None


class ImportAgentSkillItem(CamelModel):
    skill_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    triggers_text: str | None = None
    tool_whitelist: list[str] = Field(default_factory=list)
    plan_template: dict[str, Any] = Field(default_factory=dict)
    inputs_schema: dict[str, Any] = Field(default_factory=dict)
    outputs_schema: dict[str, Any] = Field(default_factory=dict)


class ImportAgentSkillsRequest(CamelModel):
    mode: ImportAgentSkillMode = "upsert"
    items: list[ImportAgentSkillItem] = Field(min_length=1)


class ImportAgentSkillResult(CamelModel):
    skill_key: str
    action: Literal["created", "updated"]


class ImportAgentSkillsResponse(CamelModel):
    results: list[ImportAgentSkillResult]

