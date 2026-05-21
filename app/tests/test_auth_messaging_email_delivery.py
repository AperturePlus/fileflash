from __future__ import annotations

import logging

import pytest

from fileflash.services.messaging import InProcessAuthEventPublisher


@pytest.mark.asyncio
async def test_publish_non_email_event_skips_delivery() -> None:
    publisher = InProcessAuthEventPublisher()

    await publisher.publish("auth.user_logged_in", {"userId": "1"})


@pytest.mark.asyncio
async def test_publish_event_log_does_not_expose_payload(caplog: pytest.LogCaptureFixture) -> None:
    publisher = InProcessAuthEventPublisher()
    sensitive_payload = {
        "email": "demo@example.com",
        "token": "verify-token-1234567890",
        "verificationToken": "verify-token-1234567890",
    }

    with caplog.at_level(logging.INFO):
        await publisher.publish(
            "auth.email_verification_resent",
            sensitive_payload,
        )

    assert "Auth event published in-process: auth.email_verification_resent" in caplog.text
    assert "verify-token-1234567890" not in caplog.text
    assert "demo@example.com" not in caplog.text
