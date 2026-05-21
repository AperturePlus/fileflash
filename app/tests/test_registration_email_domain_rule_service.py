from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.tables_identity import RegistrationEmailDomainRule
from fileflash.schemas.registration_email_domain_rule import (
    CreateRegistrationEmailDomainRuleRequest,
    UpdateRegistrationEmailDomainRuleRequest,
)
from fileflash.services.registration_email_domain_rule import RegistrationEmailDomainRuleService


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.delete = AsyncMock()


@pytest.mark.asyncio
async def test_assert_email_allowed_rejects_when_no_enabled_rules() -> None:
    session = DummySession()
    session.scalars = AsyncMock(return_value=[])
    service = RegistrationEmailDomainRuleService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError, match="邮箱后缀不被允许，请更换邮箱"):
        await service.assert_email_allowed(email="demo@example.com")


@pytest.mark.asyncio
async def test_assert_email_allowed_accepts_when_pattern_matches() -> None:
    session = DummySession()
    rule = RegistrationEmailDomainRule(
        rule_id=1,
        name="corp",
        pattern=r".*\.corp\.com",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.scalars = AsyncMock(return_value=[rule])
    service = RegistrationEmailDomainRuleService(db=session)  # type: ignore[arg-type]

    await service.assert_email_allowed(email="user@dept.corp.com")


@pytest.mark.asyncio
async def test_assert_email_allowed_rejects_when_no_match() -> None:
    session = DummySession()
    rule = RegistrationEmailDomainRule(
        rule_id=1,
        name="corp",
        pattern=r".*\.corp\.com",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.scalars = AsyncMock(return_value=[rule])
    service = RegistrationEmailDomainRuleService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError, match="邮箱后缀不被允许，请更换邮箱"):
        await service.assert_email_allowed(email="demo@example.com")


@pytest.mark.asyncio
async def test_create_rule_rejects_risky_pattern() -> None:
    session = DummySession()
    session.scalar = AsyncMock(return_value=None)
    service = RegistrationEmailDomainRuleService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError, match="Regex pattern is too risky"):
        await service.create_rule(
            payload=CreateRegistrationEmailDomainRuleRequest(
                name="risky",
                pattern=r"(a+)+$",
                enabled=True,
            )
        )


@pytest.mark.asyncio
async def test_update_rule_rejects_invalid_pattern() -> None:
    session = DummySession()
    row = RegistrationEmailDomainRule(
        rule_id=7,
        name="ok",
        pattern=r".*",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.get = AsyncMock(return_value=row)
    service = RegistrationEmailDomainRuleService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError, match="Invalid regex pattern"):
        await service.update_rule(
            rule_id=7,
            payload=UpdateRegistrationEmailDomainRuleRequest(pattern=r"([a-z"),
        )


@pytest.mark.asyncio
async def test_delete_rule_not_found() -> None:
    session = DummySession()
    session.get = AsyncMock(return_value=None)
    service = RegistrationEmailDomainRuleService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError, match="Rule not found"):
        await service.delete_rule(rule_id=100)

