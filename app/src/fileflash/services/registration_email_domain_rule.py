from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..models.tables_identity import RegistrationEmailDomainRule
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.registration_email_domain_rule import (
    CreateRegistrationEmailDomainRuleRequest,
    ListRegistrationEmailDomainRulesQuery,
    RegistrationEmailDomainRuleItem,
    UpdateRegistrationEmailDomainRuleRequest,
)


class RegistrationEmailDomainRuleService:
    _DISALLOWED_MESSAGE = "邮箱后缀不被允许，请更换邮箱"
    _PATTERN_MAX_LENGTH = 512

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_rules(
        self,
        *,
        query: ListRegistrationEmailDomainRulesQuery,
    ) -> PaginatedData[RegistrationEmailDomainRuleItem]:
        statement = select(RegistrationEmailDomainRule)
        if query.enabled is not None:
            statement = statement.where(RegistrationEmailDomainRule.enabled == query.enabled)
        if query.query_text:
            keyword = query.query_text.strip().lower()
            if keyword:
                like = f"%{keyword}%"
                statement = statement.where(
                    or_(
                        func.lower(RegistrationEmailDomainRule.name).like(like),
                        func.lower(RegistrationEmailDomainRule.pattern).like(like),
                    )
                )

        total = await self.db.scalar(select(func.count()).select_from(statement.subquery()))
        total_items = int(total or 0)
        total_pages = max(1, -(-total_items // query.per_page))
        offset = (query.page - 1) * query.per_page

        rows = list(
            await self.db.scalars(
                statement
                .order_by(RegistrationEmailDomainRule.rule_id.desc())
                .offset(offset)
                .limit(query.per_page)
            )
        )
        items = [self._to_item(row) for row in rows]
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total_items,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def create_rule(
        self,
        *,
        payload: CreateRegistrationEmailDomainRuleRequest,
    ) -> RegistrationEmailDomainRuleItem:
        name = payload.name.strip()
        pattern = payload.pattern.strip()
        self._validate_pattern(pattern)
        await self._ensure_name_unique(name=name)

        now = datetime.now(UTC)
        row = RegistrationEmailDomainRule(
            name=name,
            pattern=pattern,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_item(row)

    async def update_rule(
        self,
        *,
        rule_id: int,
        payload: UpdateRegistrationEmailDomainRuleRequest,
    ) -> RegistrationEmailDomainRuleItem:
        row = await self.db.get(RegistrationEmailDomainRule, rule_id)
        if row is None:
            raise ApiError(status_code=404, code=404, message="Rule not found")

        changed = False
        if payload.name is not None:
            next_name = payload.name.strip()
            if next_name.lower() != row.name.lower():
                await self._ensure_name_unique(name=next_name, exclude_rule_id=rule_id)
            row.name = next_name
            changed = True
        if payload.pattern is not None:
            next_pattern = payload.pattern.strip()
            self._validate_pattern(next_pattern)
            row.pattern = next_pattern
            changed = True
        if payload.enabled is not None:
            row.enabled = payload.enabled
            changed = True

        if changed:
            row.updated_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(row)
        return self._to_item(row)

    async def delete_rule(self, *, rule_id: int) -> None:
        row = await self.db.get(RegistrationEmailDomainRule, rule_id)
        if row is None:
            raise ApiError(status_code=404, code=404, message="Rule not found")
        await self.db.delete(row)
        await self.db.commit()

    async def assert_email_allowed(self, *, email: str) -> None:
        domain = self._extract_domain(email)
        rules = list(
            await self.db.scalars(
                select(RegistrationEmailDomainRule).where(RegistrationEmailDomainRule.enabled.is_(True))
            )
        )
        if not rules:
            raise ApiError(status_code=400, code=400, message=self._DISALLOWED_MESSAGE)

        for rule in rules:
            try:
                if re.fullmatch(rule.pattern, domain):
                    return
            except re.error:
                continue
        raise ApiError(status_code=400, code=400, message=self._DISALLOWED_MESSAGE)

    async def _ensure_name_unique(self, *, name: str, exclude_rule_id: int | None = None) -> None:
        statement: Select[tuple[int]] = select(RegistrationEmailDomainRule.rule_id).where(
            func.lower(RegistrationEmailDomainRule.name) == name.lower()
        )
        if exclude_rule_id is not None:
            statement = statement.where(RegistrationEmailDomainRule.rule_id != exclude_rule_id)
        exists = await self.db.scalar(statement.limit(1))
        if exists is not None:
            raise ApiError(status_code=409, code=409, message="Rule name already exists")

    @classmethod
    def _validate_pattern(cls, pattern: str) -> None:
        if not pattern:
            raise ApiError(status_code=400, code=400, message="pattern cannot be empty")
        if len(pattern) > cls._PATTERN_MAX_LENGTH:
            raise ApiError(status_code=400, code=400, message="pattern is too long")
        if cls._looks_risky_pattern(pattern):
            raise ApiError(status_code=400, code=400, message="Regex pattern is too risky")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ApiError(status_code=400, code=400, message=f"Invalid regex pattern: {exc}") from exc

    @staticmethod
    def _extract_domain(email: str) -> str:
        if "@" not in email:
            raise ApiError(status_code=400, code=400, message="Invalid email")
        _local, sep, domain = email.strip().rpartition("@")
        if not sep or not domain:
            raise ApiError(status_code=400, code=400, message="Invalid email")
        normalized = domain.strip().lower()
        if not normalized:
            raise ApiError(status_code=400, code=400, message="Invalid email")
        return normalized

    @staticmethod
    def _looks_risky_pattern(pattern: str) -> bool:
        # Reject backreferences (\1, \g<...>) and nested quantifiers like (a+)+
        if re.search(r"\\[1-9]", pattern):
            return True
        if re.search(r"\\g<[^>]+>", pattern):
            return True

        depth = 0
        group_has_quantifier: list[bool] = []
        escaped = False
        for index, ch in enumerate(pattern):
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == "(":
                depth += 1
                group_has_quantifier.append(False)
                continue
            if ch in {"*", "+", "?"}:
                if depth > 0 and group_has_quantifier:
                    group_has_quantifier[-1] = True
                continue
            if ch == "{":
                close = pattern.find("}", index + 1)
                if close != -1 and depth > 0 and group_has_quantifier:
                    group_has_quantifier[-1] = True
                continue
            if ch == ")" and depth > 0:
                had_quantifier = group_has_quantifier.pop()
                depth -= 1
                j = index + 1
                while j < len(pattern) and pattern[j] in {" ", "\t"}:
                    j += 1
                if had_quantifier and j < len(pattern):
                    if pattern[j] in {"*", "+", "?"}:
                        return True
                    if pattern[j] == "{":
                        close = pattern.find("}", j + 1)
                        if close != -1:
                            return True
        return False

    @staticmethod
    def _to_item(row: RegistrationEmailDomainRule) -> RegistrationEmailDomainRuleItem:
        return RegistrationEmailDomainRuleItem(
            rule_id=str(row.rule_id),
            name=row.name,
            pattern=row.pattern,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

