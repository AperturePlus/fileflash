## Run Backend (API + Workers)

Use one command to start backend API and file workers together:

```bash
uv run fileflash
```

Common options:

```bash
# custom host/port
uv run fileflash --host 127.0.0.1 --port 8080

# start multiple worker processes
uv run fileflash --worker-count 2

# API only (without workers)
uv run fileflash --no-worker
```

Notes:
- This runner starts `uvicorn fileflash.main:app` and `python -m fileflash.workers.consumer`.
- If any subprocess exits, the runner stops all other subprocesses.
- `uv run fileflash-dev` is kept as a backward-compatible alias.

## Database Migration Requirement

Before starting API processes, ensure Flyway migrations are fully applied (including `V10__identity_avatar.sql` and later).

Recommended startup order:
1. Start PostgreSQL
2. Run Flyway migrate
3. Start backend (`uv run fileflash`; `uv run fileflash-dev` is also supported)

If the schema is outdated, API startup will fail fast with an explicit compatibility error.
