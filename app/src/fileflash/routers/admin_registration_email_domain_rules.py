from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from ..core.deps import get_registration_email_domain_rule_service, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.registration_email_domain_rule import (
    CreateRegistrationEmailDomainRuleRequest,
    ListRegistrationEmailDomainRulesQuery,
    UpdateRegistrationEmailDomainRuleRequest,
)
from ..services.registration_email_domain_rule import RegistrationEmailDomainRuleService

router = APIRouter(prefix="/admin/registration-email-domain-rules", tags=["admin"])


@router.get("")
async def list_registration_email_domain_rules(
    query: ListRegistrationEmailDomainRulesQuery = Depends(),
    _: User = Depends(require_admin),
    service: RegistrationEmailDomainRuleService = Depends(get_registration_email_domain_rule_service),
):
    data = await service.list_rules(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Rules fetched successfully")


@router.post("")
async def create_registration_email_domain_rule(
    payload: CreateRegistrationEmailDomainRuleRequest,
    _: User = Depends(require_admin),
    service: RegistrationEmailDomainRuleService = Depends(get_registration_email_domain_rule_service),
):
    item = await service.create_rule(payload=payload)
    return api_success(
        data=item.model_dump(by_alias=True),
        code=201,
        status_code=201,
        message="Rule created successfully",
    )


@router.patch("/{rule_id}")
async def update_registration_email_domain_rule(
    rule_id: int,
    payload: UpdateRegistrationEmailDomainRuleRequest,
    _: User = Depends(require_admin),
    service: RegistrationEmailDomainRuleService = Depends(get_registration_email_domain_rule_service),
):
    item = await service.update_rule(rule_id=rule_id, payload=payload)
    return api_success(data=item.model_dump(by_alias=True), message="Rule updated successfully")


@router.delete("/{rule_id}")
async def delete_registration_email_domain_rule(
    rule_id: int,
    _: User = Depends(require_admin),
    service: RegistrationEmailDomainRuleService = Depends(get_registration_email_domain_rule_service),
):
    await service.delete_rule(rule_id=rule_id)
    return api_success(
        data={
            "ruleId": str(rule_id),
            "deletedAt": datetime.now(UTC).isoformat(),
        },
        message="Rule deleted successfully",
    )


__all__ = ["router"]

