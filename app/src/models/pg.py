from __future__ import annotations

from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from .enums import BaseStrEnum


def pg_enum(enum_cls: type[BaseStrEnum], name: str) -> PgEnum:
    return PgEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda cls: [member.value for member in cls],
    )


__all__ = ["pg_enum"]
