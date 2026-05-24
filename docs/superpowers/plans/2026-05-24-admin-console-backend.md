# Admin Console Backend Implementation Plan (Plan A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `app/src/fileflash/` 下补齐 7 个 `/admin/*` 路由（users / storage / files / moderation / logs / notifications / system），全部接真实 DB；对外形状与现有前端 `web/src/api/*.ts` 期望一致。

**Architecture:** 沿用现有 `routers/admin_registration_email_domain_rules.py` 的模式：`routers/admin_<域>.py` 仅做参数编排 + `api_success` 壳；业务逻辑落在 `services/admin/<域>.py`；Pydantic schema 在 `schemas/admin/<域>.py`（`CamelModel` + `by_alias`）。所有路由 `Depends(require_admin)`。

**Tech Stack:** FastAPI + SQLAlchemy AsyncSession + Pydantic v2 (CamelModel) + Redis (rate-limit) + pytest/AsyncMock。

**Reference Spec:** `docs/superpowers/specs/2026-05-24-admin-console-design.md`

**前置知识（执行前必读）**

1. `core/errors.py`：错误抛 `ApiError(status_code, code, message)`；`code` 是数字（=HTTP 状态码），不是字符串符号。message 用英文短语 + 可选中文。
2. `core/deps.py`：`require_admin` / `get_current_user` / `get_db` 已经存在；新增 service 都按 `get_admin_*_service` 命名加 dep factory。
3. `schemas/common.py`：`CamelModel` 强制 camelCase by alias、`extra="forbid"`、`str_strip_whitespace=True`；`PaginatedData[T]` / `PageQuery(page, per_page)` 直接复用。
4. `agents.md §5`：**用户状态外部语义是 `active | suspended`**，但 `enums.UserStatus` 内部只有 `ACTIVE / PENDING_VERIFICATION / LOCKED / DISABLED`，**没有 SUSPENDED**。映射：
   - 外部 `'active'` ↔ 内部 `UserStatus.ACTIVE`
   - 外部 `'suspended'` ↔ 内部 `UserStatus.DISABLED`（admin 主动停用；`LOCKED` 留给自动锁定）
5. `RegistrationEmailDomainRule` 路由 / 服务 / 测试**保持原样**，不动。
6. 测试目录：`app/tests/test_admin_<域>_routes.py`（路由层 + stub service）和 `test_admin_<域>_service.py`（service 层 + DummySession 或 in-memory 假实现）。
7. 执行命令：在 `app/` 目录下 `uv run pytest tests/test_admin_<域>*.py -v`；类型检查不存在，构建用 `uv run python -c "from fileflash.main import app; print(app.title)"`。

**对 spec 的两处简化（已与执行者明确）**

- spec §3.8 Rate Limit：初版**不扫 Redis**。后端只维护一份"已注册限流规则"的静态枚举，`current_usage / blocked_requests` 暂返回 0。原因：现有 `RedisRateLimiter` 仅暴露 `allow()`，无规则注册中心；如需运行时统计，需先扩展 limiter，留作后续。
- spec §5.3 `notification.broadcast_completed` 事件：本期**不发布**。`Notification` 行写入 + `Log` 写入已足以观测，事件名空挂以待后续 worker 接入。

---

## File Structure

**新建**

```
app/src/fileflash/
  schemas/admin/__init__.py
  schemas/admin/users.py
  schemas/admin/storage.py
  schemas/admin/files.py
  schemas/admin/moderation.py
  schemas/admin/logs.py
  schemas/admin/notifications.py
  schemas/admin/system.py
  services/admin/__init__.py
  services/admin/users.py
  services/admin/storage.py
  services/admin/files.py
  services/admin/moderation.py
  services/admin/logs.py
  services/admin/notifications.py
  services/admin/system.py
  routers/admin_users.py
  routers/admin_storage.py
  routers/admin_files.py
  routers/admin_moderation.py
  routers/admin_logs.py
  routers/admin_notifications.py
  routers/admin_system.py

app/tests/
  test_admin_users_routes.py
  test_admin_users_service.py
  test_admin_storage_routes.py
  test_admin_storage_service.py
  test_admin_files_routes.py
  test_admin_files_service.py
  test_admin_moderation_routes.py
  test_admin_moderation_service.py
  test_admin_logs_routes.py
  test_admin_notifications_routes.py
  test_admin_notifications_service.py
  test_admin_system_routes.py
```

**修改**

```
app/src/fileflash/
  core/deps.py                          ← 加 7 个 get_admin_*_service factory
  routers/__init__.py                   ← include 7 个新 router
  services/messaging.py                 ← 加新事件常量（可选）
  services/rate_limiter.py              ← 加 record_blocked() 累计（5.x 任务）
```

---

## Task 0: 基础设施（admin 包 + 状态映射）

**Files:**
- Create: `app/src/fileflash/schemas/admin/__init__.py`
- Create: `app/src/fileflash/services/admin/__init__.py`
- Create: `app/src/fileflash/services/admin/_status.py`
- Test: `app/tests/test_admin_user_status_mapping.py`

- [ ] **Step 0.1: 建空包（schemas/admin, services/admin）**

```bash
# 创建两个空 __init__.py
```

`app/src/fileflash/schemas/admin/__init__.py`：

```python
"""Admin-only schemas. All requests/responses share CamelModel from schemas.common."""
```

`app/src/fileflash/services/admin/__init__.py`：

```python
"""Admin-only services. Each module owns one /admin/* surface."""
```

- [ ] **Step 0.2: 写失败测试 — 状态映射**

`app/tests/test_admin_user_status_mapping.py`：

```python
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
    # 自动锁定外部仍展示为 suspended（用户不需要区分原因）
    assert internal_to_external(UserStatus.LOCKED) == "suspended"


def test_pending_verification_passthrough() -> None:
    assert internal_to_external(UserStatus.PENDING_VERIFICATION) == "pending_verification"


def test_invalid_external_status_raises() -> None:
    with pytest.raises(ApiError):
        external_to_internal("garbage")
```

- [ ] **Step 0.3: 跑测试验证失败**

Run: `cd app && uv run pytest tests/test_admin_user_status_mapping.py -v`
Expected: ImportError on `fileflash.services.admin._status`

- [ ] **Step 0.4: 实现 _status.py**

`app/src/fileflash/services/admin/_status.py`：

```python
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
```

- [ ] **Step 0.5: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_user_status_mapping.py -v`
Expected: 5 passed

- [ ] **Step 0.6: Commit**

```bash
cd app && git add src/fileflash/schemas/admin/__init__.py src/fileflash/services/admin/__init__.py src/fileflash/services/admin/_status.py
cd .. && git add app/tests/test_admin_user_status_mapping.py
git commit -m "feat(admin): scaffold admin packages and user status mapping"
```

---

## Task 1: Admin Users — schemas + service

**Files:**
- Create: `app/src/fileflash/schemas/admin/users.py`
- Create: `app/src/fileflash/services/admin/users.py`
- Test: `app/tests/test_admin_users_service.py`

- [ ] **Step 1.1: 写 schemas**

`app/src/fileflash/schemas/admin/users.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..common import CamelModel, PageQuery

ExternalUserStatus = Literal["active", "suspended", "pending_verification"]


class AdminUserItem(CamelModel):
    user_id: str
    username: str
    email: str
    role: str
    status: ExternalUserStatus
    email_verified: bool
    email_verified_at: datetime | None = None
    storage_limit: int
    storage_used: int
    usage_percentage: float
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime


class ListAdminUsersQuery(PageQuery):
    search: str | None = None
    status: Literal["active", "suspended"] | None = None
    role: Literal["USER", "ADMIN"] | None = None
    sort: Literal["username", "createdAt", "storageUsed"] = "createdAt"
    order: Literal["asc", "desc"] = "desc"


class UpdateUserStatusRequest(CamelModel):
    status: Literal["active", "suspended"]


class UpdateUserStatusResponse(CamelModel):
    user_id: str
    status: ExternalUserStatus
    updated_at: datetime


__all__ = [
    "AdminUserItem",
    "ListAdminUsersQuery",
    "UpdateUserStatusRequest",
    "UpdateUserStatusResponse",
]
```

- [ ] **Step 1.2: 写失败测试 — list 默认分页**

`app/tests/test_admin_users_service.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import UserRole, UserStatus
from fileflash.models.tables_identity import User
from fileflash.schemas.admin.users import ListAdminUsersQuery
from fileflash.services.admin.users import AdminUsersService


def _user(**kwargs) -> User:
    base = dict(
        user_id=1,
        username="alice",
        email="alice@example.com",
        password_hash="x",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        email_verified_at=datetime.now(UTC),
        storage_limit=10 * 1024 * 1024 * 1024,
        storage_used=1024,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return User(**base)


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_list_users_returns_paginated_items() -> None:
    session = DummySession()
    session.scalar.return_value = 1
    session.scalars.return_value = [_user()]
    session.execute.return_value = Mock(all=lambda: [])  # no sessions joined
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    result = await service.list_users(query=ListAdminUsersQuery())

    assert result.pagination.total_items == 1
    assert result.items[0].username == "alice"
    assert result.items[0].status == "active"
```

- [ ] **Step 1.3: 跑测试验证失败**

Run: `cd app && uv run pytest tests/test_admin_users_service.py -v`
Expected: ImportError on `fileflash.services.admin.users`

- [ ] **Step 1.4: 实现 AdminUsersService 的 list_users**

`app/src/fileflash/services/admin/users.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import UserRole, UserStatus
from ...models.tables_identity import User, UserSession
from ...schemas.admin.users import (
    AdminUserItem,
    ListAdminUsersQuery,
    UpdateUserStatusResponse,
)
from ...schemas.common import PaginatedData, PaginationMeta
from ._status import external_to_internal, internal_to_external


class AdminUsersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_users(
        self,
        *,
        query: ListAdminUsersQuery,
    ) -> PaginatedData[AdminUserItem]:
        statement = select(User).where(User.deleted_at.is_(None))

        if query.search:
            keyword = f"%{query.search.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(User.username).like(keyword),
                    func.lower(User.email).like(keyword),
                )
            )
        if query.status:
            statement = statement.where(User.status == external_to_internal(query.status))
        if query.role:
            statement = statement.where(User.role == UserRole(query.role))

        sort_column = {
            "username": User.username,
            "createdAt": User.created_at,
            "storageUsed": User.storage_used,
        }[query.sort]
        statement = statement.order_by(
            sort_column.desc() if query.order == "desc" else sort_column.asc()
        )

        total = await self.db.scalar(select(func.count()).select_from(statement.subquery()))
        total_items = int(total or 0)
        total_pages = max(1, -(-total_items // query.per_page))
        offset = (query.page - 1) * query.per_page

        rows = list(
            await self.db.scalars(statement.offset(offset).limit(query.per_page))
        )

        last_seen_map = await self._collect_last_seen([row.user_id for row in rows])
        items = [self._to_item(row, last_seen_map.get(row.user_id)) for row in rows]

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

    async def _collect_last_seen(self, user_ids: list[int]) -> dict[int, datetime]:
        if not user_ids:
            return {}
        rows = await self.db.execute(
            select(UserSession.user_id, func.max(UserSession.last_seen_at))
            .where(
                and_(
                    UserSession.user_id.in_(user_ids),
                    UserSession.revoked_at.is_(None),
                )
            )
            .group_by(UserSession.user_id)
        )
        return {user_id: seen for user_id, seen in rows.all()}

    @staticmethod
    def _to_item(row: User, last_active_at: datetime | None) -> AdminUserItem:
        limit = max(row.storage_limit, 1)
        return AdminUserItem(
            user_id=str(row.user_id),
            username=row.username,
            email=row.email,
            role=row.role.value if hasattr(row.role, "value") else str(row.role),
            status=internal_to_external(row.status),  # type: ignore[arg-type]
            email_verified=row.email_verified,
            email_verified_at=row.email_verified_at,
            storage_limit=row.storage_limit,
            storage_used=row.storage_used,
            usage_percentage=round((row.storage_used / limit) * 100, 2),
            last_login_at=row.last_login_at,
            last_active_at=last_active_at,
            created_at=row.created_at,
        )


__all__ = ["AdminUsersService"]
```

- [ ] **Step 1.5: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_users_service.py -v`
Expected: 1 passed

- [ ] **Step 1.6: 写失败测试 — set_status（成功 + 防误锁 + 404）**

追加到 `app/tests/test_admin_users_service.py`：

```python
@pytest.mark.asyncio
async def test_set_status_user_not_found() -> None:
    session = DummySession()
    session.get.return_value = None
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.set_status(user_id=999, external_status="suspended")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_set_status_suspend_last_admin_blocked() -> None:
    session = DummySession()
    admin = _user(user_id=2, role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    session.get.return_value = admin
    # 当前活跃 admin 仅 1 名 => 不允许 suspend
    session.scalar.return_value = 1
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.set_status(user_id=2, external_status="suspended")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_set_status_suspends_user_and_revokes_sessions() -> None:
    session = DummySession()
    target = _user(user_id=3)
    session.get.return_value = target
    session.scalar.return_value = 5  # active admins enough
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    result = await service.set_status(user_id=3, external_status="suspended")

    assert result.status == "suspended"
    assert target.status == UserStatus.DISABLED
    session.commit.assert_awaited()
```

- [ ] **Step 1.7: 跑测试验证失败**

Run: `cd app && uv run pytest tests/test_admin_users_service.py -v`
Expected: AttributeError on `service.set_status`

- [ ] **Step 1.8: 实现 set_status**

追加到 `app/src/fileflash/services/admin/users.py`（在类内）：

```python
    async def set_status(
        self,
        *,
        user_id: int,
        external_status: str,
    ) -> UpdateUserStatusResponse:
        target = await self.db.get(User, user_id)
        if target is None or target.deleted_at is not None:
            raise ApiError(status_code=404, code=404, message="User not found")

        new_internal = external_to_internal(external_status)

        if (
            new_internal == UserStatus.DISABLED
            and target.role == UserRole.ADMIN
            and target.status == UserStatus.ACTIVE
        ):
            remaining = await self.db.scalar(
                select(func.count(User.user_id)).where(
                    and_(
                        User.role == UserRole.ADMIN,
                        User.status == UserStatus.ACTIVE,
                        User.user_id != user_id,
                        User.deleted_at.is_(None),
                    )
                )
            )
            if int(remaining or 0) == 0:
                raise ApiError(
                    status_code=409,
                    code=409,
                    message="Cannot suspend the last active admin",
                )

        target.status = new_internal
        target.updated_at = datetime.now(UTC)

        if new_internal == UserStatus.DISABLED:
            await self.db.execute(
                UserSession.__table__.update()
                .where(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.revoked_at.is_(None),
                    )
                )
                .values(revoked_at=datetime.now(UTC))
            )

        await self.db.commit()
        await self.db.refresh(target)

        return UpdateUserStatusResponse(
            user_id=str(target.user_id),
            status=internal_to_external(target.status),  # type: ignore[arg-type]
            updated_at=target.updated_at,
        )
```

- [ ] **Step 1.9: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_users_service.py -v`
Expected: 4 passed

- [ ] **Step 1.10: Commit**

```bash
git add app/src/fileflash/schemas/admin/users.py app/src/fileflash/services/admin/users.py app/tests/test_admin_users_service.py
git commit -m "feat(admin): users service with list and set_status (last-admin guard)"
```

---

## Task 2: Admin Users — router + deps + 注册

**Files:**
- Create: `app/src/fileflash/routers/admin_users.py`
- Modify: `app/src/fileflash/core/deps.py`
- Modify: `app/src/fileflash/routers/__init__.py`
- Test: `app/tests/test_admin_users_routes.py`

- [ ] **Step 2.1: 写失败测试 — 403 给非 admin / 200 给 admin**

`app/tests/test_admin_users_routes.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_users import (
    router as admin_users_router,
    get_admin_users_service,
)
from fileflash.schemas.admin.users import (
    AdminUserItem,
    UpdateUserStatusResponse,
)
from fileflash.schemas.common import PaginatedData, PaginationMeta


class StubService:
    async def list_users(self, *, query):  # noqa: ANN001
        item = AdminUserItem(
            user_id="1", username="alice", email="a@x.com", role="USER",
            status="active", email_verified=True, email_verified_at=None,
            storage_limit=1024, storage_used=0, usage_percentage=0.0,
            last_login_at=None, last_active_at=None, created_at=datetime.now(UTC),
        )
        return PaginatedData(
            items=[item],
            pagination=PaginationMeta(
                total_items=1, total_pages=1,
                per_page=query.per_page, current_page=query.page,
                has_prev=False, has_next=False,
            ),
        )

    async def set_status(self, *, user_id, external_status):  # noqa: ANN001
        return UpdateUserStatusResponse(
            user_id=str(user_id), status=external_status,
            updated_at=datetime.now(UTC),
        )


def _client(admin: bool) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_users_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_users_service] = lambda: StubService()
    if admin:
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    else:
        async def _deny():
            raise ApiError(status_code=403, code=403, message="forbidden")
        app.dependency_overrides[require_admin] = _deny
    return TestClient(app)


def test_admin_can_list_users() -> None:
    with _client(admin=True) as c:
        resp = c.get("/api/v1/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["items"][0]["username"] == "alice"


def test_non_admin_gets_403() -> None:
    with _client(admin=False) as c:
        resp = c.get("/api/v1/admin/users")
    assert resp.status_code == 403


def test_admin_can_patch_status() -> None:
    with _client(admin=True) as c:
        resp = c.patch("/api/v1/admin/users/42/status", json={"status": "suspended"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "suspended"
```

- [ ] **Step 2.2: 跑测试验证失败**

Run: `cd app && uv run pytest tests/test_admin_users_routes.py -v`
Expected: ImportError on `fileflash.routers.admin_users`

- [ ] **Step 2.3: 实现 router + 局部 dep factory**

`app/src/fileflash/routers/admin_users.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import require_admin
from ..core.errors import api_success
from ..db.deps import get_db
from ..models.tables_identity import User
from ..schemas.admin.users import (
    ListAdminUsersQuery,
    UpdateUserStatusRequest,
)
from ..services.admin.users import AdminUsersService

router = APIRouter(prefix="/admin/users", tags=["admin"])


def get_admin_users_service(db: AsyncSession = Depends(get_db)) -> AdminUsersService:
    return AdminUsersService(db=db)


@router.get("")
async def list_admin_users(
    query: ListAdminUsersQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminUsersService = Depends(get_admin_users_service),
):
    data = await service.list_users(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Users fetched")


@router.patch("/{user_id}/status")
async def update_admin_user_status(
    user_id: int,
    payload: UpdateUserStatusRequest,
    _: User = Depends(require_admin),
    service: AdminUsersService = Depends(get_admin_users_service),
):
    result = await service.set_status(user_id=user_id, external_status=payload.status)
    return api_success(data=result.model_dump(by_alias=True), message="Status updated")


__all__ = ["router", "get_admin_users_service"]
```

- [ ] **Step 2.4: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_users_routes.py -v`
Expected: 3 passed

- [ ] **Step 2.5: 注册 router 到 api_router**

Modify `app/src/fileflash/routers/__init__.py`：在 imports 区追加

```python
from .admin_users import router as admin_users_router
```

在 `include_router` 区追加

```python
api_router.include_router(admin_users_router)
```

- [ ] **Step 2.6: 冒烟启动**

Run: `cd app && uv run python -c "from fileflash.main import app; print([r.path for r in app.routes if '/admin/users' in r.path])"`
Expected: prints `['/api/v1/admin/users', '/api/v1/admin/users/{user_id}/status']`

- [ ] **Step 2.7: Commit**

```bash
git add app/src/fileflash/routers/admin_users.py app/src/fileflash/routers/__init__.py app/tests/test_admin_users_routes.py
git commit -m "feat(admin): /admin/users list + /admin/users/{id}/status routes"
```

---

## Task 3: Admin Storage（summary / users / quota / usage-trend）

**Files:**
- Create: `app/src/fileflash/schemas/admin/storage.py`
- Create: `app/src/fileflash/services/admin/storage.py`
- Create: `app/src/fileflash/routers/admin_storage.py`
- Modify: `app/src/fileflash/routers/__init__.py`
- Test: `app/tests/test_admin_storage_service.py`, `app/tests/test_admin_storage_routes.py`

- [ ] **Step 3.1: 写 schemas**

`app/src/fileflash/schemas/admin/storage.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..common import CamelModel, PageQuery


class AdminStorageSummary(CamelModel):
    storage_used: int
    storage_limit: int
    storage_percentage: float
    file_count: int
    user_count: int
    updated_at: datetime


class AdminStorageUserItem(CamelModel):
    user_id: str
    username: str
    email: str
    storage_limit: int
    storage_used: int
    usage_percentage: float
    updated_at: datetime


class ListStorageUsersQuery(PageQuery):
    sort: Literal["storageUsed", "usagePercentage", "username"] = "storageUsed"
    order: Literal["asc", "desc"] = "desc"


class UpdateQuotaRequest(CamelModel):
    storage_limit: int = Field(ge=0)


class UpdateQuotaResponse(CamelModel):
    user_id: str
    storage_limit: int
    storage_used: int
    usage_percentage: float
    updated_at: datetime


class UsageTrendQuery(CamelModel):
    days: Literal[7, 14, 30] = 7


class UsageTrendPoint(CamelModel):
    date: str
    used: int


class UsageTrendResponse(CamelModel):
    trends: list[UsageTrendPoint]
    is_estimated: bool = False


__all__ = [
    "AdminStorageSummary",
    "AdminStorageUserItem",
    "ListStorageUsersQuery",
    "UpdateQuotaRequest",
    "UpdateQuotaResponse",
    "UsageTrendQuery",
    "UsageTrendPoint",
    "UsageTrendResponse",
]
```

- [ ] **Step 3.2: 写失败测试 — summary / quota / usage-trend**

`app/tests/test_admin_storage_service.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.tables_identity import User
from fileflash.models.enums import UserRole, UserStatus
from fileflash.schemas.admin.storage import ListStorageUsersQuery, UsageTrendQuery
from fileflash.services.admin.storage import AdminStorageService


def _user(**kwargs) -> User:
    base = dict(
        user_id=1, username="bob", email="b@x.com", password_hash="x",
        role=UserRole.USER, status=UserStatus.ACTIVE,
        email_verified=True, email_verified_at=datetime.now(UTC),
        storage_limit=10 * 1024 * 1024 * 1024, storage_used=2 * 1024 * 1024 * 1024,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return User(**base)


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_summary_aggregates_users_and_files() -> None:
    session = DummySession()
    # 三次 scalar 调用：sum(storage_used), sum(storage_limit), count(files), count(users)
    session.scalar.side_effect = [
        2 * 1024 * 1024 * 1024,    # storage_used sum
        10 * 1024 * 1024 * 1024,   # storage_limit sum
        42,                        # file count
        7,                         # user count
    ]
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    result = await service.summary()

    assert result.storage_used == 2 * 1024 * 1024 * 1024
    assert result.user_count == 7
    assert result.file_count == 42
    assert round(result.storage_percentage, 2) == 20.0


@pytest.mark.asyncio
async def test_update_quota_rejects_below_usage() -> None:
    session = DummySession()
    target = _user(storage_used=5 * 1024 * 1024 * 1024)
    session.get.return_value = target
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.update_quota(user_id=1, new_limit=1 * 1024 * 1024 * 1024)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_quota_success_updates_and_commits() -> None:
    session = DummySession()
    target = _user(storage_used=1 * 1024 * 1024 * 1024)
    session.get.return_value = target
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    result = await service.update_quota(user_id=1, new_limit=20 * 1024 * 1024 * 1024)

    assert result.storage_limit == 20 * 1024 * 1024 * 1024
    assert target.storage_limit == 20 * 1024 * 1024 * 1024
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_usage_trend_returns_n_points() -> None:
    session = DummySession()
    session.scalar.return_value = 2 * 1024 * 1024 * 1024  # T_now
    session.execute.return_value = Mock(all=lambda: [])  # no events
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    result = await service.usage_trend(query=UsageTrendQuery(days=7))

    assert len(result.trends) == 7
    assert result.is_estimated is True  # no events => 估算
```

- [ ] **Step 3.3: 跑测试验证失败**

Run: `cd app && uv run pytest tests/test_admin_storage_service.py -v`
Expected: ImportError

- [ ] **Step 3.4: 实现 AdminStorageService**

`app/src/fileflash/services/admin/storage.py`：

```python
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.tables_audit_security import Log
from ...models.tables_identity import User
from ...models.tables_storage import File
from ...schemas.admin.storage import (
    AdminStorageSummary,
    AdminStorageUserItem,
    ListStorageUsersQuery,
    UpdateQuotaResponse,
    UsageTrendPoint,
    UsageTrendQuery,
    UsageTrendResponse,
)
from ...schemas.common import PaginatedData, PaginationMeta

_STORAGE_EVENT_OPS = ("file.created", "file.deleted", "file.restored")
_TREND_CACHE_TTL = 300


class AdminStorageService:
    def __init__(self, db: AsyncSession, redis: Redis | None) -> None:
        self.db = db
        self.redis = redis

    async def summary(self) -> AdminStorageSummary:
        used_sum = await self.db.scalar(select(func.coalesce(func.sum(User.storage_used), 0)))
        limit_sum = await self.db.scalar(select(func.coalesce(func.sum(User.storage_limit), 0)))
        file_count = await self.db.scalar(select(func.count(File.file_id)))
        user_count = await self.db.scalar(
            select(func.count(User.user_id)).where(User.deleted_at.is_(None))
        )

        used = int(used_sum or 0)
        limit = int(limit_sum or 0)
        return AdminStorageSummary(
            storage_used=used,
            storage_limit=limit,
            storage_percentage=round((used / limit) * 100, 2) if limit else 0.0,
            file_count=int(file_count or 0),
            user_count=int(user_count or 0),
            updated_at=datetime.now(UTC),
        )

    async def list_storage_users(
        self,
        *,
        query: ListStorageUsersQuery,
    ) -> PaginatedData[AdminStorageUserItem]:
        statement = select(User).where(User.deleted_at.is_(None))

        sort_column = {
            "storageUsed": User.storage_used,
            "username": User.username,
            "usagePercentage": User.storage_used,  # 近似按 storage_used 排序
        }[query.sort]
        statement = statement.order_by(
            sort_column.desc() if query.order == "desc" else sort_column.asc()
        )

        total = await self.db.scalar(select(func.count()).select_from(statement.subquery()))
        total_items = int(total or 0)
        total_pages = max(1, -(-total_items // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))

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

    async def update_quota(self, *, user_id: int, new_limit: int) -> UpdateQuotaResponse:
        target = await self.db.get(User, user_id, with_for_update=True)
        if target is None or target.deleted_at is not None:
            raise ApiError(status_code=404, code=404, message="User not found")

        if new_limit < target.storage_used:
            raise ApiError(
                status_code=409,
                code=409,
                message="New quota cannot be below current usage",
            )

        target.storage_limit = new_limit
        target.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(target)
        return UpdateQuotaResponse(
            user_id=str(target.user_id),
            storage_limit=target.storage_limit,
            storage_used=target.storage_used,
            usage_percentage=round((target.storage_used / max(target.storage_limit, 1)) * 100, 2),
            updated_at=target.updated_at,
        )

    async def usage_trend(self, *, query: UsageTrendQuery) -> UsageTrendResponse:
        cached = await self._cache_get(query.days)
        if cached is not None:
            return cached

        t_now = int(
            await self.db.scalar(select(func.coalesce(func.sum(User.storage_used), 0))) or 0
        )

        cutoff = datetime.now(UTC) - timedelta(days=query.days)
        rows = await self.db.execute(
            select(Log.operation, Log.metadata_payload, Log.performed_at)
            .where(Log.operation.in_(_STORAGE_EVENT_OPS))
            .where(Log.performed_at >= cutoff)
        )
        events = rows.all()

        deltas: dict[date, int] = {}
        for op, metadata, performed_at in events:
            if not performed_at:
                continue
            size = int((metadata or {}).get("size") or 0)
            sign = 1 if op == "file.created" or op == "file.restored" else -1
            day = performed_at.astimezone(UTC).date()
            deltas[day] = deltas.get(day, 0) + sign * size

        today = datetime.now(UTC).date()
        points: list[UsageTrendPoint] = []
        running = t_now
        for offset in range(query.days):
            d = today - timedelta(days=offset)
            points.append(UsageTrendPoint(date=d.isoformat(), used=max(running, 0)))
            running -= deltas.get(d, 0)
        points.reverse()

        response = UsageTrendResponse(
            trends=points,
            is_estimated=not events,
        )
        await self._cache_set(query.days, response)
        return response

    @staticmethod
    def _to_item(row: User) -> AdminStorageUserItem:
        limit = max(row.storage_limit, 1)
        return AdminStorageUserItem(
            user_id=str(row.user_id),
            username=row.username,
            email=row.email,
            storage_limit=row.storage_limit,
            storage_used=row.storage_used,
            usage_percentage=round((row.storage_used / limit) * 100, 2),
            updated_at=row.updated_at,
        )

    async def _cache_get(self, days: int) -> UsageTrendResponse | None:
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(f"admin:storage:trend:{days}")
        except Exception:
            return None
        if not raw:
            return None
        return UsageTrendResponse.model_validate_json(raw)

    async def _cache_set(self, days: int, payload: UsageTrendResponse) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.setex(
                f"admin:storage:trend:{days}",
                _TREND_CACHE_TTL,
                payload.model_dump_json(by_alias=True),
            )
        except Exception:
            return


__all__ = ["AdminStorageService"]
```

- [ ] **Step 3.5: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_storage_service.py -v`
Expected: 4 passed

- [ ] **Step 3.6: 实现 router + 注册**

`app/src/fileflash/routers/admin_storage.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_rate_limiter, require_admin
from ..core.errors import api_success
from ..db.deps import get_db
from ..models.tables_identity import User
from ..schemas.admin.storage import (
    ListStorageUsersQuery,
    UpdateQuotaRequest,
    UsageTrendQuery,
)
from ..services.admin.storage import AdminStorageService
from ..services.rate_limiter import RedisRateLimiter

router = APIRouter(prefix="/admin/storage", tags=["admin"])


def get_admin_storage_service(
    db: AsyncSession = Depends(get_db),
    rate_limiter: RedisRateLimiter = Depends(get_rate_limiter),
) -> AdminStorageService:
    # 复用现有 RedisRateLimiter 持有的连接，仅当存在时启用缓存
    return AdminStorageService(db=db, redis=getattr(rate_limiter, "_redis", None))


@router.get("/summary")
async def get_admin_storage_summary(
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    data = await service.summary()
    return api_success(data=data.model_dump(by_alias=True), message="Storage summary fetched")


@router.get("/users")
async def list_admin_storage_users(
    query: ListStorageUsersQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    data = await service.list_storage_users(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Storage users fetched")


@router.patch("/users/{user_id}/quota")
async def update_admin_user_quota(
    user_id: int,
    payload: UpdateQuotaRequest,
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    result = await service.update_quota(user_id=user_id, new_limit=payload.storage_limit)
    return api_success(data=result.model_dump(by_alias=True), message="Quota updated")


@router.get("/usage-trend")
async def get_storage_usage_trend(
    query: UsageTrendQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminStorageService = Depends(get_admin_storage_service),
):
    result = await service.usage_trend(query=query)
    return api_success(data=result.model_dump(by_alias=True), message="Usage trend fetched")


__all__ = ["router", "get_admin_storage_service"]
```

- [ ] **Step 3.7: 写路由测试**

`app/tests/test_admin_storage_routes.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_storage import router as storage_router, get_admin_storage_service
from fileflash.schemas.admin.storage import (
    AdminStorageSummary,
    UpdateQuotaResponse,
    UsageTrendPoint,
    UsageTrendResponse,
)


class StubService:
    async def summary(self):
        return AdminStorageSummary(
            storage_used=1000, storage_limit=10000, storage_percentage=10.0,
            file_count=3, user_count=2, updated_at=datetime.now(UTC),
        )

    async def list_storage_users(self, *, query):  # noqa: ANN001
        return SimpleNamespace(model_dump=lambda **_: {
            "items": [],
            "pagination": {
                "totalItems": 0, "totalPages": 1,
                "perPage": query.per_page, "currentPage": query.page,
                "hasPrev": False, "hasNext": False,
            },
        })

    async def update_quota(self, *, user_id, new_limit):  # noqa: ANN001
        return UpdateQuotaResponse(
            user_id=str(user_id), storage_limit=new_limit,
            storage_used=0, usage_percentage=0.0, updated_at=datetime.now(UTC),
        )

    async def usage_trend(self, *, query):  # noqa: ANN001
        return UsageTrendResponse(
            trends=[UsageTrendPoint(date="2026-05-24", used=1)],
            is_estimated=False,
        )


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(storage_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_storage_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_summary_returns_camel_case() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/storage/summary")
    assert resp.status_code == 200
    assert "storageUsed" in resp.json()["data"]


def test_update_quota_passes_storage_limit() -> None:
    with _client() as c:
        resp = c.patch("/api/v1/admin/storage/users/7/quota", json={"storageLimit": 1024})
    assert resp.status_code == 200
    assert resp.json()["data"]["storageLimit"] == 1024


def test_usage_trend_default_days() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/storage/usage-trend")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["trends"]) == 1
```

- [ ] **Step 3.8: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_storage_routes.py -v`
Expected: 3 passed

- [ ] **Step 3.9: 注册 router**

Modify `app/src/fileflash/routers/__init__.py`：

```python
from .admin_storage import router as admin_storage_router
# ...
api_router.include_router(admin_storage_router)
```

- [ ] **Step 3.10: Commit**

```bash
git add app/src/fileflash/schemas/admin/storage.py \
        app/src/fileflash/services/admin/storage.py \
        app/src/fileflash/routers/admin_storage.py \
        app/src/fileflash/routers/__init__.py \
        app/tests/test_admin_storage_service.py \
        app/tests/test_admin_storage_routes.py
git commit -m "feat(admin): /admin/storage summary, users, quota, usage-trend"
```

---

## Task 4: Admin Files（list + rescan）

**Files:**
- Create: `app/src/fileflash/schemas/admin/files.py`
- Create: `app/src/fileflash/services/admin/files.py`
- Create: `app/src/fileflash/routers/admin_files.py`
- Test: `app/tests/test_admin_files_service.py`, `app/tests/test_admin_files_routes.py`
- Modify: `app/src/fileflash/routers/__init__.py`

- [ ] **Step 4.1: 写 schemas**

`app/src/fileflash/schemas/admin/files.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..common import CamelModel, PageQuery


VirusStatus = Literal["clean", "pending", "flagged"]


class AdminFileAuditItem(CamelModel):
    id: str
    name: str
    size: int
    mime_type: str
    hash: str
    virus_status: VirusStatus
    is_shared: bool
    owner_name: str
    updated_at: datetime
    created_at: datetime


class ListAdminFilesQuery(PageQuery):
    search: str | None = None
    virus_status: VirusStatus | None = None
    owner_id: str | None = None
    mime_type: str | None = None
    sort: Literal["name", "size", "createdAt", "updatedAt"] = "updatedAt"
    order: Literal["asc", "desc"] = "desc"


class RescanResponse(CamelModel):
    file_id: str
    virus_status: VirusStatus
    scanned_at: datetime


__all__ = ["AdminFileAuditItem", "ListAdminFilesQuery", "RescanResponse", "VirusStatus"]
```

- [ ] **Step 4.2: 写失败测试 — list + rescan**

`app/tests/test_admin_files_service.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.schemas.admin.files import ListAdminFilesQuery
from fileflash.services.admin.files import AdminFilesService


class DummyPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, payload: dict) -> None:  # noqa: ANN001
        self.calls.append((event_name, payload))


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()


@pytest.mark.asyncio
async def test_list_returns_paginated_empty_when_no_files() -> None:
    session = DummySession()
    session.scalar.return_value = 0
    session.execute.return_value = Mock(all=lambda: [])
    service = AdminFilesService(db=session, publisher=DummyPublisher())  # type: ignore[arg-type]

    result = await service.list_files(query=ListAdminFilesQuery())

    assert result.items == []
    assert result.pagination.total_items == 0


@pytest.mark.asyncio
async def test_rescan_missing_file_returns_404() -> None:
    session = DummySession()
    session.get.return_value = None
    service = AdminFilesService(db=session, publisher=DummyPublisher())  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.request_rescan(file_id=1, requested_by=99)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_rescan_inserts_scan_record_and_publishes_event() -> None:
    session = DummySession()
    file_row = Mock(file_id=1, object_id=2)
    session.get.return_value = file_row
    publisher = DummyPublisher()
    service = AdminFilesService(db=session, publisher=publisher)  # type: ignore[arg-type]

    result = await service.request_rescan(file_id=1, requested_by=99)

    assert result.virus_status == "pending"
    assert publisher.calls and publisher.calls[0][0] == "files.rescan_requested"
    session.commit.assert_awaited()
```

- [ ] **Step 4.3: 跑测试验证失败**

Run: `cd app && uv run pytest tests/test_admin_files_service.py -v`
Expected: ImportError

- [ ] **Step 4.4: 实现 AdminFilesService**

`app/src/fileflash/services/admin/files.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import FileStatus, ScanResult
from ...models.tables_audit_security import ObjectScanResult
from ...models.tables_identity import User
from ...models.tables_storage import File, StorageObject
from ...schemas.admin.files import (
    AdminFileAuditItem,
    ListAdminFilesQuery,
    RescanResponse,
    VirusStatus,
)
from ...schemas.common import PaginatedData, PaginationMeta


class EventPublisherProtocol(Protocol):
    async def publish(self, event_name: str, payload: dict[str, Any]) -> None: ...


_VIRUS_STATUS_MAP: dict[ScanResult, VirusStatus] = {
    ScanResult.CLEAN: "clean",
    ScanResult.PENDING: "pending",
    ScanResult.INFECTED: "flagged",
    ScanResult.BLOCKED: "flagged",
    ScanResult.FAILED: "pending",
}


class AdminFilesService:
    def __init__(self, db: AsyncSession, publisher: EventPublisherProtocol) -> None:
        self.db = db
        self.publisher = publisher

    async def list_files(
        self,
        *,
        query: ListAdminFilesQuery,
    ) -> PaginatedData[AdminFileAuditItem]:
        # 最近一次扫描结果 sub-query
        latest_scan = (
            select(
                ObjectScanResult.object_id,
                func.max(ObjectScanResult.scanned_at).label("scanned_at"),
            )
            .group_by(ObjectScanResult.object_id)
            .subquery()
        )

        statement = (
            select(File, StorageObject, User, ObjectScanResult)
            .join(StorageObject, File.storage_object_id == StorageObject.object_id)
            .join(User, File.owner_id == User.user_id)
            .join(
                latest_scan,
                latest_scan.c.object_id == StorageObject.object_id,
                isouter=True,
            )
            .join(
                ObjectScanResult,
                and_(
                    ObjectScanResult.object_id == latest_scan.c.object_id,
                    ObjectScanResult.scanned_at == latest_scan.c.scanned_at,
                ),
                isouter=True,
            )
            .where(File.status == FileStatus.ACTIVE)
            .where(File.deleted_at.is_(None))
        )

        if query.search:
            kw = f"%{query.search.strip().lower()}%"
            statement = statement.where(func.lower(File.file_name).like(kw))
        if query.owner_id:
            statement = statement.where(File.owner_id == int(query.owner_id))
        if query.mime_type:
            statement = statement.where(File.mime_type == query.mime_type)
        if query.virus_status:
            wanted = [k for k, v in _VIRUS_STATUS_MAP.items() if v == query.virus_status]
            statement = statement.where(ObjectScanResult.result.in_(wanted))

        sort_column = {
            "name": File.file_name,
            "size": File.file_size,
            "createdAt": File.created_at,
            "updatedAt": File.updated_at,
        }[query.sort]
        statement = statement.order_by(
            sort_column.desc() if query.order == "desc" else sort_column.asc()
        )

        count_stmt = select(func.count()).select_from(statement.subquery())
        total = int(await self.db.scalar(count_stmt) or 0)
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page

        rows = (await self.db.execute(statement.offset(offset).limit(query.per_page))).all()
        items = [self._to_item(file_, obj, owner, scan) for file_, obj, owner, scan in rows]

        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def request_rescan(self, *, file_id: int, requested_by: int) -> RescanResponse:
        file_row = await self.db.get(File, file_id)
        if file_row is None or file_row.deleted_at is not None or file_row.status != FileStatus.ACTIVE:
            raise ApiError(status_code=404, code=404, message="File not found")

        now = datetime.now(UTC)
        scan = ObjectScanResult(
            object_id=file_row.storage_object_id,
            scan_type="virus",
            result=ScanResult.PENDING,
            details={"requestedBy": requested_by},
            scanned_at=now,
            created_at=now,
        )
        self.db.add(scan)
        await self.db.commit()

        await self.publisher.publish(
            "files.rescan_requested",
            {
                "fileId": str(file_id),
                "objectId": str(file_row.storage_object_id),
                "requestedBy": requested_by,
            },
        )

        return RescanResponse(
            file_id=str(file_id),
            virus_status="pending",
            scanned_at=now,
        )

    @staticmethod
    def _to_item(
        file_: File,
        obj: StorageObject,
        owner: User,
        scan: ObjectScanResult | None,
    ) -> AdminFileAuditItem:
        return AdminFileAuditItem(
            id=str(file_.file_id),
            name=file_.file_name,
            size=file_.file_size,
            mime_type=file_.mime_type or obj.content_type or "application/octet-stream",
            hash=(obj.object_hash or "")[:16],
            virus_status=_VIRUS_STATUS_MAP.get(scan.result, "pending") if scan else "pending",
            is_shared=False,
            owner_name=owner.username,
            updated_at=file_.updated_at,
            created_at=file_.created_at,
        )


__all__ = ["AdminFilesService"]
```

> **校对依据：** `File` 字段 `file_name / file_size / mime_type / storage_object_id / owner_id / status / deleted_at`；`StorageObject` 字段 `object_hash / content_type / object_size`；`ScanResult` 枚举 `PENDING / CLEAN / INFECTED / BLOCKED / FAILED`。已与 `app/src/fileflash/models/tables_storage.py` 和 `enums.py` 核对一致。

- [ ] **Step 4.5: 写 rescan service 测试中 file_row 的 mock 字段对齐**

更新 Step 4.2 中 `test_rescan_inserts_scan_record_and_publishes_event`：

```python
@pytest.mark.asyncio
async def test_rescan_inserts_scan_record_and_publishes_event() -> None:
    from fileflash.models.enums import FileStatus
    session = DummySession()
    file_row = Mock(
        file_id=1, storage_object_id=2,
        deleted_at=None, status=FileStatus.ACTIVE,
    )
    session.get.return_value = file_row
    publisher = DummyPublisher()
    service = AdminFilesService(db=session, publisher=publisher)  # type: ignore[arg-type]

    result = await service.request_rescan(file_id=1, requested_by=99)

    assert result.virus_status == "pending"
    assert publisher.calls and publisher.calls[0][0] == "files.rescan_requested"
    session.commit.assert_awaited()
```

- [ ] **Step 4.6: 跑测试验证通过**

Run: `cd app && uv run pytest tests/test_admin_files_service.py -v`
Expected: 3 passed

- [ ] **Step 4.7: 实现 router + 测试 + 注册**

`app/src/fileflash/routers/admin_files.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_event_publisher, require_admin
from ..core.errors import api_success
from ..db.deps import get_db
from ..models.tables_identity import User
from ..schemas.admin.files import ListAdminFilesQuery
from ..services.admin.files import AdminFilesService
from ..services.messaging import InProcessAuthEventPublisher

router = APIRouter(prefix="/admin/files", tags=["admin"])


def get_admin_files_service(
    db: AsyncSession = Depends(get_db),
    publisher: InProcessAuthEventPublisher = Depends(get_event_publisher),
) -> AdminFilesService:
    return AdminFilesService(db=db, publisher=publisher)


@router.get("")
async def list_admin_files(
    query: ListAdminFilesQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    data = await service.list_files(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Files fetched")


@router.post("/{file_id}/rescan")
async def rescan_admin_file(
    file_id: int,
    admin: User = Depends(require_admin),
    service: AdminFilesService = Depends(get_admin_files_service),
):
    result = await service.request_rescan(file_id=file_id, requested_by=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Rescan requested")


__all__ = ["router", "get_admin_files_service"]
```

`app/tests/test_admin_files_routes.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_files import router as admin_router, get_admin_files_service
from fileflash.schemas.admin.files import RescanResponse


class StubService:
    async def list_files(self, *, query):  # noqa: ANN001
        return SimpleNamespace(model_dump=lambda **_: {
            "items": [],
            "pagination": {
                "totalItems": 0, "totalPages": 1,
                "perPage": query.per_page, "currentPage": query.page,
                "hasPrev": False, "hasNext": False,
            },
        })

    async def request_rescan(self, *, file_id, requested_by):  # noqa: ANN001
        return RescanResponse(
            file_id=str(file_id), virus_status="pending",
            scanned_at=datetime.now(UTC),
        )


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_files_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=99)
    return TestClient(app)


def test_list_files_returns_empty() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/files")
    assert resp.status_code == 200


def test_rescan_returns_pending() -> None:
    with _client() as c:
        resp = c.post("/api/v1/admin/files/7/rescan")
    assert resp.status_code == 200
    assert resp.json()["data"]["virusStatus"] == "pending"
```

- [ ] **Step 4.8: 跑测试 + 注册 router + commit**

Run: `cd app && uv run pytest tests/test_admin_files_routes.py -v`
Expected: 2 passed

Modify `app/src/fileflash/routers/__init__.py` 加入 `admin_files_router` 的 import 和 include。

```bash
git add app/src/fileflash/schemas/admin/files.py app/src/fileflash/services/admin/files.py app/src/fileflash/routers/admin_files.py app/src/fileflash/routers/__init__.py app/tests/test_admin_files_*.py
git commit -m "feat(admin): /admin/files list + /admin/files/{id}/rescan with event"
```

---

## Task 5: Admin Moderation（violations list + resolve）

**Files:**
- Create: `app/src/fileflash/schemas/admin/moderation.py`
- Create: `app/src/fileflash/services/admin/moderation.py`
- Create: `app/src/fileflash/routers/admin_moderation.py`
- Test: `app/tests/test_admin_moderation_service.py`, `app/tests/test_admin_moderation_routes.py`

- [ ] **Step 5.1: 写 schemas**

`app/src/fileflash/schemas/admin/moderation.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..common import CamelModel, PageQuery


ViolationLevel = Literal["low", "medium", "high"]
ViolationStatus = Literal["pending", "under_review", "resolved"]


class ViolationItem(CamelModel):
    id: str
    file_id: str | None
    file_name: str | None
    type: str
    level: ViolationLevel
    reported_at: datetime
    status: ViolationStatus


class ListViolationsQuery(PageQuery):
    status: ViolationStatus | None = None


class ResolveViolationResponse(CamelModel):
    violation_id: str
    resolved_at: datetime


__all__ = [
    "ListViolationsQuery",
    "ResolveViolationResponse",
    "ViolationItem",
    "ViolationLevel",
    "ViolationStatus",
]
```

- [ ] **Step 5.2: 写失败测试**

`app/tests/test_admin_moderation_service.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.schemas.admin.moderation import ListViolationsQuery
from fileflash.services.admin.moderation import AdminModerationService


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_resolve_missing_case_returns_404() -> None:
    session = DummySession()
    session.get.return_value = None
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.resolve_case(case_id=1, handled_by=2)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_already_resolved_returns_409() -> None:
    session = DummySession()
    case = Mock(case_id=1, status="resolved")
    session.get.return_value = case
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.resolve_case(case_id=1, handled_by=2)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_resolve_pending_case_sets_resolved() -> None:
    session = DummySession()
    case = Mock(case_id=1, status="pending", handled_by=None, handled_at=None,
                resolution=None, file_id=10)
    session.get.return_value = case
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    result = await service.resolve_case(case_id=1, handled_by=2)

    assert result.violation_id == "1"
    assert case.status == "resolved"
    assert case.resolution == "admin_clear"
    assert case.handled_by == 2
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_list_returns_empty_paginated() -> None:
    session = DummySession()
    session.scalar.return_value = 0
    session.execute.return_value = Mock(all=lambda: [])
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    result = await service.list_violations(query=ListViolationsQuery())
    assert result.items == []
    assert result.pagination.total_items == 0
```

- [ ] **Step 5.3: 实现 service**

`app/src/fileflash/services/admin/moderation.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.tables_audit_security import ModerationCase
from ...models.tables_storage import File
from ...schemas.admin.moderation import (
    ListViolationsQuery,
    ResolveViolationResponse,
    ViolationItem,
    ViolationLevel,
)
from ...schemas.common import PaginatedData, PaginationMeta

_OPEN_STATES = ("pending", "under_review")


class AdminModerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_violations(
        self,
        *,
        query: ListViolationsQuery,
    ) -> PaginatedData[ViolationItem]:
        statement = (
            select(ModerationCase, File)
            .join(File, File.file_id == ModerationCase.file_id, isouter=True)
        )
        if query.status:
            statement = statement.where(ModerationCase.status == query.status)
        statement = statement.order_by(ModerationCase.created_at.desc())

        total = int(
            await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = (await self.db.execute(statement.offset(offset).limit(query.per_page))).all()

        items = [self._to_item(case, file_) for case, file_ in rows]
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def resolve_case(self, *, case_id: int, handled_by: int) -> ResolveViolationResponse:
        case = await self.db.get(ModerationCase, case_id, with_for_update=True)
        if case is None:
            raise ApiError(status_code=404, code=404, message="Violation case not found")
        if case.status not in _OPEN_STATES:
            raise ApiError(status_code=409, code=409, message="Case already resolved")

        now = datetime.now(UTC)
        case.status = "resolved"
        case.resolution = "admin_clear"
        case.handled_by = handled_by
        case.handled_at = now
        case.updated_at = now
        await self.db.commit()

        return ResolveViolationResponse(violation_id=str(case_id), resolved_at=now)

    @staticmethod
    def _to_item(case: ModerationCase, file_: File | None) -> ViolationItem:
        return ViolationItem(
            id=str(case.case_id),
            file_id=str(case.file_id) if case.file_id else None,
            file_name=file_.name if file_ else None,
            type=case.reason_type,
            level=_level_from_confidence(case.confidence),
            reported_at=case.created_at,
            status=case.status,  # type: ignore[arg-type]
        )


def _level_from_confidence(confidence: Decimal | None) -> ViolationLevel:
    if confidence is None:
        return "low"
    value = float(confidence)
    if value > 0.8:
        return "high"
    if value > 0.5:
        return "medium"
    return "low"


__all__ = ["AdminModerationService"]
```

- [ ] **Step 5.4: 跑 service 测试**

Run: `cd app && uv run pytest tests/test_admin_moderation_service.py -v`
Expected: 4 passed

- [ ] **Step 5.5: 实现 router + 测试**

`app/src/fileflash/routers/admin_moderation.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import require_admin
from ..core.errors import api_success
from ..db.deps import get_db
from ..models.tables_identity import User
from ..schemas.admin.moderation import ListViolationsQuery
from ..services.admin.moderation import AdminModerationService

router = APIRouter(prefix="/admin/violations", tags=["admin"])


def get_admin_moderation_service(
    db: AsyncSession = Depends(get_db),
) -> AdminModerationService:
    return AdminModerationService(db=db)


@router.get("")
async def list_violations(
    query: ListViolationsQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminModerationService = Depends(get_admin_moderation_service),
):
    data = await service.list_violations(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Violations fetched")


@router.post("/{case_id}/resolve")
async def resolve_violation(
    case_id: int,
    admin: User = Depends(require_admin),
    service: AdminModerationService = Depends(get_admin_moderation_service),
):
    result = await service.resolve_case(case_id=case_id, handled_by=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Violation resolved")


__all__ = ["router", "get_admin_moderation_service"]
```

`app/tests/test_admin_moderation_routes.py`（参照 §2.1 模式，2 测例：list 通过 / resolve 通过）：

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_moderation import (
    router as mod_router,
    get_admin_moderation_service,
)
from fileflash.schemas.admin.moderation import ResolveViolationResponse


class StubService:
    async def list_violations(self, *, query):  # noqa: ANN001
        return SimpleNamespace(model_dump=lambda **_: {
            "items": [],
            "pagination": {
                "totalItems": 0, "totalPages": 1,
                "perPage": query.per_page, "currentPage": query.page,
                "hasPrev": False, "hasNext": False,
            },
        })

    async def resolve_case(self, *, case_id, handled_by):  # noqa: ANN001
        return ResolveViolationResponse(violation_id=str(case_id), resolved_at=datetime.now(UTC))


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(mod_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_moderation_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_list_violations() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/violations")
    assert resp.status_code == 200


def test_resolve_violation() -> None:
    with _client() as c:
        resp = c.post("/api/v1/admin/violations/3/resolve")
    assert resp.status_code == 200
    assert resp.json()["data"]["violationId"] == "3"
```

- [ ] **Step 5.6: 跑测试 + 注册 + commit**

Run: `cd app && uv run pytest tests/test_admin_moderation_routes.py -v`

Modify `routers/__init__.py` 加入 `admin_moderation_router` import + include。

```bash
git add app/src/fileflash/schemas/admin/moderation.py app/src/fileflash/services/admin/moderation.py app/src/fileflash/routers/admin_moderation.py app/src/fileflash/routers/__init__.py app/tests/test_admin_moderation_*.py
git commit -m "feat(admin): /admin/violations list + resolve via ModerationCase"
```

---

## Task 6: Admin Logs

**Files:**
- Create: `app/src/fileflash/schemas/admin/logs.py`
- Create: `app/src/fileflash/services/admin/logs.py`
- Create: `app/src/fileflash/routers/admin_logs.py`
- Test: `app/tests/test_admin_logs_routes.py`

- [ ] **Step 6.1: schemas**

`app/src/fileflash/schemas/admin/logs.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from ..common import CamelModel, PageQuery


class LogItem(CamelModel):
    id: str
    user_id: str | None
    operation: str
    operation_name: str
    target_type: str | None
    target_id: str | None
    result: str
    ip_address: str | None
    user_agent: str | None
    performed_at: datetime
    details: str | None = None
    metadata: dict[str, Any] = {}


class ListAdminLogsQuery(PageQuery):
    user_id: str | None = None
    operation: str | None = None
    result: Literal["success", "failure"] | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None


class AdminLogsResponse(CamelModel):
    logs: list[LogItem]
    pagination: dict[str, Any]


__all__ = ["AdminLogsResponse", "ListAdminLogsQuery", "LogItem"]
```

- [ ] **Step 6.2: 实现 service（轻量；只 list）**

`app/src/fileflash/services/admin/logs.py`：

```python
from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.tables_audit_security import Log
from ...schemas.admin.logs import AdminLogsResponse, ListAdminLogsQuery, LogItem


class AdminLogsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_logs(self, *, query: ListAdminLogsQuery) -> AdminLogsResponse:
        statement = select(Log)
        conditions = []
        if query.user_id:
            conditions.append(Log.user_id == int(query.user_id))
        if query.operation:
            conditions.append(Log.operation == query.operation)
        if query.result:
            conditions.append(Log.result == query.result)
        if query.from_at:
            conditions.append(Log.performed_at >= query.from_at)
        if query.to_at:
            conditions.append(Log.performed_at <= query.to_at)
        if conditions:
            statement = statement.where(and_(*conditions))
        statement = statement.order_by(Log.performed_at.desc())

        total = int(
            await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))

        logs = [
            LogItem(
                id=str(row.id),
                user_id=str(row.user_id) if row.user_id else None,
                operation=row.operation,
                operation_name=row.operation,
                target_type=row.target_type,
                target_id=str(row.target_id) if row.target_id else None,
                result=row.result,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                performed_at=row.performed_at,
                details=row.details,
                metadata=row.metadata_payload or {},
            )
            for row in rows
        ]

        return AdminLogsResponse(
            logs=logs,
            pagination={
                "totalItems": total,
                "totalPages": total_pages,
                "perPage": query.per_page,
                "currentPage": query.page,
                "hasPrev": query.page > 1,
                "hasNext": query.page < total_pages,
            },
        )


__all__ = ["AdminLogsService"]
```

- [ ] **Step 6.3: 实现 router**

`app/src/fileflash/routers/admin_logs.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import require_admin
from ..core.errors import api_success
from ..db.deps import get_db
from ..models.tables_identity import User
from ..schemas.admin.logs import ListAdminLogsQuery
from ..services.admin.logs import AdminLogsService

router = APIRouter(prefix="/admin/logs", tags=["admin"])


def get_admin_logs_service(db: AsyncSession = Depends(get_db)) -> AdminLogsService:
    return AdminLogsService(db=db)


@router.get("")
async def list_admin_logs(
    query: ListAdminLogsQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminLogsService = Depends(get_admin_logs_service),
):
    data = await service.list_logs(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Logs fetched")


__all__ = ["router", "get_admin_logs_service"]
```

- [ ] **Step 6.4: 测试**

`app/tests/test_admin_logs_routes.py`：

```python
from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_logs import router as logs_router, get_admin_logs_service
from fileflash.schemas.admin.logs import AdminLogsResponse


class StubService:
    async def list_logs(self, *, query):  # noqa: ANN001
        return AdminLogsResponse(
            logs=[],
            pagination={
                "totalItems": 0, "totalPages": 1,
                "perPage": query.per_page, "currentPage": query.page,
                "hasPrev": False, "hasNext": False,
            },
        )


def test_admin_can_list_logs() -> None:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(logs_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_logs_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    with TestClient(app) as c:
        resp = c.get("/api/v1/admin/logs")
    assert resp.status_code == 200
    assert resp.json()["data"]["logs"] == []
```

- [ ] **Step 6.5: 跑测试 + 注册 + commit**

Run: `cd app && uv run pytest tests/test_admin_logs_routes.py -v`

Modify `routers/__init__.py` 加入 `admin_logs_router` import + include。

```bash
git add app/src/fileflash/schemas/admin/logs.py app/src/fileflash/services/admin/logs.py app/src/fileflash/routers/admin_logs.py app/src/fileflash/routers/__init__.py app/tests/test_admin_logs_routes.py
git commit -m "feat(admin): /admin/logs list with filters"
```

---

## Task 7: Admin Notifications（list / broadcast / read / archive）

**Files:**
- Create: `app/src/fileflash/schemas/admin/notifications.py`
- Create: `app/src/fileflash/services/admin/notifications.py`
- Create: `app/src/fileflash/routers/admin_notifications.py`
- Test: `app/tests/test_admin_notifications_service.py`, `app/tests/test_admin_notifications_routes.py`

- [ ] **Step 7.1: schemas**

`app/src/fileflash/schemas/admin/notifications.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from ..common import CamelModel, PageQuery


class AdminNotificationItem(CamelModel):
    id: str
    message: str
    title: str | None
    type: str
    status: str
    is_read: bool
    created_at: datetime
    updated_at: datetime
    recipient_count: int | None = None


class ListAdminNotificationsQuery(PageQuery):
    status: str | None = None
    type: str | None = None


class BroadcastRequest(CamelModel):
    title: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=1, max_length=2000)
    type: Literal["system", "announcement"] = "system"


class BroadcastResponse(CamelModel):
    broadcast_id: str
    recipient_count: int
    sent_at: datetime


__all__ = [
    "AdminNotificationItem",
    "BroadcastRequest",
    "BroadcastResponse",
    "ListAdminNotificationsQuery",
]
```

- [ ] **Step 7.2: 写失败测试**

`app/tests/test_admin_notifications_service.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.schemas.admin.notifications import BroadcastRequest
from fileflash.services.admin.notifications import (
    AdminNotificationsService,
    MAX_BROADCAST_RECIPIENTS,
)


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.add_all = Mock()
        self.commit = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_broadcast_rejects_empty_message() -> None:
    # Pydantic 会先拦截；这里测 service 层显式拒绝（防御）
    session = DummySession()
    service = AdminNotificationsService(db=session)  # type: ignore[arg-type]
    with pytest.raises(ApiError):
        await service.broadcast(
            payload=BroadcastRequest.model_construct(title=None, message="", type="system"),
            sender_id=1,
        )


@pytest.mark.asyncio
async def test_broadcast_too_many_recipients_returns_422() -> None:
    session = DummySession()
    session.scalar.return_value = MAX_BROADCAST_RECIPIENTS + 1
    service = AdminNotificationsService(db=session)  # type: ignore[arg-type]
    with pytest.raises(ApiError) as exc:
        await service.broadcast(
            payload=BroadcastRequest(message="hi", type="system"),
            sender_id=1,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_broadcast_writes_one_row_per_recipient() -> None:
    session = DummySession()
    session.scalar.return_value = 3
    session.scalars.return_value = iter([10, 11, 12])
    service = AdminNotificationsService(db=session)  # type: ignore[arg-type]

    result = await service.broadcast(
        payload=BroadcastRequest(message="ping", type="system"),
        sender_id=1,
    )

    assert result.recipient_count == 3
    assert session.add_all.called
```

- [ ] **Step 7.3: 实现 service**

`app/src/fileflash/services/admin/notifications.py`：

```python
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import UserStatus
from ...models.tables_audit_security import Notification
from ...models.tables_identity import User
from ...schemas.admin.notifications import (
    AdminNotificationItem,
    BroadcastRequest,
    BroadcastResponse,
    ListAdminNotificationsQuery,
)
from ...schemas.common import PaginatedData, PaginationMeta

MAX_BROADCAST_RECIPIENTS = 50_000
_CHUNK_SIZE = 500


class AdminNotificationsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_notifications(
        self,
        *,
        query: ListAdminNotificationsQuery,
    ) -> PaginatedData[AdminNotificationItem]:
        statement = select(Notification)
        if query.status:
            statement = statement.where(Notification.status == query.status)
        if query.type:
            statement = statement.where(Notification.notification_type == query.type)
        statement = statement.order_by(Notification.created_at.desc())

        total = int(
            await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))

        items = [self._to_item(row) for row in rows]
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def broadcast(
        self,
        *,
        payload: BroadcastRequest,
        sender_id: int,
    ) -> BroadcastResponse:
        message = (payload.message or "").strip()
        if not message:
            raise ApiError(status_code=422, code=422, message="Broadcast message cannot be empty")

        recipient_count = int(
            await self.db.scalar(
                select(func.count(User.user_id)).where(
                    User.status == UserStatus.ACTIVE,
                    User.deleted_at.is_(None),
                )
            ) or 0
        )
        if recipient_count > MAX_BROADCAST_RECIPIENTS:
            raise ApiError(
                status_code=422,
                code=422,
                message=f"Recipient count {recipient_count} exceeds limit {MAX_BROADCAST_RECIPIENTS}",
            )

        broadcast_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        delivered = 0

        async for chunk in self._iter_active_user_ids():
            rows = [
                Notification(
                    user_id=uid,
                    title=payload.title,
                    notification_type=payload.type,
                    channel="in_app",
                    message=message,
                    payload={"broadcastId": broadcast_id},
                    sender_user_id=sender_id,
                    status="sent",
                    sent_at=now,
                    is_read=False,
                    created_at=now,
                    updated_at=now,
                )
                for uid in chunk
            ]
            if rows:
                self.db.add_all(rows)
                await self.db.commit()
                delivered += len(rows)

        return BroadcastResponse(
            broadcast_id=broadcast_id,
            recipient_count=delivered,
            sent_at=now,
        )

    async def _iter_active_user_ids(self) -> AsyncIterator[list[int]]:
        stream = await self.db.scalars(
            select(User.user_id).where(
                User.status == UserStatus.ACTIVE,
                User.deleted_at.is_(None),
            )
        )
        buffer: list[int] = []
        for user_id in stream:
            buffer.append(user_id)
            if len(buffer) >= _CHUNK_SIZE:
                yield buffer
                buffer = []
        if buffer:
            yield buffer

    async def archive(self, *, notification_id: int) -> None:
        row = await self.db.get(Notification, notification_id)
        if row is None:
            raise ApiError(status_code=404, code=404, message="Notification not found")
        row.status = "archived"
        row.updated_at = datetime.now(UTC)
        await self.db.commit()

    @staticmethod
    def _to_item(row: Notification) -> AdminNotificationItem:
        broadcast_id = (row.payload or {}).get("broadcastId") if row.payload else None
        return AdminNotificationItem(
            id=str(row.id),
            message=row.message,
            title=row.title,
            type=row.notification_type,
            status=row.status,
            is_read=bool(row.is_read),
            created_at=row.created_at or datetime.now(UTC),
            updated_at=row.updated_at,
            recipient_count=None if broadcast_id is None else None,
        )


__all__ = ["AdminNotificationsService", "MAX_BROADCAST_RECIPIENTS"]
```

- [ ] **Step 7.4: 跑测试**

Run: `cd app && uv run pytest tests/test_admin_notifications_service.py -v`
Expected: 3 passed

- [ ] **Step 7.5: 实现 router + 路由测试**

`app/src/fileflash/routers/admin_notifications.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import require_admin
from ..core.errors import api_success
from ..db.deps import get_db
from ..models.tables_identity import User
from ..schemas.admin.notifications import (
    BroadcastRequest,
    ListAdminNotificationsQuery,
)
from ..services.admin.notifications import AdminNotificationsService

router = APIRouter(prefix="/admin/notifications", tags=["admin"])


def get_admin_notifications_service(
    db: AsyncSession = Depends(get_db),
) -> AdminNotificationsService:
    return AdminNotificationsService(db=db)


@router.get("")
async def list_admin_notifications(
    query: ListAdminNotificationsQuery = Depends(),
    _: User = Depends(require_admin),
    service: AdminNotificationsService = Depends(get_admin_notifications_service),
):
    data = await service.list_notifications(query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Notifications fetched")


@router.post("/broadcast")
async def broadcast_notification(
    payload: BroadcastRequest,
    admin: User = Depends(require_admin),
    service: AdminNotificationsService = Depends(get_admin_notifications_service),
):
    result = await service.broadcast(payload=payload, sender_id=admin.user_id)
    return api_success(data=result.model_dump(by_alias=True), message="Broadcast sent")


@router.delete("/{notification_id}")
async def archive_admin_notification(
    notification_id: int,
    _: User = Depends(require_admin),
    service: AdminNotificationsService = Depends(get_admin_notifications_service),
):
    await service.archive(notification_id=notification_id)
    return api_success(
        data={"notificationId": str(notification_id), "status": "archived"},
        message="Notification archived",
    )


__all__ = ["router", "get_admin_notifications_service"]
```

`app/tests/test_admin_notifications_routes.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_notifications import (
    router as n_router,
    get_admin_notifications_service,
)
from fileflash.schemas.admin.notifications import BroadcastResponse


class StubService:
    async def list_notifications(self, *, query):  # noqa: ANN001
        return SimpleNamespace(model_dump=lambda **_: {
            "items": [],
            "pagination": {
                "totalItems": 0, "totalPages": 1,
                "perPage": query.per_page, "currentPage": query.page,
                "hasPrev": False, "hasNext": False,
            },
        })

    async def broadcast(self, *, payload, sender_id):  # noqa: ANN001
        return BroadcastResponse(
            broadcast_id="b1", recipient_count=2, sent_at=datetime.now(UTC),
        )

    async def archive(self, *, notification_id):  # noqa: ANN001
        return None


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(n_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_notifications_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_list() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/notifications")
    assert resp.status_code == 200


def test_broadcast() -> None:
    with _client() as c:
        resp = c.post("/api/v1/admin/notifications/broadcast",
                      json={"message": "hello", "type": "system"})
    assert resp.status_code == 200
    assert resp.json()["data"]["broadcastId"] == "b1"


def test_archive() -> None:
    with _client() as c:
        resp = c.delete("/api/v1/admin/notifications/9")
    assert resp.status_code == 200
```

- [ ] **Step 7.6: 跑测试 + 注册 + commit**

```bash
cd app && uv run pytest tests/test_admin_notifications_routes.py -v
```

Modify `routers/__init__.py` 加 `admin_notifications_router` import + include。

```bash
git add app/src/fileflash/schemas/admin/notifications.py app/src/fileflash/services/admin/notifications.py app/src/fileflash/routers/admin_notifications.py app/src/fileflash/routers/__init__.py app/tests/test_admin_notifications_*.py
git commit -m "feat(admin): /admin/notifications list, broadcast, archive"
```

---

## Task 8: Admin System（health + rate-limit）

**Files:**
- Create: `app/src/fileflash/schemas/admin/system.py`
- Create: `app/src/fileflash/services/admin/system.py`
- Create: `app/src/fileflash/routers/admin_system.py`
- Test: `app/tests/test_admin_system_routes.py`

- [ ] **Step 8.1: schemas**

`app/src/fileflash/schemas/admin/system.py`：

```python
from __future__ import annotations

from datetime import datetime

from ..common import CamelModel


class SystemHealth(CamelModel):
    platform_targets: list[str]
    max_concurrent_uploads: int
    active_upload_sessions: int
    virus_scan_enabled: bool
    thumbnail_generation_enabled: bool
    registration_mail_enabled: bool
    hash_computation_enabled: bool
    last_updated_at: datetime


class RateLimitRule(CamelModel):
    rule_id: str
    scope: str
    window_seconds: int
    limit: int
    current_usage: int
    blocked_requests: int


class RateLimitStatus(CamelModel):
    rules: list[RateLimitRule]
    evaluated_at: datetime


__all__ = ["RateLimitRule", "RateLimitStatus", "SystemHealth"]
```

- [ ] **Step 8.2: 实现 service（轻量；health 来自 settings，rate-limit 静态枚举）**

`app/src/fileflash/services/admin/system.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.settings import Settings
from ...models.enums import UploadTaskStatus
from ...models.tables_storage import UploadTask
from ...schemas.admin.system import RateLimitRule, RateLimitStatus, SystemHealth

# 静态规则定义；如 auth router 有 N 个 RateLimiter.allow 调用，把它们对应的 scope 列在这。
_RATE_LIMIT_RULES = [
    {"rule_id": "login", "scope": "auth.login", "window_seconds": 60, "limit": 5},
    {"rule_id": "register", "scope": "auth.register", "window_seconds": 600, "limit": 3},
    {"rule_id": "forgot_password", "scope": "auth.forgot_password", "window_seconds": 600, "limit": 3},
    {"rule_id": "resend_verification", "scope": "auth.resend_verification", "window_seconds": 600, "limit": 3},
]


class AdminSystemService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def health(self) -> SystemHealth:
        active_uploads = int(
            await self.db.scalar(
                select(func.count(UploadTask.task_id)).where(
                    UploadTask.status.in_([UploadTaskStatus.INIT, UploadTaskStatus.UPLOADING])
                )
            ) or 0
        )

        platform_targets: list[str] = []
        if self.settings.object_storage_bucket:
            platform_targets.append(f"s3://{self.settings.object_storage_bucket}")
        if self.settings.redis_url:
            platform_targets.append("redis")

        return SystemHealth(
            platform_targets=platform_targets,
            max_concurrent_uploads=getattr(self.settings, "max_concurrent_uploads", 4),
            active_upload_sessions=active_uploads,
            virus_scan_enabled=bool(getattr(self.settings, "virus_scan_enabled", False)),
            thumbnail_generation_enabled=bool(getattr(self.settings, "thumbnail_generation_enabled", True)),
            registration_mail_enabled=bool(self.settings.mail_server and self.settings.mail_from),
            hash_computation_enabled=True,
            last_updated_at=datetime.now(UTC),
        )

    async def rate_limit_status(self) -> RateLimitStatus:
        rules = [
            RateLimitRule(
                rule_id=rule["rule_id"],
                scope=rule["scope"],
                window_seconds=rule["window_seconds"],
                limit=rule["limit"],
                current_usage=0,  # 不扫 Redis；运行时统计后续扩展
                blocked_requests=0,
            )
            for rule in _RATE_LIMIT_RULES
        ]
        return RateLimitStatus(rules=rules, evaluated_at=datetime.now(UTC))


__all__ = ["AdminSystemService"]
```

- [ ] **Step 8.3: 实现 router**

`app/src/fileflash/routers/admin_system.py`：

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_settings_dep, require_admin
from ..core.errors import api_success
from ..core.settings import Settings
from ..db.deps import get_db
from ..models.tables_identity import User
from ..services.admin.system import AdminSystemService

router = APIRouter(prefix="/admin/system", tags=["admin"])


def get_admin_system_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> AdminSystemService:
    return AdminSystemService(db=db, settings=settings)


@router.get("/health")
async def get_system_health(
    _: User = Depends(require_admin),
    service: AdminSystemService = Depends(get_admin_system_service),
):
    data = await service.health()
    return api_success(data=data.model_dump(by_alias=True), message="System health fetched")


@router.get("/rate-limit")
async def get_rate_limit_status(
    _: User = Depends(require_admin),
    service: AdminSystemService = Depends(get_admin_system_service),
):
    data = await service.rate_limit_status()
    return api_success(data=data.model_dump(by_alias=True), message="Rate limit fetched")


__all__ = ["router", "get_admin_system_service"]
```

- [ ] **Step 8.4: 测试**

`app/tests/test_admin_system_routes.py`：

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_system import router as sys_router, get_admin_system_service
from fileflash.schemas.admin.system import (
    RateLimitRule, RateLimitStatus, SystemHealth,
)


class StubService:
    async def health(self):
        return SystemHealth(
            platform_targets=["s3://bkt"], max_concurrent_uploads=4,
            active_upload_sessions=0, virus_scan_enabled=False,
            thumbnail_generation_enabled=True, registration_mail_enabled=False,
            hash_computation_enabled=True, last_updated_at=datetime.now(UTC),
        )

    async def rate_limit_status(self):
        return RateLimitStatus(
            rules=[
                RateLimitRule(
                    rule_id="login", scope="auth.login",
                    window_seconds=60, limit=5, current_usage=0, blocked_requests=0,
                )
            ],
            evaluated_at=datetime.now(UTC),
        )


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(sys_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_system_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_health() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/system/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["activeUploadSessions"] == 0


def test_rate_limit() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/system/rate-limit")
    assert resp.status_code == 200
    assert resp.json()["data"]["rules"][0]["scope"] == "auth.login"
```

- [ ] **Step 8.5: 跑测试 + 注册 + commit**

```bash
cd app && uv run pytest tests/test_admin_system_routes.py -v
```

Modify `routers/__init__.py` 加入 `admin_system_router` import + include。

```bash
git add app/src/fileflash/schemas/admin/system.py app/src/fileflash/services/admin/system.py app/src/fileflash/routers/admin_system.py app/src/fileflash/routers/__init__.py app/tests/test_admin_system_routes.py
git commit -m "feat(admin): /admin/system health and rate-limit"
```

---

## Task 9: 端到端冒烟 + 全量回归

- [ ] **Step 9.1: 全量启动冒烟**

Run: `cd app && uv run python -c "from fileflash.main import app; print(sorted(r.path for r in app.routes if '/admin/' in r.path))"`
Expected: prints 14+ paths including `/api/v1/admin/users`, `/api/v1/admin/storage/summary`, `/api/v1/admin/files`, `/api/v1/admin/violations`, `/api/v1/admin/logs`, `/api/v1/admin/notifications`, `/api/v1/admin/system/health` 等。

- [ ] **Step 9.2: 跑全量 admin 测试**

Run: `cd app && uv run pytest tests/test_admin_ -v`
Expected: 所有 admin_* 测试通过（含 Task 0-8 累计 ≥ 25 个测例）。

- [ ] **Step 9.3: 跑全量回归**

Run: `cd app && uv run pytest -q`
Expected: 不引入新 failure；现有测试全绿。

- [ ] **Step 9.4: 编写 changelog / README 摘要（可选）**

如果项目维护 README/CHANGELOG，添加一段：

> 新增 Admin Console 后端 API（/admin/users, /admin/storage/*, /admin/files, /admin/violations, /admin/logs, /admin/notifications, /admin/system/*）。前端请参照 Plan B 完成 Console 重构。

如果项目无此惯例，跳过本步。

- [ ] **Step 9.5: Commit final**

```bash
git status
# 若 Step 9.4 有改动则提交：
# git add README.md && git commit -m "docs: note admin console API surface"
```

---

## Plan A 完工标准

- 所有 `/admin/*` 路由：`/users`, `/storage/*`, `/files*`, `/violations*`, `/logs`, `/notifications*`, `/system/*` 可经过真实 DB 工作，鉴权由 `require_admin` 控制。
- 14+ 新增测例全部通过。
- 全量 `uv run pytest -q` 仍绿。
- 现有 `/admin/registration-email-domain-rules` 零改动、零回归。
- 前端在 mock 关闭、指向真实后端时（设 `VITE_USE_MOCK=false`），Console 各页（Plan B 完成后）可正常工作。
