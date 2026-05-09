Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Starting Atlas UI (Dash, one command)..." -ForegroundColor Cyan

# Defaults (override by setting env vars before running this script)
if (-not $env:SUITEUI_ASYNC) { $env:SUITEUI_ASYNC = "0" }
if (-not $env:SUITEUI_USE_REDIS) { $env:SUITEUI_USE_REDIS = "0" }

python -m pip install -e ".[ui]" | Out-Host
python manage.py migrate | Out-Host

Write-Host ""
Write-Host "Open:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host ""

# If async mode is enabled, start a Celery worker in a separate PowerShell.
if ($env:SUITEUI_ASYNC -in @("1","true","yes","y")) {
  Write-Host "Starting Celery worker (async mode)..." -ForegroundColor Cyan
  Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy","Bypass",
    "-Command",
    "cd '$PSScriptRoot\..' ; `$env:SUITEUI_ASYNC='1' ; python -m celery -A suiteui worker -l info -P solo"
  ) | Out-Null
}

# Bind explicitly so the printed URL matches the one to open.
$env:DASH_HOST="127.0.0.1"
$env:DASH_PORT="8000"
python -m dashui.app

