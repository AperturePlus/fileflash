from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import CamelModel, PageQuery


class RegistrationEmailDomainRuleItem(CamelModel):
    rule_id: str
    name: str
    pattern: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ListRegistrationEmailDomainRulesQuery(PageQuery):
    query_text: str | None = None
    enabled: bool | None = None


class CreateRegistrationEmailDomainRuleRequest(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    pattern: str = Field(min_length=1, max_length=512)
    enabled: bool = True


class UpdateRegistrationEmailDomainRuleRequest(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    pattern: str | None = Field(default=None, min_length=1, max_length=512)
    enabled: bool | None = None

