Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Starting Celery worker..." -ForegroundColor Cyan
Write-Host "Requires Redis running (localhost:6379)." -ForegroundColor Yellow

python -m pip install -e ".[ui]" | Out-Host

# Use distributed execution mode
$env:SUITEUI_ASYNC="1"
$env:SUITEUI_USE_REDIS="1"

# Windows-friendly pool
python -m celery -A suiteui worker -l info -P solo

