Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Starting Atlas UI (Dash)..." -ForegroundColor Cyan

python -m pip install -e ".[ui]" | Out-Host

python manage.py migrate | Out-Host

Write-Host ""
Write-Host "Open:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host ""

# Local default: run jobs immediately in-process (no Celery worker required).
$env:SUITEUI_ASYNC="0"
$env:SUITEUI_USE_REDIS="0"

# Bind explicitly so the printed URL matches the one to open.
$env:DASH_HOST="127.0.0.1"
$env:DASH_PORT="8000"
python -m dashui.app

