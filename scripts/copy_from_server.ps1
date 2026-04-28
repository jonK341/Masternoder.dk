# Script to copy files from masternoder.dk /var/www/html to local directory
# Usage: .\copy_from_server.ps1

param(
    [string]$ServerHost = "masternoder.dk",
    [string]$Username = "",
    [string]$RemotePath = "/var/www/html",
    [string]$LocalPath = ".\server_backup"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Copying files from masternoder.dk server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if username is provided
if ([string]::IsNullOrEmpty($Username)) {
    $Username = Read-Host "Enter SSH username (e.g., root, admin, or your username)"
}

# Create local backup directory
if (-not (Test-Path $LocalPath)) {
    New-Item -ItemType Directory -Path $LocalPath -Force | Out-Null
    Write-Host "Created local directory: $LocalPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Server: $ServerHost" -ForegroundColor Yellow
Write-Host "Username: $Username" -ForegroundColor Yellow
Write-Host "Remote Path: $RemotePath" -ForegroundColor Yellow
Write-Host "Local Path: $LocalPath" -ForegroundColor Yellow
Write-Host ""

# Test SSH connection first
Write-Host "Testing SSH connection..." -ForegroundColor Cyan
$testConnection = ssh -o ConnectTimeout=10 -o BatchMode=yes "$Username@$ServerHost" "echo 'Connection successful'" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "SSH connection test failed. You may need to:" -ForegroundColor Red
    Write-Host "1. Enter password when prompted" -ForegroundColor Yellow
    Write-Host "2. Set up SSH keys for passwordless access" -ForegroundColor Yellow
    Write-Host "3. Check if SSH service is running on the server" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit
    }
}

Write-Host ""
Write-Host "Starting file copy..." -ForegroundColor Cyan
Write-Host "This may take a while depending on file size..." -ForegroundColor Yellow
Write-Host ""

# Use SCP to copy files recursively
$scpCommand = "scp -r `"$Username@${ServerHost}:${RemotePath}/*`" `"$LocalPath`""

Write-Host "Running: $scpCommand" -ForegroundColor Gray
Write-Host ""

# Execute SCP
scp -r "$Username@${ServerHost}:${RemotePath}/*" "$LocalPath"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Files copied successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Files are located in: $LocalPath" -ForegroundColor Cyan
    
    # Show summary
    $fileCount = (Get-ChildItem -Path $LocalPath -Recurse -File | Measure-Object).Count
    $dirCount = (Get-ChildItem -Path $LocalPath -Recurse -Directory | Measure-Object).Count
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Yellow
    Write-Host "  Files: $fileCount" -ForegroundColor White
    Write-Host "  Directories: $dirCount" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Copy failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "1. Incorrect username or password" -ForegroundColor White
    Write-Host "2. SSH keys not set up" -ForegroundColor White
    Write-Host "3. Server path does not exist" -ForegroundColor White
    Write-Host "4. Permission denied" -ForegroundColor White
    Write-Host ""
    Write-Host "Try running manually:" -ForegroundColor Cyan
    Write-Host "  scp -r $Username@${ServerHost}:${RemotePath}/* $LocalPath" -ForegroundColor Gray
}

