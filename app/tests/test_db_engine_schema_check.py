from __future__ import annotations

from typing import Any

import pytest

from fileflash.db import engine as engine_module


class _DummyResult:
    def __init__(self, value: int | None) -> None:
        self._value = value

    def scalar(self) -> int | None:
        return self._value


class _DummyConnection:
    def __init__(self, results: list[int | None]) -> None:
        self._results = list(results)

    async def execute(self, *_args: Any, **_kwargs: Any) -> _DummyResult:
        if not self._results:
            return _DummyResult(None)
        return _DummyResult(self._results.pop(0))


class _DummyConnectContext:
    def __init__(self, connection: _DummyConnection) -> None:
        self._connection = connection

    async def __aenter__(self) -> _DummyConnection:
        return self._connection

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        return False


class _DummyEngine:
    def __init__(self, results: list[int | None]) -> None:
        self._results = results

    def connect(self) -> _DummyConnectContext:
        return _DummyConnectContext(_DummyConnection(self._results))


@pytest.mark.asyncio
async def test_verify_schema_compatibility_fails_when_domain_rule_table_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_module, "engine", _DummyEngine([1, None]))

    with pytest.raises(RuntimeError, match="registration_email_domain_rule"):
        await engine_module.verify_schema_compatibility()
