from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from fileflash.core.settings import Settings
from fileflash.models.enums import UserRole
from fileflash.models.tables_identity import User
from fileflash.services.dev_seed import DevAccountSeeder, DevSeedSummary, initialize_dev_accounts


class DummySeedSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self._user_seq = 100

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if isinstance(obj, User) and obj.user_id is None:
                self._user_seq += 1
                obj.user_id = self._user_seq

    async def commit(self) -> None:
        self.commits += 1


class MemoryDevAccountSeeder(DevAccountSeeder):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.preferences: set[int] = set()
        self.roots: set[int] = set()

    async def _find_existing_user(self, *, spec):  # type: ignore[override]
        for obj in self.db.added:
            if not isinstance(obj, User):
                continue
            if (
                obj.username.lower() == spec.username.lower()
                or obj.email.lower() == spec.email.lower()
            ):
                return obj
        return None

    async def _ensure_preference(self, *, user, language, now, summary):  # type: ignore[override]
        if int(user.user_id) not in self.preferences:
            self.preferences.add(int(user.user_id))
            summary.created_preferences += 1

    async def _ensure_root_folder(self, *, user, now, summary):  # type: ignore[override]
        if int(user.user_id) not in self.roots:
            self.roots.add(int(user.user_id))
            summary.created_roots += 1


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(_env_file=None, **payload)


@pytest.mark.asyncio
async def test_dev_account_seeder_is_idempotent_and_supports_password_reset():
    session = DummySeedSession()
    seeder = MemoryDevAccountSeeder(db=session)

    first = await seeder.seed(reset_password=False)
    assert first.created_users == 2
    assert first.updated_users == 0
    assert first.reset_password_users == 0
    assert first.created_preferences == 2
    assert first.created_roots == 2

    users = [obj for obj in session.added if isinstance(obj, User)]
    original_hashes = {user.username: user.password_hash for user in users}

    second = await seeder.seed(reset_password=False)
    assert second.created_users == 0
    assert second.updated_users == 2
    assert second.reset_password_users == 0
    assert second.created_preferences == 0
    assert second.created_roots == 0

    third = await seeder.seed(reset_password=True)
    assert third.created_users == 0
    assert third.updated_users == 2
    assert third.reset_password_users == 2

    refreshed_hashes = {user.username: user.password_hash for user in users}
    assert refreshed_hashes["admin"] != original_hashes["admin"]
    assert refreshed_hashes["demo"] != original_hashes["demo"]


@pytest.mark.asyncio
async def test_initialize_dev_accounts_skips_auto_run_outside_dev_and_prod(
    monkeypatch: pytest.MonkeyPatch,
):
    guard = AsyncMock(side_effect=AssertionError("SessionLocal should not be called"))
    monkeypatch.setattr("fileflash.services.dev_seed.SessionLocal", guard)

    result = await initialize_dev_accounts(
        settings=make_settings(APP_ENV="staging"),
        auto_run=True,
        reset_password=False,
    )

    assert result is False
    guard.assert_not_called()


@pytest.mark.asyncio
async def test_initialize_dev_accounts_uses_env_admin_in_production(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}

    class SessionLocalStub:
        calls = 0

        def __call__(self):
            self.calls += 1
            return self

        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return None

    class SeederStub:
        def __init__(self, *, db: object, accounts: tuple[object, ...]) -> None:
            captured["db"] = db
            captured["accounts"] = accounts

        async def seed(self, *, reset_password: bool = False) -> DevSeedSummary:
            captured["reset_password"] = reset_password
            return DevSeedSummary(created_users=1)

    session_local = SessionLocalStub()
    monkeypatch.setattr("fileflash.services.dev_seed.SessionLocal", session_local)
    monkeypatch.setattr("fileflash.services.dev_seed.DevAccountSeeder", SeederStub)

    result = await initialize_dev_accounts(
        settings=make_settings(
            APP_ENV="production",
            DEFAULT_ADMIN_USERNAME="root-admin",
            DEFAULT_ADMIN_EMAIL="root-admin@example.com",
            DEFAULT_ADMIN_PASSWORD="p" * 32,
        ),
        auto_run=True,
        reset_password=False,
    )

    assert result is True
    assert session_local.calls == 1
    accounts = captured["accounts"]
    assert isinstance(accounts, tuple)
    assert len(accounts) == 1
    account = accounts[0]
    assert account.username == "root-admin"
    assert account.email == "root-admin@example.com"
    assert account.password == "p" * 32
    assert account.role == UserRole.ADMIN
    assert captured["reset_password"] is False

