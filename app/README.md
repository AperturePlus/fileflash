## Run Backend (API + Workers)

Use one command to start backend API and file workers together:

```bash
uv run python -m fileflash.scripts.run_with_workers
```

Common options:

```bash
# custom host/port
uv run python -m fileflash.scripts.run_with_workers --host 127.0.0.1 --port 8080

# start multiple worker processes
uv run python -m fileflash.scripts.run_with_workers --worker-count 2

# API only (without workers)
uv run python -m fileflash.scripts.run_with_workers --no-worker
```

Notes:
- This runner starts `uvicorn fileflash.main:app` and `python -m fileflash.workers.consumer`.
- If any subprocess exits, the runner stops all other subprocesses.
- If your environment resolves project scripts correctly, `uv run fileflash-dev` is equivalent.

## Database Migration Requirement

Before starting API processes, ensure Flyway migrations are fully applied (including `V10__identity_avatar.sql` and later).

Recommended startup order:
1. Start PostgreSQL
2. Run Flyway migrate
3. Start API (`uv run fileflash`) or runner (`uv run fileflash-dev`)

If the schema is outdated, API startup will fail fast with an explicit compatibility error.
