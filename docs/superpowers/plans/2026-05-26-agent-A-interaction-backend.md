# Agent 子项目 A（交互/反馈层）— 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 agent 后端从单向 SSE + DB 轮询升级为 Redis pub/sub 推送 + POST inbox 双向通道，支持 `agent.ask` / `agent.progress` / `agent.thinking` / `tool.partial` 等新事件，以及 pause/resume/skip/approve/cancel 等控制信号在 step 边界生效。

**Architecture:** 新增 `AgentEventBus`（Redis pub/sub 封装）、`AgentInboxMessage` 表 + repository、`AgentInbox` 服务、`AskProtocol` 协议三大单元；SSE 端点从轮询 DB 改为订阅 Redis channel；ExecuteRunner / PlanRunner 在 step 边界检查 inbox。前端最小接入留给前端 plan。

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy async + Redis pub/sub (`redis.asyncio`) + Flyway SQL 迁移 + pytest + 既有 stub 风格测试（不引入 fakeredis）。

**Spec:** `docs/superpowers/specs/2026-05-26-agent-improvements-design.md` 子项目 A 部分

---

## File Structure

**新建（src）**

- `app/src/fileflash/agents/harness/event_bus.py` — `AgentEventBus`（publish + subscribe）+ 内存 stub 用于测试
- `app/src/fileflash/agents/harness/inbox.py` — `AgentInbox` 服务（写表 + publish）
- `app/src/fileflash/agents/harness/ask.py` — `AskProtocol` 协议（创建 ask 消息、阻塞等回答）
- `app/src/fileflash/repositories/agent/inbox.py` — `AgentInboxMessageRepository`

**新建（迁移）**

- `docker/flyway/migrations/V14__agent_inbox.sql` — `AgentInboxMessage` 表 + enum 类型

**修改**

- `app/src/fileflash/models/enums.py` — 新增 `AgentInboxRole` / `AgentInboxKind` / `AgentInboxStatus`
- `app/src/fileflash/models/tables_agent.py` — 新增 `AgentInboxMessage` ORM model
- `app/src/fileflash/models/__init__.py` — 导出 `AgentInboxMessage`
- `app/src/fileflash/repositories/__init__.py` — 导出 `AgentInboxMessageRepository`
- `app/src/fileflash/schemas/agent.py` — 新事件类型字面量 + 上行 message 类型
- `app/src/fileflash/routers/agent.py` — 新增 `POST /agent/jobs/{id}/messages`、改 SSE 实现、删除 `POST /agent/cancel/{job_id}`
- `app/src/fileflash/agents/runtime/execute_runner.py` — step 边界检查 inbox（pause/resume/cancel/skip/approve）+ publish 工具事件
- `app/src/fileflash/agents/runtime/plan_runner.py` — 接入 ask 协议
- `app/src/fileflash/agents/worker.py` — 创建 EventBus 单例并下发到 runner
- `app/src/fileflash/core/settings.py` — 增 `agent_inbox_ask_timeout_sec`（默认 1800）+ Redis pub/sub channel 配置项
- `app/src/fileflash/core/deps.py` — 注入 `AgentEventBus` 依赖

**测试**

- `app/tests/test_agent_event_bus.py` — 新
- `app/tests/test_agent_inbox.py` — 新
- `app/tests/test_agent_ask_protocol.py` — 新
- `app/tests/test_agent_routes.py` — 扩展
- `app/tests/test_agent_plan_execute_runtime.py` — 扩展

**前端**

不在本 plan 范围。参见 `2026-05-26-agent-A-interaction-frontend.md`。本 plan 完成后，后端通过 curl/httpx 集成测试可以独立验证。

---

## Sequencing

```
Task 1 (settings) ──► Task 2 (enums) ──► Task 3 (SQL 迁移) ──► Task 4 (ORM model)
                                                                       │
                                              ┌────────────────────────┘
                                              ▼
                                  Task 5 (repository)
                                              │
       ┌──────────────────────────────────────┼─────────────────────────┐
       ▼                                       ▼                         ▼
Task 6 (schemas)                Task 7 (EventBus)               Task 8 (Inbox service)
                                                                          │
                                                                          ▼
                                                                  Task 9 (Ask protocol)
                                                                          │
                                                ┌─────────────────────────┘
                                                ▼
                                  Task 10 (POST /messages 路由)
                                                │
                                                ▼
                                  Task 11 (SSE 改 EventBus subscribe)
                                                │
                                                ▼
                                  Task 12 (删 POST /cancel)
                                                │
                                                ▼
                                  Task 13 (ExecuteRunner 接 inbox)
                                                │
                                                ▼
                                  Task 14 (PlanRunner 接 ask)
                                                │
                                                ▼
                                  Task 15 (worker 装配)
                                                │
                                                ▼
                                  Task 16 (端到端集成测试)
```

---

## Task 1: 配置项与依赖

**Files:**

- Modify: `app/src/fileflash/core/settings.py`

- [ ] **Step 1: 在 `Settings` 类合适位置（紧跟 `redis_url` 之后）增加 4 个配置项**

```python
    agent_inbox_ask_timeout_sec: int = Field(
        default=1800,
        alias="AGENT_INBOX_ASK_TIMEOUT_SEC",
    )
    agent_event_channel_prefix: str = Field(
        default="agent:job",
        alias="AGENT_EVENT_CHANNEL_PREFIX",
    )
    agent_inbox_channel_prefix: str = Field(
        default="agent:inbox",
        alias="AGENT_INBOX_CHANNEL_PREFIX",
    )
    agent_event_bus_buffer_size: int = Field(
        default=64,
        alias="AGENT_EVENT_BUS_BUFFER_SIZE",
    )
```

- [ ] **Step 2: 删除既有 `routers/agent.py` 顶部的 `AGENT_EVENT_POLL_INTERVAL_SEC` 常量（line 22）。如果还有其它文件引用此常量，先用 Grep 确认无引用再删。**

Run: `grep -rn "AGENT_EVENT_POLL_INTERVAL_SEC" app/src/ app/tests/`
Expected: 仅 `routers/agent.py:22` 一处定义、`_event_stream` 内一处引用。

- [ ] **Step 3: Commit**

```bash
git add app/src/fileflash/core/settings.py
git commit -m "feat(agent): add inbox + event bus settings"
```

---

## Task 2: 新增 inbox 相关枚举

**Files:**

- Modify: `app/src/fileflash/models/enums.py`

- [ ] **Step 1: 在 `AgentMcpVisibility` 之后追加三个枚举**

```python
class AgentInboxRole(BaseStrEnum):
    AGENT = "agent"
    USER = "user"


class AgentInboxKind(BaseStrEnum):
    ASK = "ask"
    REPLY = "reply"
    CONTROL_PAUSE = "control.pause"
    CONTROL_RESUME = "control.resume"
    CONTROL_APPROVE = "control.approve"
    CONTROL_DENY = "control.deny"
    CONTROL_SKIP = "control.skip"
    CONTROL_CANCEL = "control.cancel"


class AgentInboxStatus(BaseStrEnum):
    WAITING = "waiting"
    ANSWERED = "answered"
    TIMED_OUT = "timed_out"
    DROPPED = "dropped"
```

- [ ] **Step 2: 把上面三个名字加到 `__all__` 末尾**

```python
__all__ = [
    # ... existing entries ...
    "AgentInboxRole",
    "AgentInboxKind",
    "AgentInboxStatus",
]
```

- [ ] **Step 3: Commit**

```bash
git add app/src/fileflash/models/enums.py
git commit -m "feat(agent): add inbox role/kind/status enums"
```

---

## Task 3: Flyway 迁移 V14（新表 + pg enums）

**Files:**

- Create: `docker/flyway/migrations/V14__agent_inbox.sql`

- [ ] **Step 1: 写完整 SQL 迁移**

```sql
-- =========================
-- Domain: agent inbox
-- =========================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_inbox_role_enum') THEN
        CREATE TYPE agent_inbox_role_enum AS ENUM ('agent', 'user');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_inbox_kind_enum') THEN
        CREATE TYPE agent_inbox_kind_enum AS ENUM (
            'ask',
            'reply',
            'control.pause',
            'control.resume',
            'control.approve',
            'control.deny',
            'control.skip',
            'control.cancel'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_inbox_status_enum') THEN
        CREATE TYPE agent_inbox_status_enum AS ENUM ('waiting', 'answered', 'timed_out', 'dropped');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS agent_inbox_message (
    inbox_message_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    job_id BIGINT NOT NULL,
    role agent_inbox_role_enum NOT NULL,
    kind agent_inbox_kind_enum NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reply_to_id BIGINT NULL,
    status agent_inbox_status_enum NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    answered_at TIMESTAMP NULL,
    CONSTRAINT fk_agent_inbox_message_job
        FOREIGN KEY (job_id) REFERENCES background_job(job_id) ON DELETE CASCADE,
    CONSTRAINT fk_agent_inbox_message_reply_to
        FOREIGN KEY (reply_to_id) REFERENCES agent_inbox_message(inbox_message_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_inbox_message_job_created
    ON agent_inbox_message (job_id, created_at);

CREATE INDEX IF NOT EXISTS idx_agent_inbox_message_job_status
    ON agent_inbox_message (job_id, status)
    WHERE status IS NOT NULL;
```

- [ ] **Step 2: 在本地 PostgreSQL 应用迁移（按既有 Flyway 流程）**

Run: `docker compose -f docker/compose.yml up flyway --build` 或项目既有 migration 命令。
Expected: V14 标记为 success；`\dt agent_inbox_message` 在 psql 中能看到新表。

- [ ] **Step 3: Commit**

```bash
git add docker/flyway/migrations/V14__agent_inbox.sql
git commit -m "feat(agent): V14 add agent_inbox_message table"
```

---

## Task 4: ORM model `AgentInboxMessage`

**Files:**

- Modify: `app/src/fileflash/models/tables_agent.py`
- Modify: `app/src/fileflash/models/__init__.py`

- [ ] **Step 1: 在 `tables_agent.py` 顶部导入区追加**

```python
from .enums import (
    AgentExecutionPolicy,
    AgentInboxKind,
    AgentInboxRole,
    AgentInboxStatus,
    AgentMcpVisibility,
    AgentMemoryKind,
    AgentMemoryScope,
    AgentSkillVisibility,
)
```

- [ ] **Step 2: 在 `AgentWorkSession` 类之后追加 `AgentInboxMessage` 类**

```python
class AgentInboxMessage(Base):
    __tablename__ = "agent_inbox_message"
    __table_args__ = (
        Index("idx_agent_inbox_message_job_created", "job_id", "created_at"),
        Index(
            "idx_agent_inbox_message_job_status",
            "job_id",
            "status",
            postgresql_where=text("status IS NOT NULL"),
        ),
    )

    inbox_message_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("background_job.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[AgentInboxRole] = mapped_column(
        pg_enum(AgentInboxRole, "agent_inbox_role_enum"),
        nullable=False,
    )
    kind: Mapped[AgentInboxKind] = mapped_column(
        pg_enum(AgentInboxKind, "agent_inbox_kind_enum"),
        nullable=False,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    reply_to_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("agent_inbox_message.inbox_message_id", ondelete="SET NULL"),
    )
    status: Mapped[AgentInboxStatus | None] = mapped_column(
        pg_enum(AgentInboxStatus, "agent_inbox_status_enum"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime)
```

- [ ] **Step 3: 把 `AgentInboxMessage` 加到 `__all__` 末尾，并在 `app/src/fileflash/models/__init__.py` 导出**

```python
# tables_agent.py __all__
__all__ = [
    "AgentActionLog",
    "AgentInboxMessage",
    "AgentMcpServer",
    "AgentMemory",
    "AgentPlan",
    "AgentSkill",
    "AgentUserSetting",
    "AgentWorkSession",
]
```

- [ ] **Step 4: 写最小 sanity 测试，确认 model 能与 DB 通信**

新建 `app/tests/test_agent_inbox_model.py`：

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from fileflash.models import AgentInboxMessage, BackgroundJob
from fileflash.models.enums import AgentInboxKind, AgentInboxRole, AgentInboxStatus


@pytest.mark.asyncio
async def test_insert_ask_message_round_trip(db_session, sample_background_job):  # noqa: ANN001
    msg = AgentInboxMessage(
        job_id=sample_background_job.job_id,
        role=AgentInboxRole.AGENT,
        kind=AgentInboxKind.ASK,
        payload_json={"prompt": "which one?", "schema": {}},
        status=AgentInboxStatus.WAITING,
        created_at=datetime.now(UTC),
    )
    db_session.add(msg)
    await db_session.commit()
    fetched = await db_session.scalar(select(AgentInboxMessage).where(
        AgentInboxMessage.inbox_message_id == msg.inbox_message_id
    ))
    assert fetched is not None
    assert fetched.kind == AgentInboxKind.ASK
    assert fetched.status == AgentInboxStatus.WAITING
    assert fetched.payload_json["prompt"] == "which one?"
```

> 注：`db_session` / `sample_background_job` 是项目既有 pytest fixture（参见 `app/tests/test_agent_repositories.py`）。如名字不一致，沿用该测试文件里的 fixture 名。

- [ ] **Step 5: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_inbox_model.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/src/fileflash/models/tables_agent.py app/src/fileflash/models/__init__.py app/tests/test_agent_inbox_model.py
git commit -m "feat(agent): add AgentInboxMessage ORM model"
```

---

## Task 5: `AgentInboxMessageRepository`

**Files:**

- Create: `app/src/fileflash/repositories/agent/inbox.py`
- Modify: `app/src/fileflash/repositories/__init__.py`
- Create: `app/tests/test_agent_inbox_repository.py`

- [ ] **Step 1: 写测试（先 fail）**

```python
# app/tests/test_agent_inbox_repository.py
from datetime import UTC, datetime

import pytest

from fileflash.models.enums import AgentInboxKind, AgentInboxRole, AgentInboxStatus
from fileflash.repositories import AgentInboxMessageRepository


@pytest.mark.asyncio
async def test_create_ask_then_record_reply(db_session, sample_background_job):  # noqa: ANN001
    repo = AgentInboxMessageRepository(db_session)
    ask = await repo.create_ask(
        job_id=int(sample_background_job.job_id),
        payload={"prompt": "choose", "schema": {"choice": ["A", "B"]}},
    )
    await db_session.commit()
    assert ask.status == AgentInboxStatus.WAITING
    assert ask.role == AgentInboxRole.AGENT
    assert ask.kind == AgentInboxKind.ASK

    reply = await repo.record_user_message(
        job_id=int(sample_background_job.job_id),
        kind=AgentInboxKind.REPLY,
        payload={"value": "A"},
        reply_to_id=int(ask.inbox_message_id),
    )
    await db_session.commit()
    assert reply.role == AgentInboxRole.USER
    assert reply.reply_to_id == ask.inbox_message_id

    answered = await repo.mark_answered(
        inbox_message_id=int(ask.inbox_message_id),
        answered_at=datetime.now(UTC),
    )
    await db_session.commit()
    assert answered.status == AgentInboxStatus.ANSWERED
    assert answered.answered_at is not None


@pytest.mark.asyncio
async def test_pending_controls_excludes_consumed(db_session, sample_background_job):  # noqa: ANN001
    repo = AgentInboxMessageRepository(db_session)
    pause = await repo.record_user_message(
        job_id=int(sample_background_job.job_id),
        kind=AgentInboxKind.CONTROL_PAUSE,
        payload={},
    )
    await db_session.commit()

    pending = await repo.list_pending_controls(job_id=int(sample_background_job.job_id))
    assert [m.inbox_message_id for m in pending] == [pause.inbox_message_id]

    await repo.mark_dropped(inbox_message_id=int(pause.inbox_message_id))
    await db_session.commit()
    pending_after = await repo.list_pending_controls(job_id=int(sample_background_job.job_id))
    assert pending_after == []
```

- [ ] **Step 2: 运行测试，确认 fail**

Run: `cd app && uv run pytest tests/test_agent_inbox_repository.py -v`
Expected: FAIL — `AgentInboxMessageRepository` not exported.

- [ ] **Step 3: 实现 repository**

`app/src/fileflash/repositories/agent/inbox.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentInboxMessage
from ...models.enums import AgentInboxKind, AgentInboxRole, AgentInboxStatus

_CONTROL_KINDS = frozenset(
    {
        AgentInboxKind.CONTROL_PAUSE,
        AgentInboxKind.CONTROL_RESUME,
        AgentInboxKind.CONTROL_APPROVE,
        AgentInboxKind.CONTROL_DENY,
        AgentInboxKind.CONTROL_SKIP,
        AgentInboxKind.CONTROL_CANCEL,
    }
)


class AgentInboxMessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_ask(
        self,
        *,
        job_id: int,
        payload: dict[str, Any],
    ) -> AgentInboxMessage:
        msg = AgentInboxMessage(
            job_id=job_id,
            role=AgentInboxRole.AGENT,
            kind=AgentInboxKind.ASK,
            payload_json=payload,
            status=AgentInboxStatus.WAITING,
            created_at=datetime.now(UTC),
        )
        self._db.add(msg)
        await self._db.flush()
        return msg

    async def record_user_message(
        self,
        *,
        job_id: int,
        kind: AgentInboxKind,
        payload: dict[str, Any],
        reply_to_id: int | None = None,
    ) -> AgentInboxMessage:
        msg = AgentInboxMessage(
            job_id=job_id,
            role=AgentInboxRole.USER,
            kind=kind,
            payload_json=payload,
            reply_to_id=reply_to_id,
            status=None,
            created_at=datetime.now(UTC),
        )
        self._db.add(msg)
        await self._db.flush()
        return msg

    async def mark_answered(
        self,
        *,
        inbox_message_id: int,
        answered_at: datetime,
    ) -> AgentInboxMessage:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None:
            raise ValueError(f"AgentInboxMessage {inbox_message_id} not found")
        msg.status = AgentInboxStatus.ANSWERED
        msg.answered_at = answered_at
        await self._db.flush()
        return msg

    async def mark_dropped(self, *, inbox_message_id: int) -> None:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None:
            return
        if msg.kind in _CONTROL_KINDS:
            msg.status = AgentInboxStatus.DROPPED
            msg.answered_at = datetime.now(UTC)
        await self._db.flush()

    async def get_ask(self, *, inbox_message_id: int) -> AgentInboxMessage | None:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None or msg.kind != AgentInboxKind.ASK:
            return None
        return msg

    async def get_reply_for(self, *, ask_id: int) -> AgentInboxMessage | None:
        return await self._db.scalar(
            select(AgentInboxMessage).where(
                and_(
                    AgentInboxMessage.reply_to_id == ask_id,
                    AgentInboxMessage.kind == AgentInboxKind.REPLY,
                )
            )
        )

    async def list_pending_controls(self, *, job_id: int) -> list[AgentInboxMessage]:
        rows = await self._db.scalars(
            select(AgentInboxMessage)
            .where(
                and_(
                    AgentInboxMessage.job_id == job_id,
                    AgentInboxMessage.role == AgentInboxRole.USER,
                    AgentInboxMessage.kind.in_(list(_CONTROL_KINDS)),
                    AgentInboxMessage.status.is_(None),
                )
            )
            .order_by(AgentInboxMessage.created_at.asc())
        )
        return list(rows)
```

> 注：control 消息以"`status IS NULL` 表示未消费"为约定；worker 处理完后调 `mark_dropped`（命名只表"已消费、不再有效"，不代表用户错误）。Reply 消息保持 `status IS NULL`，由 `mark_answered` 处理对应的 ask。

- [ ] **Step 4: 导出**

`app/src/fileflash/repositories/__init__.py`：在合适位置新增

```python
from .agent.inbox import AgentInboxMessageRepository

__all__ = [
    # ... existing entries ...
    "AgentInboxMessageRepository",
]
```

- [ ] **Step 5: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_inbox_repository.py -v`
Expected: PASS（2 个用例）

- [ ] **Step 6: Commit**

```bash
git add app/src/fileflash/repositories/agent/inbox.py app/src/fileflash/repositories/__init__.py app/tests/test_agent_inbox_repository.py
git commit -m "feat(agent): add AgentInboxMessageRepository"
```

---

## Task 6: 新事件类型与上行 message schemas

**Files:**

- Modify: `app/src/fileflash/schemas/agent.py`

- [ ] **Step 1: 扩展 `AgentJobEventType` 字面量与新增上行 message 模型**

把 `AgentJobEventType` 改为：

```python
AgentJobEventType = Literal[
    "job.queued",
    "job.running",
    "plan.ready",
    "tool.started",
    "tool.succeeded",
    "tool.failed",
    "tool.partial",
    "agent.thinking",
    "agent.progress",
    "agent.ask",
    "agent.paused",
    "agent.resumed",
    "job.succeeded",
    "job.failed",
    "job.canceled",
]
```

在文件末尾（`__all__` 之前）新增：

```python
AgentInboxMessageKind = Literal[
    "reply",
    "control.pause",
    "control.resume",
    "control.approve",
    "control.deny",
    "control.skip",
    "control.cancel",
]


class AgentInboxMessageRequest(CamelModel):
    kind: AgentInboxMessageKind
    reply_to: str | None = None              # ask 的 inbox_message_id（str-encoded）
    value: Any = None                        # reply 时为用户回答；control 时通常 None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentInboxMessageResponse(CamelModel):
    inbox_message_id: str
    kind: AgentInboxMessageKind
    accepted_at: datetime
```

把这两个名字加入 `__all__`。

- [ ] **Step 2: 写最小验证测试**

新建 `app/tests/test_agent_inbox_schema.py`：

```python
import pytest
from pydantic import ValidationError

from fileflash.schemas.agent import AgentInboxMessageRequest


def test_reply_with_value_validates() -> None:
    msg = AgentInboxMessageRequest.model_validate(
        {"kind": "reply", "replyTo": "42", "value": "yes"}
    )
    assert msg.kind == "reply"
    assert msg.reply_to == "42"
    assert msg.value == "yes"


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentInboxMessageRequest.model_validate({"kind": "control.explode"})
```

- [ ] **Step 3: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_inbox_schema.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add app/src/fileflash/schemas/agent.py app/tests/test_agent_inbox_schema.py
git commit -m "feat(agent): extend job event types and add inbox message schemas"
```

---

## Task 7: `AgentEventBus`（Redis pub/sub 封装）

**Files:**

- Create: `app/src/fileflash/agents/harness/event_bus.py`
- Modify: `app/src/fileflash/agents/harness/events.py` — 保留 `AgentEvent`，删除 `EventBus` scaffold
- Create: `app/tests/test_agent_event_bus.py`

- [ ] **Step 1: 写测试（先 fail）**

```python
# app/tests/test_agent_event_bus.py
from datetime import UTC, datetime

import pytest

from fileflash.agents.harness.event_bus import (
    AgentEventEnvelope,
    InMemoryAgentEventBus,
)


@pytest.mark.asyncio
async def test_subscriber_receives_published_event() -> None:
    bus = InMemoryAgentEventBus()
    envelope = AgentEventEnvelope(
        job_id=42,
        event_type="agent.ask",
        payload={"prompt": "choose"},
        emitted_at=datetime.now(UTC),
    )
    async with bus.subscribe(job_id=42) as stream:
        await bus.publish(envelope)
        received = await stream.next(timeout=1.0)
    assert received == envelope


@pytest.mark.asyncio
async def test_only_subscribers_of_same_job_receive() -> None:
    bus = InMemoryAgentEventBus()
    own = AgentEventEnvelope(job_id=1, event_type="job.running", payload={}, emitted_at=datetime.now(UTC))
    other = AgentEventEnvelope(job_id=2, event_type="job.running", payload={}, emitted_at=datetime.now(UTC))
    async with bus.subscribe(job_id=1) as stream:
        await bus.publish(other)
        await bus.publish(own)
        first = await stream.next(timeout=1.0)
    assert first == own


@pytest.mark.asyncio
async def test_close_subscriber_unblocks() -> None:
    bus = InMemoryAgentEventBus()
    async with bus.subscribe(job_id=7) as stream:
        with pytest.raises(TimeoutError):
            await stream.next(timeout=0.1)
```

- [ ] **Step 2: 运行测试，确认 fail**

Run: `cd app && uv run pytest tests/test_agent_event_bus.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: 实现 `event_bus.py`**

```python
# app/src/fileflash/agents/harness/event_bus.py
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol

from redis.asyncio import Redis

from ...core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentEventEnvelope:
    job_id: int
    event_type: str
    payload: dict[str, Any]
    emitted_at: datetime
    event_id: str | None = None

    def to_json(self) -> str:
        body = asdict(self)
        body["emitted_at"] = self.emitted_at.isoformat()
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> "AgentEventEnvelope":
        data = json.loads(raw)
        return cls(
            job_id=int(data["job_id"]),
            event_type=str(data["event_type"]),
            payload=dict(data.get("payload") or {}),
            emitted_at=datetime.fromisoformat(data["emitted_at"]),
            event_id=data.get("event_id"),
        )


class AgentEventStream(Protocol):
    async def next(self, *, timeout: float | None = None) -> AgentEventEnvelope: ...
    async def aclose(self) -> None: ...


class AgentEventBus(Protocol):
    async def publish(self, envelope: AgentEventEnvelope) -> None: ...
    def subscribe(self, *, job_id: int) -> "AgentEventSubscription": ...


@dataclass(slots=True)
class _InMemoryStream:
    queue: asyncio.Queue[AgentEventEnvelope]

    async def next(self, *, timeout: float | None = None) -> AgentEventEnvelope:
        if timeout is None:
            return await self.queue.get()
        return await asyncio.wait_for(self.queue.get(), timeout=timeout)

    async def aclose(self) -> None:
        return None


class InMemoryAgentEventBus:
    """同进程实现，用于单元测试和单进程开发。生产用 RedisAgentEventBus。"""

    def __init__(self, *, buffer_size: int = 64) -> None:
        self._buffer = buffer_size
        self._subscribers: dict[int, list[asyncio.Queue[AgentEventEnvelope]]] = {}

    async def publish(self, envelope: AgentEventEnvelope) -> None:
        queues = list(self._subscribers.get(envelope.job_id, []))
        for q in queues:
            if q.full():
                logger.warning("InMemoryAgentEventBus drop: queue full job_id=%s", envelope.job_id)
                continue
            await q.put(envelope)

    @contextlib.asynccontextmanager
    async def subscribe(self, *, job_id: int) -> AsyncIterator[_InMemoryStream]:
        q: asyncio.Queue[AgentEventEnvelope] = asyncio.Queue(maxsize=self._buffer)
        self._subscribers.setdefault(job_id, []).append(q)
        try:
            yield _InMemoryStream(queue=q)
        finally:
            self._subscribers[job_id].remove(q)
            if not self._subscribers[job_id]:
                del self._subscribers[job_id]


class RedisAgentEventBus:
    """生产实现：worker 进程 publish 到 channel，web 进程 subscribe。"""

    def __init__(
        self,
        *,
        redis: Redis,
        channel_prefix: str,
        buffer_size: int = 64,
    ) -> None:
        self._redis = redis
        self._channel_prefix = channel_prefix
        self._buffer = buffer_size

    def _channel(self, job_id: int) -> str:
        return f"{self._channel_prefix}:{job_id}:events"

    async def publish(self, envelope: AgentEventEnvelope) -> None:
        await self._redis.publish(self._channel(envelope.job_id), envelope.to_json())

    @contextlib.asynccontextmanager
    async def subscribe(self, *, job_id: int) -> AsyncIterator["_RedisStream"]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(job_id))
        stream = _RedisStream(pubsub=pubsub)
        try:
            yield stream
        finally:
            await pubsub.unsubscribe(self._channel(job_id))
            await pubsub.aclose()


@dataclass(slots=True)
class _RedisStream:
    pubsub: Any

    async def next(self, *, timeout: float | None = None) -> AgentEventEnvelope:
        message = await self.pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=timeout if timeout is not None else 0,
        )
        if message is None:
            raise TimeoutError("No event within timeout")
        data = message.get("data")
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return AgentEventEnvelope.from_json(str(data))

    async def aclose(self) -> None:
        await self.pubsub.aclose()


def build_agent_event_bus(*, settings: Settings | None = None, redis: Redis | None = None) -> AgentEventBus:
    cfg = settings or get_settings()
    if redis is None:
        if not cfg.redis_url:
            return InMemoryAgentEventBus(buffer_size=cfg.agent_event_bus_buffer_size)
        from redis.asyncio import Redis as RedisClient  # local import to avoid hard dep at import time

        redis = RedisClient.from_url(cfg.redis_url, decode_responses=True)
    return RedisAgentEventBus(
        redis=redis,
        channel_prefix=cfg.agent_event_channel_prefix,
        buffer_size=cfg.agent_event_bus_buffer_size,
    )
```

- [ ] **Step 4: 清理 events.py scaffold**

`app/src/fileflash/agents/harness/events.py` 改为：

```python
# Kept as a re-export shim until callers migrate to event_bus.py.
from .event_bus import AgentEventEnvelope as AgentEvent

__all__ = ["AgentEvent"]
```

> 此 shim 后续 PR 删除。本 plan 暂不删，避免外部 import 路径同时变更。

- [ ] **Step 5: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_event_bus.py -v`
Expected: PASS（3 个用例）

- [ ] **Step 6: Commit**

```bash
git add app/src/fileflash/agents/harness/event_bus.py app/src/fileflash/agents/harness/events.py app/tests/test_agent_event_bus.py
git commit -m "feat(agent): add AgentEventBus with in-memory and Redis impls"
```

---

## Task 8: `AgentInbox` 服务（写表 + publish）

**Files:**

- Create: `app/src/fileflash/agents/harness/inbox.py`
- Create: `app/tests/test_agent_inbox.py`

- [ ] **Step 1: 写测试**

```python
# app/tests/test_agent_inbox.py
from datetime import UTC, datetime

import pytest

from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.models.enums import AgentInboxKind
from fileflash.repositories import AgentInboxMessageRepository


@pytest.mark.asyncio
async def test_handle_reply_persists_and_publishes(db_session, sample_background_job):  # noqa: ANN001
    repo = AgentInboxMessageRepository(db_session)
    ask = await repo.create_ask(
        job_id=int(sample_background_job.job_id),
        payload={"prompt": "?"},
    )
    await db_session.commit()

    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=db_session, event_bus=bus)

    async with bus.subscribe(job_id=int(sample_background_job.job_id)) as stream:
        msg = await inbox.handle(
            job_id=int(sample_background_job.job_id),
            kind=AgentInboxKind.REPLY,
            payload={"value": "yes"},
            reply_to_id=int(ask.inbox_message_id),
        )
        await db_session.commit()
        evt = await stream.next(timeout=1.0)

    assert msg.kind == AgentInboxKind.REPLY
    assert evt.event_type == "agent.inbox.reply"
    assert evt.payload["replyTo"] == str(ask.inbox_message_id)
    assert evt.payload["value"] == "yes"


@pytest.mark.asyncio
async def test_reply_with_unknown_ask_raises(db_session, sample_background_job):  # noqa: ANN001
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=db_session, event_bus=bus)
    with pytest.raises(ValueError):
        await inbox.handle(
            job_id=int(sample_background_job.job_id),
            kind=AgentInboxKind.REPLY,
            payload={"value": "yes"},
            reply_to_id=999999,
        )
```

- [ ] **Step 2: 运行测试，确认 fail**

Run: `cd app && uv run pytest tests/test_agent_inbox.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: 实现 `AgentInbox`**

```python
# app/src/fileflash/agents/harness/inbox.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.enums import AgentInboxKind
from ...repositories import AgentInboxMessageRepository
from .event_bus import AgentEventBus, AgentEventEnvelope


_INBOX_EVENT_TYPES: dict[AgentInboxKind, str] = {
    AgentInboxKind.REPLY: "agent.inbox.reply",
    AgentInboxKind.CONTROL_PAUSE: "agent.inbox.control",
    AgentInboxKind.CONTROL_RESUME: "agent.inbox.control",
    AgentInboxKind.CONTROL_APPROVE: "agent.inbox.control",
    AgentInboxKind.CONTROL_DENY: "agent.inbox.control",
    AgentInboxKind.CONTROL_SKIP: "agent.inbox.control",
    AgentInboxKind.CONTROL_CANCEL: "agent.inbox.control",
}


class AgentInbox:
    def __init__(self, *, db: AsyncSession, event_bus: AgentEventBus) -> None:
        self._db = db
        self._bus = event_bus
        self._repo = AgentInboxMessageRepository(db)

    async def handle(
        self,
        *,
        job_id: int,
        kind: AgentInboxKind,
        payload: dict[str, Any],
        reply_to_id: int | None = None,
    ):
        if kind == AgentInboxKind.REPLY:
            if reply_to_id is None:
                raise ValueError("reply requires reply_to_id")
            ask = await self._repo.get_ask(inbox_message_id=reply_to_id)
            if ask is None:
                raise ValueError(f"ask {reply_to_id} not found")
            if ask.job_id != job_id:
                raise ValueError(f"ask {reply_to_id} belongs to a different job")

        msg = await self._repo.record_user_message(
            job_id=job_id,
            kind=kind,
            payload=payload,
            reply_to_id=reply_to_id,
        )
        event_type = _INBOX_EVENT_TYPES[kind]
        envelope_payload: dict[str, Any] = {"kind": kind.value, "messageId": str(msg.inbox_message_id)}
        if reply_to_id is not None:
            envelope_payload["replyTo"] = str(reply_to_id)
        if "value" in payload:
            envelope_payload["value"] = payload["value"]
        await self._bus.publish(
            AgentEventEnvelope(
                job_id=job_id,
                event_type=event_type,
                payload=envelope_payload,
                emitted_at=datetime.now(UTC),
            )
        )
        return msg
```

- [ ] **Step 4: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_inbox.py -v`
Expected: PASS（2 个用例）

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/harness/inbox.py app/tests/test_agent_inbox.py
git commit -m "feat(agent): add AgentInbox service"
```

---

## Task 9: `AskProtocol`（worker 等用户回答）

**Files:**

- Create: `app/src/fileflash/agents/harness/ask.py`
- Create: `app/tests/test_agent_ask_protocol.py`

- [ ] **Step 1: 写测试**

```python
# app/tests/test_agent_ask_protocol.py
import asyncio
from datetime import UTC, datetime

import pytest

from fileflash.agents.harness.ask import AskProtocol, AskTimedOut
from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.models.enums import AgentInboxKind, AgentInboxStatus
from fileflash.repositories import AgentInboxMessageRepository


@pytest.mark.asyncio
async def test_ask_returns_when_reply_arrives(db_session, sample_background_job):  # noqa: ANN001
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=db_session, event_bus=bus)
    protocol = AskProtocol(
        db=db_session,
        event_bus=bus,
        job_id=int(sample_background_job.job_id),
    )
    await protocol.start()
    try:
        async def reply_later():
            await asyncio.sleep(0.05)
            # 找到刚创建的 ask
            repo = AgentInboxMessageRepository(db_session)
            from sqlalchemy import select
            from fileflash.models import AgentInboxMessage
            ask = await db_session.scalar(
                select(AgentInboxMessage)
                .where(AgentInboxMessage.kind == AgentInboxKind.ASK)
                .order_by(AgentInboxMessage.inbox_message_id.desc())
            )
            await inbox.handle(
                job_id=int(sample_background_job.job_id),
                kind=AgentInboxKind.REPLY,
                payload={"value": "A"},
                reply_to_id=int(ask.inbox_message_id),
            )
            await db_session.commit()

        replier = asyncio.create_task(reply_later())
        result = await protocol.ask(
            prompt="choose",
            schema={"choice": ["A", "B"]},
            timeout_sec=2.0,
        )
        await replier
    finally:
        await protocol.aclose()

    assert result == "A"


@pytest.mark.asyncio
async def test_ask_times_out(db_session, sample_background_job):  # noqa: ANN001
    bus = InMemoryAgentEventBus()
    protocol = AskProtocol(
        db=db_session,
        event_bus=bus,
        job_id=int(sample_background_job.job_id),
    )
    await protocol.start()
    try:
        with pytest.raises(AskTimedOut):
            await protocol.ask(prompt="?", schema={}, timeout_sec=0.1)
    finally:
        await protocol.aclose()

    # 验证 ask 已被标 timed_out
    from sqlalchemy import select
    from fileflash.models import AgentInboxMessage
    asks = list(
        await db_session.scalars(
            select(AgentInboxMessage).where(AgentInboxMessage.kind == AgentInboxKind.ASK)
        )
    )
    assert asks
    assert asks[-1].status == AgentInboxStatus.TIMED_OUT
```

- [ ] **Step 2: 运行测试，确认 fail**

Run: `cd app && uv run pytest tests/test_agent_ask_protocol.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: 实现 `AskProtocol`**

```python
# app/src/fileflash/agents/harness/ask.py
from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.enums import AgentInboxKind
from ...repositories import AgentInboxMessageRepository
from .event_bus import AgentEventBus, AgentEventEnvelope


class AskTimedOut(Exception):
    def __init__(self, *, ask_id: int) -> None:
        super().__init__(f"Ask {ask_id} timed out")
        self.ask_id = ask_id


class AskProtocol:
    """worker 端：创建 ask 表条目、publish agent.ask 事件、阻塞等 reply 经 inbox channel 唤醒。

    生命周期绑定单个 job_id。`start()` 后开始订阅；`aclose()` 释放订阅。
    """

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
        self._sub_stream = None
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
        for fut in self._waiters.values():
            if not fut.done():
                fut.cancel()

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

        await self._bus.publish(
            AgentEventEnvelope(
                job_id=self._job_id,
                event_type="agent.ask",
                payload={
                    "messageId": str(msg.inbox_message_id),
                    "prompt": prompt,
                    "schema": schema,
                    "timeoutSec": timeout_sec,
                },
                emitted_at=datetime.now(UTC),
            )
        )

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        self._waiters[int(msg.inbox_message_id)] = fut
        try:
            value = await asyncio.wait_for(fut, timeout=timeout_sec)
        except asyncio.TimeoutError as exc:
            from ...models.enums import AgentInboxStatus
            ask = await self._repo.get_ask(inbox_message_id=int(msg.inbox_message_id))
            if ask is not None:
                ask.status = AgentInboxStatus.TIMED_OUT
                ask.answered_at = datetime.now(UTC)
                await self._db.commit()
            raise AskTimedOut(ask_id=int(msg.inbox_message_id)) from exc
        finally:
            self._waiters.pop(int(msg.inbox_message_id), None)

        await self._repo.mark_answered(
            inbox_message_id=int(msg.inbox_message_id),
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
            except Exception:  # noqa: BLE001
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
            fut = self._waiters.get(ask_id)
            if fut is None or fut.done():
                continue
            fut.set_result(envelope.payload.get("value"))
```

- [ ] **Step 4: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_ask_protocol.py -v`
Expected: PASS（2 个用例）

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/harness/ask.py app/tests/test_agent_ask_protocol.py
git commit -m "feat(agent): add AskProtocol for worker-to-user blocking ask"
```

---

## Task 10: `POST /agent/jobs/{job_id}/messages` 路由

**Files:**

- Modify: `app/src/fileflash/routers/agent.py`
- Modify: `app/src/fileflash/core/deps.py`
- Modify: `app/tests/test_agent_routes.py`

- [ ] **Step 1: 在 `deps.py` 增加 EventBus 依赖**

```python
# app/src/fileflash/core/deps.py — 在文件末尾增加
from ..agents.harness.event_bus import AgentEventBus, build_agent_event_bus

_event_bus_singleton: AgentEventBus | None = None


def get_agent_event_bus() -> AgentEventBus:
    global _event_bus_singleton
    if _event_bus_singleton is None:
        _event_bus_singleton = build_agent_event_bus()
    return _event_bus_singleton
```

> 注：如果 deps.py 已有 module-level singleton 模式，沿用既有写法；否则用上述简单单例。

- [ ] **Step 2: 在 `routers/agent.py` 新增路由**

在 `cancel_agent_job` 之前插入：

```python
from ..agents.harness.event_bus import AgentEventBus
from ..agents.harness.inbox import AgentInbox
from ..core.deps import get_agent_event_bus
from ..models.enums import AgentInboxKind
from ..schemas.agent import AgentInboxMessageRequest, AgentInboxMessageResponse


@router.post("/jobs/{job_id}/messages")
async def post_agent_job_message(
    job_id: str,
    payload: AgentInboxMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_bus: Annotated[AgentEventBus, Depends(get_agent_event_bus)],
):
    parsed_job_id = _parse_job_id(job_id)
    job = await db.scalar(
        select(BackgroundJob).where(
            and_(
                BackgroundJob.job_id == parsed_job_id,
                BackgroundJob.requested_by == current_user.user_id,
                BackgroundJob.task_type.in_(["agent.plan", "agent.execute"]),
            )
        )
    )
    if job is None:
        raise ApiError(status_code=404, code=404, message="Job not found")

    kind = AgentInboxKind(payload.kind)
    reply_to_id: int | None = None
    if payload.reply_to is not None:
        try:
            reply_to_id = int(payload.reply_to)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid replyTo") from exc

    inbox = AgentInbox(db=db, event_bus=event_bus)
    try:
        msg = await inbox.handle(
            job_id=parsed_job_id,
            kind=kind,
            payload=_inbox_payload_from_request(payload),
            reply_to_id=reply_to_id,
        )
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message=str(exc)) from exc
    await db.commit()

    data = AgentInboxMessageResponse(
        inbox_message_id=str(msg.inbox_message_id),
        kind=payload.kind,
        accepted_at=msg.created_at,
    )
    return api_success(data=data.model_dump(by_alias=True), message="Message accepted")


def _inbox_payload_from_request(req: AgentInboxMessageRequest) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if req.value is not None:
        body["value"] = req.value
    if req.metadata:
        body["metadata"] = req.metadata
    return body
```

> 注：`Any` 已经在 typing 中；如未 import，在文件顶部 `from typing import Annotated, Any`。

- [ ] **Step 3: 扩展 `test_agent_routes.py`，新增一组用例**

```python
# app/tests/test_agent_routes.py — 在文件末尾追加
from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.core.deps import get_agent_event_bus
from fileflash.models import AgentInboxMessage
from fileflash.models.enums import AgentInboxKind


def _build_app_with_bus(bus: InMemoryAgentEventBus, db_stub) -> FastAPI:  # noqa: ANN001
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_db] = lambda: db_stub
    app.dependency_overrides[get_current_user] = lambda: User(user_id=7)
    app.dependency_overrides[get_agent_event_bus] = lambda: bus
    return app


def test_post_message_control_pause_accepted(db_session, sample_background_job):  # noqa: ANN001
    bus = InMemoryAgentEventBus()
    # 真 DB session 测；不再用 StubDb
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: User(
        user_id=int(sample_background_job.requested_by)
    )
    app.dependency_overrides[get_agent_event_bus] = lambda: bus

    client = TestClient(app)
    resp = client.post(
        f"/agent/jobs/{sample_background_job.job_id}/messages",
        json={"kind": "control.pause"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["kind"] == "control.pause"
```

> 注：`sample_background_job` fixture 应该指向 `requested_by=7` 的 BackgroundJob；如 fixture 不一致，按既有 fixture 命名调整。

- [ ] **Step 4: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_routes.py -v -k "post_message"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/core/deps.py app/src/fileflash/routers/agent.py app/tests/test_agent_routes.py
git commit -m "feat(agent): add POST /agent/jobs/{id}/messages upstream channel"
```

---

## Task 11: SSE 端点改为订阅 EventBus

**Files:**

- Modify: `app/src/fileflash/routers/agent.py`

- [ ] **Step 1: 替换 `stream_agent_job_events` 与 `event_stream` 内部逻辑**

把现有 `stream_agent_job_events` 整体替换为：

```python
@router.get("/jobs/{job_id}/events")
async def stream_agent_job_events(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_bus: Annotated[AgentEventBus, Depends(get_agent_event_bus)],
):
    parsed_job_id = _parse_job_id(job_id)
    initial_events, initial_terminal = await _agent_job_events_for_job(
        db=db,
        job_id=parsed_job_id,
        user_id=int(current_user.user_id),
    )

    async def event_stream():
        seen: set[str] = set()
        for event in initial_events:
            seen.add(event.id)
            yield _format_sse_event(event)
        if initial_terminal:
            return
        async with event_bus.subscribe(job_id=parsed_job_id) as stream:
            while True:
                try:
                    envelope = await stream.next(timeout=30.0)
                except TimeoutError:
                    # 30s 心跳，避免代理断连
                    yield ": keep-alive\n\n"
                    continue
                event = _envelope_to_job_event(envelope)
                if event.id in seen:
                    continue
                seen.add(event.id)
                yield _format_sse_event(event)
                if event.type in {"job.succeeded", "job.failed", "job.canceled"}:
                    break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

新增辅助函数：

```python
def _envelope_to_job_event(env: "AgentEventEnvelope") -> AgentJobEvent:
    return AgentJobEvent(
        id=env.event_id or f"{env.job_id}:{env.event_type}:{env.emitted_at.isoformat()}",
        job_id=str(env.job_id),
        task_type="agent.execute",  # type 在 envelope payload 里冗余，简化
        type=env.event_type,  # type: ignore[arg-type]
        status=str(env.payload.get("status") or ""),
        agent_phase=env.payload.get("agentPhase"),
        message=str(env.payload.get("message") or ""),
        data=dict(env.payload.get("data") or env.payload),
        timestamp=env.emitted_at,
    )
```

把 `AGENT_EVENT_POLL_INTERVAL_SEC` 常量删掉，把 `asyncio.sleep(...)` 调用一并删除。在文件顶部加入：

```python
from ..agents.harness.event_bus import AgentEventBus, AgentEventEnvelope
```

> 注：保留 `_agent_job_events_for_job` 用作 initial replay（连接刚建立时拉一次历史），因为 pub/sub 不持久化。

- [ ] **Step 2: 扩展 SSE 测试**

在 `test_agent_routes.py` 已有的 SSE 用例之外加一个：

```python
def test_sse_streams_published_events(db_session, sample_background_job):  # noqa: ANN001
    bus = InMemoryAgentEventBus()
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(ApiError, api_error_handler)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: User(
        user_id=int(sample_background_job.requested_by)
    )
    app.dependency_overrides[get_agent_event_bus] = lambda: bus

    import asyncio
    from datetime import UTC, datetime

    async def producer():
        await asyncio.sleep(0.1)
        await bus.publish(
            AgentEventEnvelope(
                job_id=int(sample_background_job.job_id),
                event_type="agent.progress",
                payload={"step": 1, "total": 3, "message": "halfway"},
                emitted_at=datetime.now(UTC),
            )
        )
        await asyncio.sleep(0.05)
        await bus.publish(
            AgentEventEnvelope(
                job_id=int(sample_background_job.job_id),
                event_type="job.succeeded",
                payload={"status": "succeeded"},
                emitted_at=datetime.now(UTC),
            )
        )

    client = TestClient(app)
    # TestClient 不直接支持 async producer 并发；用线程
    import threading

    def run_producer() -> None:
        asyncio.run(producer())

    t = threading.Thread(target=run_producer)
    t.start()
    with client.stream("GET", f"/agent/jobs/{sample_background_job.job_id}/events") as resp:
        lines = []
        for chunk in resp.iter_lines():
            if chunk:
                lines.append(chunk)
            if any("job.succeeded" in line for line in lines):
                break
    t.join()

    assert any("agent.progress" in line for line in lines)
    assert any("job.succeeded" in line for line in lines)
```

> 注：原有依赖 0.6s DB 轮询的 SSE 测试如失败，按新模型重写为"测 initial replay + 测订阅流"两段。

- [ ] **Step 3: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_routes.py -v -k "sse"`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add app/src/fileflash/routers/agent.py app/tests/test_agent_routes.py
git commit -m "feat(agent): replace SSE polling with EventBus subscription"
```

---

## Task 12: 删除 `POST /agent/cancel/{job_id}`

**Files:**

- Modify: `app/src/fileflash/routers/agent.py`
- Modify: `app/tests/test_agent_routes.py`

- [ ] **Step 1: 删除 `cancel_agent_job` 函数与对应的 `from ..schemas.agent import ... CancelAgentResponse` 引用**

确认 import 调整后无 unused。

- [ ] **Step 2: 删除 `test_agent_routes.py` 中所有 `POST /agent/cancel` 测试用例**

Run: `grep -n "cancel_agent\|/agent/cancel" app/tests/test_agent_routes.py`
逐条删除。

- [ ] **Step 3: 全仓搜索其他引用并清理**

Run: `grep -rn "agent/cancel\|cancelAgentJob" app/ web/`
Expected: 仅 `web/` 下有引用（前端 plan 处理），后端无引用。如果后端有，一并删除。

- [ ] **Step 4: 运行全部 agent 测试**

Run: `cd app && uv run pytest tests/test_agent_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/routers/agent.py app/tests/test_agent_routes.py
git commit -m "refactor(agent): drop legacy POST /agent/cancel route"
```

---

## Task 13: `ExecuteRunner` 接入 inbox（pause/resume/skip/approve/cancel）

**Files:**

- Modify: `app/src/fileflash/agents/runtime/execute_runner.py`
- Modify: `app/tests/test_agent_plan_execute_runtime.py`

- [ ] **Step 1: 在 `ExecuteRunner.__init__` 增加 EventBus 依赖与状态**

```python
class ExecuteRunner:
    def __init__(
        self,
        *,
        policy_guard: PolicyGuard | None = None,
        event_bus: AgentEventBus | None = None,
    ) -> None:
        self.policy_guard = policy_guard or PolicyGuard()
        self.event_bus = event_bus
```

> 默认 `None` 时退化为静默（不 publish），用于单元测试与旧调用兼容。

- [ ] **Step 2: 在 `ExecuteRunner.run` 顶部新增 step 边界控制处理**

把原 line 62-66 的循环顶部替换为：

```python
        from ...repositories import AgentInboxMessageRepository

        inbox_repo = AgentInboxMessageRepository(db)
        paused = False

        for action in actions:
            await db.refresh(job)
            if job.cancel_requested_at is not None:
                raise AgentJobCanceled()

            # ---- step 边界 inbox 处理 ----
            while True:
                pending = await inbox_repo.list_pending_controls(job_id=int(job.job_id))
                for ctrl in pending:
                    if ctrl.kind == AgentInboxKind.CONTROL_CANCEL:
                        await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                        job.cancel_requested_at = datetime.now(UTC)
                        await db.commit()
                        raise AgentJobCanceled()
                    if ctrl.kind == AgentInboxKind.CONTROL_PAUSE:
                        paused = True
                        await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                        await self._publish_state("agent.paused", job_id=int(job.job_id))
                    elif ctrl.kind == AgentInboxKind.CONTROL_RESUME:
                        paused = False
                        await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                        await self._publish_state("agent.resumed", job_id=int(job.job_id))
                    elif ctrl.kind == AgentInboxKind.CONTROL_SKIP:
                        # 标记跳过当前 step；继续外层 for
                        await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                        warnings.append(f"Step {action.step} skipped by user")
                        applied -= 0  # 不计入 applied
                        await db.commit()
                        break  # break inner pending loop
                    else:
                        # approve / deny — 单工具实时审批，由 policy_guard 读取，这里仅消费
                        await inbox_repo.mark_dropped(inbox_message_id=int(ctrl.inbox_message_id))
                await db.commit()
                if not paused:
                    break
                # paused: 等 100ms 再轮询
                await asyncio.sleep(0.1)
            # ---- 结束 inbox 处理 ----
```

并在顶部 import 处新增：

```python
import asyncio

from ...models.enums import AgentInboxKind
from ..harness.event_bus import AgentEventBus, AgentEventEnvelope
```

新增 `_publish_state` 实例方法（与 `run` 同一类）：

```python
    async def _publish_state(self, event_type: str, *, job_id: int) -> None:
        if self.event_bus is None:
            return
        await self.event_bus.publish(
            AgentEventEnvelope(
                job_id=job_id,
                event_type=event_type,
                payload={},
                emitted_at=datetime.now(UTC),
            )
        )
```

- [ ] **Step 3: 把工具调用的事件 publish 也接上 EventBus**

在 line 103-110（`append_step` running 之后）、line 130-140（`finish_step` succeeded 之后）、以及 failure 分支，分别插入：

```python
            # 工具开始
            if self.event_bus is not None:
                await self.event_bus.publish(
                    AgentEventEnvelope(
                        job_id=int(job.job_id),
                        event_type="tool.started",
                        payload={
                            "step": int(action.step),
                            "tool": str(action.tool),
                            "input": resolved_input,
                        },
                        emitted_at=started,
                    )
                )

            # 工具成功
            if self.event_bus is not None:
                await self.event_bus.publish(
                    AgentEventEnvelope(
                        job_id=int(job.job_id),
                        event_type="tool.succeeded",
                        payload={
                            "step": int(action.step),
                            "tool": str(action.tool),
                            "output": safe_output,
                            "durationMs": duration_ms,
                        },
                        emitted_at=datetime.now(UTC),
                    )
                )

            # 工具失败（含 resolve / dispatch 两个分支）
            if self.event_bus is not None:
                await self.event_bus.publish(
                    AgentEventEnvelope(
                        job_id=int(job.job_id),
                        event_type="tool.failed",
                        payload={
                            "step": int(action.step),
                            "tool": str(action.tool),
                            "errorMessage": f"{type(exc).__name__}: {exc}"[:2000],
                        },
                        emitted_at=datetime.now(UTC),
                    )
                )
```

- [ ] **Step 4: 写 / 改测试，覆盖 pause-resume、cancel-via-inbox**

在 `test_agent_plan_execute_runtime.py` 末尾追加：

```python
import asyncio

from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.agents.runtime.execute_runner import AgentJobCanceled, ExecuteRunner
from fileflash.models.enums import AgentInboxKind


@pytest.mark.asyncio
async def test_execute_runner_pauses_then_resumes(
    db_session, executable_job_with_two_steps,  # noqa: ANN001
):
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=db_session, event_bus=bus)
    runner = ExecuteRunner(event_bus=bus)

    async def control_later():
        await asyncio.sleep(0.05)
        await inbox.handle(
            job_id=int(executable_job_with_two_steps.job_id),
            kind=AgentInboxKind.CONTROL_PAUSE,
            payload={},
        )
        await db_session.commit()
        await asyncio.sleep(0.2)
        await inbox.handle(
            job_id=int(executable_job_with_two_steps.job_id),
            kind=AgentInboxKind.CONTROL_RESUME,
            payload={},
        )
        await db_session.commit()

    sender = asyncio.create_task(control_later())
    result = await runner.run(db=db_session, job=executable_job_with_two_steps)
    await sender

    assert result.applied_actions == 2


@pytest.mark.asyncio
async def test_execute_runner_canceled_via_inbox(
    db_session, executable_job_with_two_steps,  # noqa: ANN001
):
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=db_session, event_bus=bus)
    runner = ExecuteRunner(event_bus=bus)

    async def cancel_later():
        await asyncio.sleep(0.05)
        await inbox.handle(
            job_id=int(executable_job_with_two_steps.job_id),
            kind=AgentInboxKind.CONTROL_CANCEL,
            payload={},
        )
        await db_session.commit()

    sender = asyncio.create_task(cancel_later())
    with pytest.raises(AgentJobCanceled):
        await runner.run(db=db_session, job=executable_job_with_two_steps)
    await sender
```

> 注：`executable_job_with_two_steps` 是新 fixture。如项目已有可执行 job 的 fixture（参见 test_agent_plan_execute_runtime.py），沿用即可，否则在 `conftest.py` 加一个简单 fixture 构造含两步 read-only 计划的 job。

- [ ] **Step 5: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_plan_execute_runtime.py -v -k "pause or canceled_via_inbox"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/src/fileflash/agents/runtime/execute_runner.py app/tests/test_agent_plan_execute_runtime.py
git commit -m "feat(agent): wire ExecuteRunner to inbox controls and event bus"
```

---

## Task 14: `PlanRunner` 接入 ask（基础占位 + 接口暴露）

**Files:**

- Modify: `app/src/fileflash/agents/runtime/plan_runner.py`
- Modify: `app/tests/test_agent_plan_execute_runtime.py`

> 本 Task 不引入 LLM 触发 ask 的判断逻辑（那需要改 prompt 与 tool-use 模板，留给后续）。本 Task 仅把 `AskProtocol` 注入到 `PlanRunner` 与 `ExecuteRunner`，并提供 `await self._ask(...)` 辅助方法，供后续 prompt 模板调用。

- [ ] **Step 1: 在 `PlanRunner.__init__` 增加 EventBus + ask 启停**

```python
class PlanRunner:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        planner_client: PlannerClient | None = None,
        event_bus: AgentEventBus | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.planner_client = planner_client or AnthropicPlannerClient(settings=self.settings)
        self.event_bus = event_bus
```

在 import 处新增：

```python
from ..harness.event_bus import AgentEventBus
from ..harness.ask import AskProtocol
```

在 `run` 方法的开头：

```python
        ask: AskProtocol | None = None
        if self.event_bus is not None:
            ask = AskProtocol(db=db, event_bus=self.event_bus, job_id=int(job.job_id))
            await ask.start()
        try:
            # ... 现有 run 逻辑 ...
            return result
        finally:
            if ask is not None:
                await ask.aclose()
```

在类中新增辅助：

```python
    async def _ask(
        self,
        *,
        ask: AskProtocol | None,
        prompt: str,
        schema: dict[str, Any],
    ) -> Any | None:
        if ask is None:
            return None
        return await ask.ask(
            prompt=prompt,
            schema=schema,
            timeout_sec=float(self.settings.agent_inbox_ask_timeout_sec),
        )
```

> 后续 prompt 模板里若决定需要澄清，调 `await self._ask(ask=ask, prompt=..., schema=...)`。本 plan 仅做接线；触发逻辑留到后续。

- [ ] **Step 2: ExecuteRunner 同样增加 ask 接线（已 publish 事件，但当前不主动调 ask）**

只是为了对称，方便后续 prompt 模板复用。改 `ExecuteRunner.run` 顶部：

```python
        ask: AskProtocol | None = None
        if self.event_bus is not None:
            ask = AskProtocol(db=db, event_bus=self.event_bus, job_id=int(job.job_id))
            await ask.start()
        try:
            # ... 现有 run 逻辑 ...
            return result
        finally:
            if ask is not None:
                await ask.aclose()
```

> 当前 ExecuteRunner 不调用 `ask.ask()`；这只是接线。

- [ ] **Step 3: 跳过端到端 ask 触发用例**

> 触发 LLM 调 ask 取决于后续 prompt 模板的改动，超出本 plan 范围。`AskProtocol` 自身的行为（成功回答 + 超时 + status 写回）已在 Task 9 的两个用例完整覆盖。本 Task 不再写额外测试。

- [ ] **Step 4: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_plan_execute_runtime.py -v`
Expected: 既有用例 PASS（接线为可选注入，不破坏旧调用方）

- [ ] **Step 5: Commit**

```bash
git add app/src/fileflash/agents/runtime/plan_runner.py app/src/fileflash/agents/runtime/execute_runner.py app/tests/test_agent_plan_execute_runtime.py
git commit -m "feat(agent): wire AskProtocol into PlanRunner and ExecuteRunner"
```

---

## Task 15: worker 装配 EventBus 与 runner 注入

**Files:**

- Modify: `app/src/fileflash/agents/worker.py`

- [ ] **Step 1: 在 `AgentWorkerConsumer.__init__` 中创建 EventBus 单例并下发**

```python
class AgentWorkerConsumer:
    def __init__(
        self,
        *,
        queue: RedisStreamJobQueue,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
        event_bus: AgentEventBus | None = None,
    ) -> None:
        self._settings = get_settings()
        self._queue = queue
        self._session_factory = session_factory
        self._event_bus = event_bus or build_agent_event_bus(settings=self._settings)
```

在 imports 处新增：

```python
from ..agents.harness.event_bus import AgentEventBus, build_agent_event_bus
```

- [ ] **Step 2: 在 `_run_job` / `_process_message` 中创建 runner 时传入 event_bus**

找到现有 `PlanRunner()` / `ExecuteRunner(...)` 实例化点（在 `_run_job` 内），替换为：

```python
            if message.task_type == "agent.plan":
                runner = PlanRunner(event_bus=self._event_bus)
                result = await runner.run(db=db, job=fresh_job)
                ...
            elif message.task_type == "agent.execute":
                runner = ExecuteRunner(event_bus=self._event_bus)
                result = await runner.run(db=db, job=fresh_job)
                ...
```

> 注：以现有代码的实例化位置为准；保持依赖注入路径一致。

- [ ] **Step 3: 在 `_mark_canceled` / `_mark_failed` / `_mark_succeeded` 中也 publish 终态事件**

```python
    async def _publish_terminal(
        self,
        *,
        job_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._event_bus.publish(
            AgentEventEnvelope(
                job_id=job_id,
                event_type=event_type,
                payload=payload or {},
                emitted_at=datetime.now(UTC),
            )
        )
```

并在三个 mark 函数末尾分别 `await self._publish_terminal(...)`，事件类型对应 `job.canceled` / `job.failed` / `job.succeeded`。

- [ ] **Step 4: 加最小验证测试**

`app/tests/test_agent_worker.py` 已存在；在末尾追加：

```python
@pytest.mark.asyncio
async def test_worker_publishes_terminal_event(...):  # 沿用既有 test_agent_worker.py 的 fixture
    ...
    # 注入 InMemoryAgentEventBus，跑一个 succeed 流，断言收到 job.succeeded envelope
```

> 注：如 test_agent_worker.py 现有结构难以注入 event_bus，跳过此 step，依赖 Task 16 的端到端验证。

- [ ] **Step 5: 运行测试**

Run: `cd app && uv run pytest tests/test_agent_worker.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/src/fileflash/agents/worker.py app/tests/test_agent_worker.py
git commit -m "feat(agent): inject EventBus into worker and publish terminal events"
```

---

## Task 16: 端到端集成测试（POST 消息 → worker 收到 → publish → SSE 收到）

**Files:**

- Create: `app/tests/test_agent_a_end_to_end.py`

- [ ] **Step 1: 写端到端测试**

```python
# app/tests/test_agent_a_end_to_end.py
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from fileflash.agents.harness.event_bus import (
    AgentEventEnvelope,
    InMemoryAgentEventBus,
)
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.agents.runtime.execute_runner import (
    AgentJobCanceled,
    ExecuteRunner,
)
from fileflash.models.enums import AgentInboxKind


@pytest.mark.asyncio
async def test_user_pause_then_cancel_via_inbox(
    db_session, executable_job_with_two_steps,  # noqa: ANN001
):
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=db_session, event_bus=bus)
    runner = ExecuteRunner(event_bus=bus)

    seen_events: list[str] = []

    async def consumer():
        async with bus.subscribe(job_id=int(executable_job_with_two_steps.job_id)) as stream:
            for _ in range(8):
                try:
                    env = await stream.next(timeout=2.0)
                except TimeoutError:
                    break
                seen_events.append(env.event_type)
                if env.event_type == "agent.paused":
                    await inbox.handle(
                        job_id=int(executable_job_with_two_steps.job_id),
                        kind=AgentInboxKind.CONTROL_CANCEL,
                        payload={},
                    )
                    await db_session.commit()

    listener = asyncio.create_task(consumer())

    async def pause_soon():
        await asyncio.sleep(0.05)
        await inbox.handle(
            job_id=int(executable_job_with_two_steps.job_id),
            kind=AgentInboxKind.CONTROL_PAUSE,
            payload={},
        )
        await db_session.commit()

    nudger = asyncio.create_task(pause_soon())

    with pytest.raises(AgentJobCanceled):
        await runner.run(db=db_session, job=executable_job_with_two_steps)

    await nudger
    listener.cancel()
    with pytest.raises(asyncio.CancelledError):
        await listener

    assert "agent.paused" in seen_events
    assert "tool.started" in seen_events or "tool.failed" in seen_events
```

- [ ] **Step 2: 运行**

Run: `cd app && uv run pytest tests/test_agent_a_end_to_end.py -v`
Expected: PASS

- [ ] **Step 3: 全部 agent 测试 smoke**

Run: `cd app && uv run pytest tests/ -k "agent" -v`
Expected: 全部 PASS（含旧的 test_agent_routes.py / test_agent_repositories.py / test_agent_plan_execute_runtime.py）

- [ ] **Step 4: Commit**

```bash
git add app/tests/test_agent_a_end_to_end.py
git commit -m "test(agent): end-to-end pause + cancel via inbox"
```

---

## Acceptance Checklist（实施完成判定）

- [ ] `app/src/fileflash/agents/harness/event_bus.py` 提供 `InMemoryAgentEventBus` 与 `RedisAgentEventBus`，并通过 `build_agent_event_bus` 工厂自动选择
- [ ] `AgentInboxMessage` 表通过 V14 Flyway 迁移创建，ORM model + repository 已接入
- [ ] `POST /agent/jobs/{job_id}/messages` 接受 7 种 kind（reply + 6 种 control）
- [ ] `POST /agent/cancel/{job_id}` 已删除；取消统一走 inbox `control.cancel`
- [ ] SSE 端点不再轮询 DB；初始 replay 后纯订阅 EventBus，包含 30s 心跳
- [ ] `ExecuteRunner` 在 step 边界处理 pause/resume/skip/approve/deny/cancel
- [ ] `PlanRunner` 与 `ExecuteRunner` 都启动了 `AskProtocol`；后续 prompt 模板可调 `_ask`
- [ ] `worker.py` 注入 EventBus 并 publish `job.succeeded` / `job.failed` / `job.canceled` 终态
- [ ] 端到端集成测试覆盖 pause → cancel via inbox 全链路

**注意（不在本 plan 范围）：**

- 前端接入新事件类型与上行通道 — 留给 `2026-05-26-agent-A-interaction-frontend.md`
- prompt 模板里何时调 `ask` — 留给后续；本 plan 只提供接口
- worker 多副本下"等用户回答的 worker 被杀"恢复机制 — 仅靠 `agent_inbox_ask_timeout_sec` 兜底；进一步的 owner 恢复留给后续 plan
