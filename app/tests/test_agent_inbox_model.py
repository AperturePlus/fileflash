from __future__ import annotations

from datetime import UTC, datetime

from fileflash.models import AgentInboxMessage
from fileflash.models.enums import AgentInboxKind, AgentInboxRole, AgentInboxStatus


def test_agent_inbox_message_model_fields() -> None:
    msg = AgentInboxMessage(
        job_id=1,
        role=AgentInboxRole.AGENT,
        kind=AgentInboxKind.ASK,
        payload_json={"prompt": "which one?", "schema": {}},
        status=AgentInboxStatus.WAITING,
        created_at=datetime.now(UTC),
    )

    assert AgentInboxMessage.__tablename__ == "agent_inbox_message"
    assert msg.kind == AgentInboxKind.ASK
    assert msg.status == AgentInboxStatus.WAITING
    assert msg.payload_json["prompt"] == "which one?"
