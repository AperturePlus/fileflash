from __future__ import annotations

from ...core.errors import ApiError
from ...models.enums import UserStatus

_EXTERNAL_TO_INTERNAL = {
    "active": UserStatus.ACTIVE,
    "suspended": UserStatus.DISABLED,
}

_INTERNAL_TO_EXTERNAL = {
    UserStatus.ACTIVE: "active",
    UserStatus.DISABLED: "suspended",
    UserStatus.LOCKED: "suspended",
    UserStatus.PENDING_VERIFICATION: "pending_verification",
}


def external_to_internal(value: str) -> UserStatus:
    try:
        return _EXTERNAL_TO_INTERNAL[value]
    except KeyError as exc:
        raise ApiError(
            status_code=422,
            code=422,
            message=f"Invalid user status: {value!r}",
        ) from exc


def internal_to_external(value: UserStatus) -> str:
    return _INTERNAL_TO_EXTERNAL.get(value, value.value)


__all__ = ["external_to_internal", "internal_to_external"]
