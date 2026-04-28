# Alternative script using rsync (if available)
# rsync is more efficient for syncing files
# Usage: .\copy_from_server_rsync.ps1

param(
    [string]$ServerHost = "masternoder.dk",
    [string]$Username = "",
    [string]$RemotePath = "/var/www/html",
    [string]$LocalPath = ".\server_backup"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Syncing files using rsync" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if rsync is available
$rsyncAvailable = Get-Command rsync -ErrorAction SilentlyContinue

if (-not $rsyncAvailable) {
    Write-Host "rsync not found. Installing via WSL or using SCP method..." -ForegroundColor Yellow
    Write-Host "Please use copy_from_server.ps1 instead, or install rsync" -ForegroundColor Yellow
    exit
}

# Check if username is provided
if ([string]::IsNullOrEmpty($Username)) {
    $Username = Read-Host "Enter SSH username"
}

# Create local backup directory
if (-not (Test-Path $LocalPath)) {
    New-Item -ItemType Directory -Path $LocalPath -Force | Out-Null
}

Write-Host "Server: $ServerHost" -ForegroundColor Yellow
Write-Host "Username: $Username" -ForegroundColor Yellow
Write-Host "Remote Path: $RemotePath" -ForegroundColor Yellow
Write-Host "Local Path: $LocalPath" -ForegroundColor Yellow
Write-Host ""

# Use rsync for efficient syncing
Write-Host "Starting rsync..." -ForegroundColor Cyan
rsync -avz --progress "$Username@${ServerHost}:${RemotePath}/" "$LocalPath/"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Sync completed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Sync failed!" -ForegroundColor Red
}

