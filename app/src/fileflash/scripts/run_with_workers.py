from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from redis import Redis

from ..core.settings import get_settings


@dataclass(slots=True)
class ManagedProcess:
    name: str
    process: subprocess.Popen[bytes]
    command: list[str]


def _build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    default_worker_count = max(1, settings.worker_process_count)
    parser = argparse.ArgumentParser(
        description="Run FileFlash backend API with worker processes.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="API host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="API port (default: 8080)")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload for API process.",
    )
    parser.add_argument(
        "--worker-count",
        type=int,
        default=default_worker_count,
        help=(
            "Number of file worker consumer processes "
            f"(default from WORKER_PROCESS_COUNT: {default_worker_count})."
        ),
    )
    parser.add_argument(
        "--no-worker",
        action="store_true",
        help="Start API only (without file workers).",
    )
    return parser


def _spawn_process(name: str, command: list[str], cwd: Path) -> ManagedProcess:
    popen_kwargs: dict[str, object] = {"cwd": str(cwd)}
    if sys.platform == "win32":
        # Needed so CTRL_BREAK_EVENT can be delivered to child process group.
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        command,
        **popen_kwargs,
    )
    return ManagedProcess(name=name, process=proc, command=command)


def _format_cmd(command: list[str]) -> str:
    return " ".join(command)


def _stop_process(managed: ManagedProcess, *, timeout_sec: float = 8.0) -> None:
    proc = managed.process
    if proc.poll() is not None:
        return

    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=timeout_sec)
        return
    except Exception:
        pass

    try:
        proc.kill()
        proc.wait(timeout=timeout_sec)
    except Exception:
        pass


def _validate_redis_for_workers(env: Mapping[str, str] | None = None) -> tuple[bool, str]:
    redis_url = (env or {}).get("REDIS_URL", "").strip()
    if not redis_url:
        settings = get_settings()
        redis_url = (settings.redis_url or "").strip()
    if not redis_url.strip():
        return (
            False,
            "[run-with-workers] worker startup preflight failed: REDIS_URL is not set.",
        )

    client: Redis | None = None
    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=2.0, socket_timeout=2.0)
        client.ping()
    except Exception as exc:
        return (
            False,
            (
                "[run-with-workers] worker startup preflight failed: "
                f"cannot connect to Redis at {redis_url}. error={type(exc).__name__}: {exc}"
            ),
        )
    finally:
        try:
            client.close()
        except Exception:
            pass

    return True, ""


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.worker_count < 1:
        parser.error("--worker-count must be >= 1")

    cwd = Path(__file__).resolve().parents[2]
    python = sys.executable

    processes: list[ManagedProcess] = []
    try:
        if not args.no_worker:
            ok, error_message = _validate_redis_for_workers()
            if not ok:
                print(error_message, file=sys.stderr)
                return 2

        api_cmd = [
            python,
            "-m",
            "uvicorn",
            "fileflash.main:app",
            "--host",
            str(args.host),
            "--port",
            str(args.port),
        ]
        if args.reload:
            api_cmd.append("--reload")

        api_proc = _spawn_process("api", api_cmd, cwd)
        processes.append(api_proc)
        print(f"[run-with-workers] started {api_proc.name}: {_format_cmd(api_cmd)}")

        if not args.no_worker:
            for index in range(args.worker_count):
                worker_name = f"worker-{index + 1}"
                worker_cmd = [python, "-m", "fileflash.workers.consumer"]
                worker_proc = _spawn_process(worker_name, worker_cmd, cwd)
                processes.append(worker_proc)
                print(f"[run-with-workers] started {worker_name}: {_format_cmd(worker_cmd)}")

        while True:
            for managed in processes:
                exit_code = managed.process.poll()
                if exit_code is not None:
                    print(
                        f"[run-with-workers] process exited: {managed.name} code={exit_code}",
                        file=sys.stderr,
                    )
                    return int(exit_code)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[run-with-workers] shutdown requested, stopping all processes...")
        return 0
    finally:
        for managed in reversed(processes):
            _stop_process(managed)
            code = managed.process.poll()
            print(f"[run-with-workers] stopped {managed.name} code={code}")


if __name__ == "__main__":
    raise SystemExit(main())
