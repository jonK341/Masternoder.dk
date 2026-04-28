# Easy start for Flask server - run from project root (double-click or: powershell -File start_server.ps1)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Check if already running
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -UseBasicParsing -TimeoutSec 2
    Write-Host "Server is already running at http://127.0.0.1:5000" -ForegroundColor Green
    Write-Host "Open in browser: http://127.0.0.1:5000"
    Read-Host "Press Enter to close"
    exit 0
} catch {
    # Not running, continue to start
}

Write-Host "Starting Flask server..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1
python run.py
Read-Host "Press Enter to close"
