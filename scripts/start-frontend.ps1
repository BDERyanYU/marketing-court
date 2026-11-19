$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'frontend')
pnpm exec vite --host 127.0.0.1 --port 5173 --strictPort
