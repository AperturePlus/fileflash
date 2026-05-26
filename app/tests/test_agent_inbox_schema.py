from __future__ import annotations

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
