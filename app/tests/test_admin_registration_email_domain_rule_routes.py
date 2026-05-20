from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_registration_email_domain_rule_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.schemas.registration_email_domain_rule import RegistrationEmailDomainRuleItem
from fileflash.routers.admin_registration_email_domain_rules import router as admin_router


class StubRuleService:
    async def list_rules(self, *, query):  # noqa: ANN001
        return SimpleNamespace(
            model_dump=lambda **_: {
                "items": [],
                "pagination": {
                    "totalItems": 0,
                    "totalPages": 1,
                    "perPage": query.per_page,
                    "currentPage": query.page,
                    "hasPrev": False,
                    "hasNext": False,
                },
            }
        )

    async def create_rule(self, *, payload):  # noqa: ANN001
        return RegistrationEmailDomainRuleItem(
            rule_id="1",
            name=payload.name,
            pattern=payload.pattern,
            enabled=payload.enabled,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def update_rule(self, *, rule_id: int, payload):  # noqa: ANN001
        return RegistrationEmailDomainRuleItem(
            rule_id=str(rule_id),
            name=payload.name or "existing",
            pattern=payload.pattern or r".*",
            enabled=True if payload.enabled is None else payload.enabled,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def delete_rule(self, *, rule_id: int):  # noqa: ANN001
        _ = rule_id


def _build_client(admin: bool) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_router, prefix="/api/v1")

    app.dependency_overrides[get_registration_email_domain_rule_service] = lambda: StubRuleService()
    if admin:
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1, role="admin")
    else:
        async def _deny():
            raise ApiError(status_code=403, code=403, message="Admin access required")
        app.dependency_overrides[require_admin] = _deny

    return TestClient(app)


def test_admin_can_list_rules() -> None:
    with _build_client(admin=True) as client:
        response = client.get("/api/v1/admin/registration-email-domain-rules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["items"] == []
    assert payload["data"]["pagination"]["totalItems"] == 0


def test_non_admin_forbidden() -> None:
    with _build_client(admin=False) as client:
        response = client.get("/api/v1/admin/registration-email-domain-rules")

    assert response.status_code == 403
    payload = response.json()
    assert payload["success"] is False
    assert payload["message"] == "Admin access required"


def test_admin_create_and_delete_rule() -> None:
    with _build_client(admin=True) as client:
        create_response = client.post(
            "/api/v1/admin/registration-email-domain-rules",
            json={"name": "corp", "pattern": r".*\.corp\.com", "enabled": True},
        )
        delete_response = client.delete("/api/v1/admin/registration-email-domain-rules/1")

    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload["success"] is True
    assert create_payload["data"]["name"] == "corp"
    assert create_payload["data"]["pattern"] == r".*\.corp\.com"

    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload["success"] is True
    assert delete_payload["data"]["ruleId"] == "1"
