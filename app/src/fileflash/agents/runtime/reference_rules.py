from __future__ import annotations

import re

_STEP_REFERENCE = re.compile(r"^\$step(?P<step>\d+)\.(?P<path>[A-Za-z0-9_.-]+)$")
_SYMBOLIC_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REFERENCE_FIELDS = frozenset(
    {
        "id",
        "fileid",
        "folderid",
        "parentfolderid",
        "targetfolderid",
        "targetparentid",
    }
)


def parse_step_reference(value: str) -> tuple[int, tuple[str, ...]] | None:
    match = _STEP_REFERENCE.match(value.strip())
    if not match:
        return None
    step = int(match.group("step"))
    path = tuple(part for part in match.group("path").split(".") if part)
    if not path:
        return None
    return step, path


def is_symbolic_id_placeholder(*, value: str, field_name: str | None) -> bool:
    if not field_name or field_name.strip().lower() not in _REFERENCE_FIELDS:
        return False
    candidate = value.strip()
    if not candidate:
        return False
    if candidate.lower() == "root":
        return False
    if candidate.isdigit():
        return False
    if parse_step_reference(candidate) is not None:
        return False
    return _SYMBOLIC_ID.match(candidate) is not None


__all__ = ["is_symbolic_id_placeholder", "parse_step_reference"]
