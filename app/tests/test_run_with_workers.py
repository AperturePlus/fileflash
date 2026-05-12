from __future__ import annotations

from dataclasses import dataclass

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

    monkeypatch.setattr(run_with_workers, "_spawn_process", fake_spawn)
    monkeypatch.setattr(run_with_workers, "_stop_process", lambda *_args, **_kwargs: None)
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
