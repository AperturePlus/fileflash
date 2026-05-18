#!/usr/bin/env bash
# Run from repo root: bash docker/flyway/run-migrate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIGRATIONS="$ROOT/docker/flyway/migrations"

DB_HOST="${FF_DB_HOST:-192.168.100.128}"
DB_PORT="${FF_DB_PORT:-5432}"
DB_NAME="${FF_DB_NAME:-fileflash}"
DB_USER="${FF_DB_USER:-admin}"
DB_PASSWORD="${FF_DB_PASSWORD:-psgl-ff-db}"

echo "Flyway migrate -> jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"
docker run --rm \
  -v "${MIGRATIONS}:/flyway/sql" \
  flyway/flyway:10 \
  -url="jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}" \
  -user="${DB_USER}" \
  -password="${DB_PASSWORD}" \
  -connectRetries=3 \
  migrate

echo "Done. Look for agent.db ok in uvicorn startup logs."
