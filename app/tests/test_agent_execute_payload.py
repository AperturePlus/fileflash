from __future__ import annotations

import json
from datetime import UTC, datetime

from fileflash.schemas.agent import ExecuteAgentRequest, ExecuteApproval


def test_execute_request_dump_json_serializes_confirmed_at() -> None:
    request = ExecuteAgentRequest(
        plan_job_id="3",
        plan_hash="sha256:abc",
        approval=ExecuteApproval(
            confirmed_by="1",
            confirmed_at=datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC),
        ),
    )
    payload = request.model_dump(by_alias=True, mode="json")
    json.dumps(payload)
    assert payload["approval"]["confirmedAt"] == "2026-05-17T12:00:00Z"
