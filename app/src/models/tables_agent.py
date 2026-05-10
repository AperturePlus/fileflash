from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import (
    AgentExecutionPolicy,
    AgentMcpVisibility,
    AgentMemoryKind,
    AgentMemoryScope,
    AgentSkillVisibility,
)
from .pg import pg_enum


class AgentUserSetting(Base):
    __tablename__ = "agent_user_setting"
    __table_args__ = (
        Index("idx_agent_user_setting_user_id", "user_id"),
    )

    setting_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    default_execution_policy: Mapped[AgentExecutionPolicy] = mapped_column(
        pg_enum(AgentExecutionPolicy, "agent_execution_policy_enum"),
        nullable=False,
        server_default=text("'confirm'"),
    )
    default_data_policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_model: Mapped[str | None] = mapped_column(String(100))
    default_budget_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("20000"))
    default_max_steps: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("20"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AgentMcpServer(Base):
    __tablename__ = "agent_mcp_server"
    __table_args__ = (
        Index("idx_agent_mcp_server_visibility_enabled", "visibility", "enabled"),
        Index("idx_agent_mcp_server_owner_visibility", "owner_user_id", "visibility"),
    )

    mcp_server_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
    )
    visibility: Mapped[AgentMcpVisibility] = mapped_column(
        pg_enum(AgentMcpVisibility, "agent_mcp_visibility_enum"),
        nullable=False,
        server_default=text("'system'"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    transport: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'streamable_http'"))
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'none'"))
    headers_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    tool_namespace: Mapped[str | None] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AgentSkill(Base):
    __tablename__ = "agent_skill"
    __table_args__ = (
        Index("idx_agent_skill_visibility_created_at", "visibility", text("created_at DESC")),
        Index("idx_agent_skill_owner_visibility", "owner_user_id", "visibility"),
        UniqueConstraint("skill_key", name="uk_agent_skill_skill_key"),
    )

    skill_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    skill_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    triggers_text: Mapped[str | None] = mapped_column(Text)
    tool_whitelist_json: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    plan_template_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    inputs_schema_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    outputs_schema_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    visibility: Mapped[AgentSkillVisibility] = mapped_column(
        pg_enum(AgentSkillVisibility, "agent_skill_visibility_enum"),
        nullable=False,
        server_default=text("'global'"),
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AgentMemory(Base):
    __tablename__ = "agent_memory"
    __table_args__ = (
        Index("idx_agent_memory_user_scope", "user_id", "scope", "scope_key"),
        Index("idx_agent_memory_user_expires", "user_id", "expires_at"),
    )

    memory_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[AgentMemoryScope] = mapped_column(
        pg_enum(AgentMemoryScope, "agent_memory_scope_enum"),
        nullable=False,
    )
    scope_key: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[AgentMemoryKind] = mapped_column(
        pg_enum(AgentMemoryKind, "agent_memory_kind_enum"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_job_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("background_job.job_id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)


class AgentPlan(Base):
    __tablename__ = "agent_plan"
    __table_args__ = (
        Index("idx_agent_plan_user_created_at", "user_id", text("created_at DESC")),
        Index("idx_agent_plan_plan_hash", "plan_hash"),
    )

    plan_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("background_job.job_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    execution_policy: Mapped[AgentExecutionPolicy] = mapped_column(
        pg_enum(AgentExecutionPolicy, "agent_execution_policy_enum"),
        nullable=False,
    )
    data_policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    chosen_skill_id: Mapped[str | None] = mapped_column(String(120))
    proposed_actions_json: Mapped[list[Any] | dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    plan_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    cost_estimate_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AgentActionLog(Base):
    __tablename__ = "agent_action_log"
    __table_args__ = (
        Index("idx_agent_action_log_job_started_at", "job_id", "started_at"),
        Index("idx_agent_action_log_job_status", "job_id", "status"),
        UniqueConstraint("job_id", "step_no", name="uk_agent_action_log_job_step"),
    )

    action_log_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("background_job.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    outputs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class AgentWorkSession(Base):
    __tablename__ = "agent_work_session"
    __table_args__ = (
        Index("idx_agent_work_session_user_status", "user_id", "status"),
        Index("idx_agent_work_session_created_at", text("created_at DESC")),
    )

    work_session_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("background_job.job_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    checkpoint_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    checkpoint_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_checkpoint_at: Mapped[datetime | None] = mapped_column(DateTime)
    tool_call_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_tool_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_tool_finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)


__all__ = [
    "AgentActionLog",
    "AgentMcpServer",
    "AgentMemory",
    "AgentPlan",
    "AgentSkill",
    "AgentUserSetting",
    "AgentWorkSession",
]
