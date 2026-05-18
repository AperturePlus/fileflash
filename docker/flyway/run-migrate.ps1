# Run all Flyway migrations against the VM Postgres (edit connection if needed).
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File docker/flyway/run-migrate.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path "$RepoRoot/docker/flyway/migrations/V1__base.sql")) {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}

$Migrations = Join-Path $RepoRoot "docker/flyway/migrations"
$DbHost = if ($env:FF_DB_HOST) { $env:FF_DB_HOST } else { "192.168.100.128" }
$DbPort = if ($env:FF_DB_PORT) { $env:FF_DB_PORT } else { "5432" }
$DbName = if ($env:FF_DB_NAME) { $env:FF_DB_NAME } else { "fileflash" }
$DbUser = if ($env:FF_DB_USER) { $env:FF_DB_USER } else { "admin" }
$DbPassword = if ($env:FF_DB_PASSWORD) { $env:FF_DB_PASSWORD } else { "psgl-ff-db" }

Write-Host "Flyway migrate -> jdbc:postgresql://${DbHost}:${DbPort}/${DbName} (user=$DbUser)"
Write-Host "SQL dir: $Migrations"

docker run --rm `
  -v "${Migrations}:/flyway/sql" `
  flyway/flyway:10 `
  -url="jdbc:postgresql://${DbHost}:${DbPort}/${DbName}" `
  -user="$DbUser" `
  -password="$DbPassword" `
  -connectRetries=3 `
  migrate

Write-Host "Done. Restart uvicorn and check startup logs for agent.db ok"
