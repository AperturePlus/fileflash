#!/usr/bin/env python3
"""Apply docker/flyway/migrations/*.sql in order (Flyway-compatible history table).

Usage (from app/):
  uv run python scripts/flyway_migrate.py
  uv run python scripts/flyway_migrate.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[1]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from fileflash.core.settings import get_settings

HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS flyway_schema_history (
    installed_rank SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    description VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'SQL',
    script VARCHAR(1000) NOT NULL,
    checksum INTEGER NULL,
    installed_by VARCHAR(100) NOT NULL DEFAULT 'flyway_migrate.py',
    installed_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL DEFAULT TRUE
);
"""


def _repo_migrations_dir() -> Path:
    # app/scripts -> repo root/docker/flyway/migrations
    return _APP_ROOT.parent / "docker" / "flyway" / "migrations"


def _parse_version(path: Path) -> tuple[int, str, str]:
    # V4__worker.sql -> (4, "4", "worker")
    match = re.match(r"V(\d+)__(.+)\.sql$", path.name, re.IGNORECASE)
    if not match:
        raise ValueError(f"Unexpected migration file name: {path.name}")
    number = int(match.group(1))
    description = match.group(2)
    return number, str(number), description


def _sync_database_url(async_url: str) -> str:
    if async_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + async_url[len("postgresql+asyncpg://") :]
    return async_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FileFlash SQL migrations")
    parser.add_argument("--dry-run", action="store_true", help="List pending migrations only")
    parser.add_argument(
        "--mark-through",
        type=int,
        default=0,
        help="Mark migrations <= this version as applied without executing (baseline existing DB)",
    )
    parser.add_argument(
        "--from-version",
        type=int,
        default=1,
        help="Only consider migrations with version >= this number",
    )
    args = parser.parse_args()

    try:
        import psycopg2
    except ImportError:
        print(
            "psycopg2 is required: uv add --dev psycopg2-binary\n"
            "Or run on Linux VM: bash docker/flyway/run-migrate.sh",
            file=sys.stderr,
        )
        return 1

    settings = get_settings()
    db_url = _sync_database_url(settings.async_database_url)
    migrations_dir = _repo_migrations_dir()
    if not migrations_dir.is_dir():
        print(f"Migrations not found: {migrations_dir}", file=sys.stderr)
        return 1

    files = sorted(migrations_dir.glob("V*.sql"), key=lambda p: _parse_version(p)[0])
    if not files:
        print("No migration files found.", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(HISTORY_DDL)

    cur.execute("SELECT version FROM flyway_schema_history WHERE success = TRUE")
    applied = {row[0] for row in cur.fetchall()}

    pending = []
    for path in files:
        rank, version, description = _parse_version(path)
        if rank < args.from_version:
            continue
        if version in applied:
            print(f"skip V{version} ({description})")
            continue
        if args.mark_through and rank <= args.mark_through:
            print(f"baseline V{version} ({description})")
            cur.execute(
                """
                INSERT INTO flyway_schema_history (version, description, script, success)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT DO NOTHING
                """,
                (version, description, path.name),
            )
            applied.add(version)
            continue
        pending.append((path, version, description))

    if not pending:
        print("All migrations already applied.")
        return 0

    print(f"Database: {db_url.split('@')[-1]}")
    print(f"Pending: {len(pending)} migration(s)")
    for path, version, description in pending:
        print(f"  - V{version} {description} ({path.name})")

    if args.dry_run:
        return 0

    for path, version, description in pending:
        sql = path.read_text(encoding="utf-8")
        print(f"Applying V{version} {description}...")
        try:
            cur.execute(sql)
        except Exception as exc:
            print(f"FAILED V{version}: {exc}", file=sys.stderr)
            conn.close()
            return 2
        cur.execute(
            """
            INSERT INTO flyway_schema_history (version, description, script, success)
            VALUES (%s, %s, %s, TRUE)
            """,
            (version, description, path.name),
        )
        print(f"OK V{version}")

    cur.close()
    conn.close()
    print("Migrations complete. Restart uvicorn and check: agent.db ok table=background_job")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
