from __future__ import annotations

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import UserStatus
from fileflash.services.admin._status import external_to_internal, internal_to_external


def test_active_maps_both_ways() -> None:
    assert external_to_internal("active") == UserStatus.ACTIVE
    assert internal_to_external(UserStatus.ACTIVE) == "active"


def test_suspended_maps_to_disabled() -> None:
    assert external_to_internal("suspended") == UserStatus.DISABLED
    assert internal_to_external(UserStatus.DISABLED) == "suspended"


def test_locked_externally_appears_as_suspended() -> None:
    assert internal_to_external(UserStatus.LOCKED) == "suspended"


def test_pending_verification_passthrough() -> None:
    assert internal_to_external(UserStatus.PENDING_VERIFICATION) == "pending_verification"


def test_invalid_external_status_raises() -> None:
    with pytest.raises(ApiError):
        external_to_internal("garbage")
