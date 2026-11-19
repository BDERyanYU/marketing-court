$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
uv run --no-sync --env-file .env uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
