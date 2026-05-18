from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AgentSkillCatalogEntry:
    skill_id: int
    skill_key: str
    name: str
    description: str
    triggers_text: str | None
    tool_whitelist_json: list[Any] | dict[str, Any]
    plan_template_json: dict[str, Any]
    inputs_schema_json: dict[str, Any]
    outputs_schema_json: dict[str, Any]
    visibility: str
    owner_user_id: int | None
    created_at: datetime
    updated_at: datetime
    search_text: str


@dataclass(slots=True)
class AgentMcpCatalogEntry:
    mcp_server_id: int
    name: str
    description: str | None
    endpoint: str
    transport: str
    auth_type: str
    headers_json: dict[str, Any]
    tool_namespace: str | None
    enabled: bool
    metadata_json: dict[str, Any]
    visibility: str
    owner_user_id: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class AgentMemoryActiveEntry:
    memory_id: int
    user_id: int
    scope: str
    scope_key: str | None
    kind: str
    title: str
    content: str
    source_job_id: int | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
