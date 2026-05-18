from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from fileflash.scripts import run_with_workers


@dataclass
class _FakeProcess:
    poll_result: int | None = None

    def poll(self):
        return self.poll_result

    def send_signal(self, *_args, **_kwargs):
        return None

    def wait(self, timeout=None):
        return None

    def terminate(self):
        return None

    def kill(self):
        return None


def test_run_with_workers_uses_fileflash_entrypoints(monkeypatch):
    started: list[tuple[str, list[str], object]] = []

    def fake_spawn(name: str, command: list[str], cwd):
        started.append((name, command, cwd))
        return run_with_workers.ManagedProcess(name=name, process=_FakeProcess(), command=command)

    def raise_keyboard_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        run_with_workers,
        "get_settings",
        lambda: SimpleNamespace(worker_process_count=1, redis_url="redis://localhost:6379/0"),
    )
    monkeypatch.setattr(run_with_workers, "_spawn_process", fake_spawn)
    monkeypatch.setattr(run_with_workers, "_stop_process", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_with_workers, "_validate_redis_for_workers", lambda _env=None: (True, ""))
    monkeypatch.setattr(run_with_workers.time, "sleep", raise_keyboard_interrupt)
    monkeypatch.setattr(run_with_workers.sys, "argv", ["run-with-workers"])

    exit_code = run_with_workers.main()

    assert exit_code == 0
    assert started[0][0] == "api"
    assert started[0][1][:4] == [run_with_workers.sys.executable, "-m", "uvicorn", "fileflash.main:app"]
    assert "--host" in started[0][1]
    assert "--port" in started[0][1]
    assert started[1][0] == "worker-1"
    assert started[1][1] == [run_with_workers.sys.executable, "-m", "fileflash.workers.consumer"]


def test_run_with_workers_default_worker_count_comes_from_settings(monkeypatch):
    started: list[tuple[str, list[str], object]] = []

    def fake_spawn(name: str, command: list[str], cwd):
        started.append((name, command, cwd))
        return run_with_workers.ManagedProcess(name=name, process=_FakeProcess(), command=command)

    def raise_keyboard_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        run_with_workers,
        "get_settings",
        lambda: SimpleNamespace(worker_process_count=2, redis_url="redis://localhost:6379/0"),
    )
    monkeypatch.setattr(run_with_workers, "_spawn_process", fake_spawn)
    monkeypatch.setattr(run_with_workers, "_stop_process", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_with_workers, "_validate_redis_for_workers", lambda _env=None: (True, ""))
    monkeypatch.setattr(run_with_workers.time, "sleep", raise_keyboard_interrupt)
    monkeypatch.setattr(run_with_workers.sys, "argv", ["run-with-workers"])

    exit_code = run_with_workers.main()

    assert exit_code == 0
    worker_names = [name for name, _command, _cwd in started if name.startswith("worker-")]
    assert worker_names == ["worker-1", "worker-2"]


def test_run_with_workers_cli_worker_count_overrides_settings(monkeypatch):
    started: list[tuple[str, list[str], object]] = []

    def fake_spawn(name: str, command: list[str], cwd):
        started.append((name, command, cwd))
        return run_with_workers.ManagedProcess(name=name, process=_FakeProcess(), command=command)

    def raise_keyboard_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        run_with_workers,
        "get_settings",
        lambda: SimpleNamespace(worker_process_count=3, redis_url="redis://localhost:6379/0"),
    )
    monkeypatch.setattr(run_with_workers, "_spawn_process", fake_spawn)
    monkeypatch.setattr(run_with_workers, "_stop_process", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_with_workers, "_validate_redis_for_workers", lambda _env=None: (True, ""))
    monkeypatch.setattr(run_with_workers.time, "sleep", raise_keyboard_interrupt)
    monkeypatch.setattr(run_with_workers.sys, "argv", ["run-with-workers", "--worker-count", "1"])

    exit_code = run_with_workers.main()

    assert exit_code == 0
    worker_names = [name for name, _command, _cwd in started if name.startswith("worker-")]
    assert worker_names == ["worker-1"]


def test_run_with_workers_fails_fast_when_redis_url_missing(monkeypatch, capsys):
    def fail_if_spawned(*_args, **_kwargs):
        raise AssertionError("should not spawn")

    monkeypatch.setattr(
        run_with_workers,
        "get_settings",
        lambda: SimpleNamespace(worker_process_count=1, redis_url=None),
    )
    monkeypatch.setattr(run_with_workers, "_spawn_process", fail_if_spawned)
    monkeypatch.setattr(run_with_workers.sys, "argv", ["run-with-workers"])

    exit_code = run_with_workers.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "REDIS_URL is not set" in captured.err


def test_run_with_workers_fails_fast_when_redis_ping_fails(monkeypatch, capsys):
    class _FailingRedisClient:
        def ping(self):
            raise RuntimeError("ping failed")

        def close(self):
            return None

    def fail_if_spawned(*_args, **_kwargs):
        raise AssertionError("should not spawn")

    monkeypatch.setattr(
        run_with_workers,
        "get_settings",
        lambda: SimpleNamespace(worker_process_count=1, redis_url="redis://localhost:6379/0"),
    )
    monkeypatch.setattr(run_with_workers, "_spawn_process", fail_if_spawned)
    monkeypatch.setattr(
        run_with_workers.Redis,
        "from_url",
        lambda *_args, **_kwargs: _FailingRedisClient(),
    )
    monkeypatch.setattr(run_with_workers.sys, "argv", ["run-with-workers"])

    exit_code = run_with_workers.main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "cannot connect to Redis" in captured.err
    assert "ping failed" in captured.err


def test_run_with_workers_no_worker_skips_redis_preflight(monkeypatch):
    started: list[tuple[str, list[str], object]] = []

    def fake_spawn(name: str, command: list[str], cwd):
        started.append((name, command, cwd))
        return run_with_workers.ManagedProcess(name=name, process=_FakeProcess(), command=command)

    def raise_keyboard_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("redis preflight should be skipped when --no-worker is set")

    monkeypatch.setattr(
        run_with_workers,
        "get_settings",
        lambda: SimpleNamespace(worker_process_count=2, redis_url=None),
    )
    monkeypatch.setattr(run_with_workers, "_spawn_process", fake_spawn)
    monkeypatch.setattr(run_with_workers, "_stop_process", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_with_workers, "_validate_redis_for_workers", fail_if_called)
    monkeypatch.setattr(run_with_workers.time, "sleep", raise_keyboard_interrupt)
    monkeypatch.setattr(run_with_workers.sys, "argv", ["run-with-workers", "--no-worker"])

    exit_code = run_with_workers.main()

    assert exit_code == 0
    assert [name for name, _command, _cwd in started] == ["api"]
