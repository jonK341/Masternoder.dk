#Requires -Version 5.1
<#
.SYNOPSIS
  Starts the MN2 daemon helper (bash) on Windows via Git Bash or bash on PATH.

  PowerShell does not run .sh files natively and has no chmod/export like bash.

  Production: SSH to Linux and run there:
    cd /var/www/html && bash scripts/run_masternoder2d.sh

.NOTES
  Install Git for Windows to get bash, or use WSL.
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Sh = Join-Path $PSScriptRoot "run_masternoder2d.sh"

if (-not (Test-Path $Sh)) {
    Write-Error "Missing $Sh"
    exit 1
}

function Find-Bash {
    $c = Get-Command bash -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $git = "${env:ProgramFiles}\Git\bin\bash.exe"
    if (Test-Path $git) { return $git }
    $git32 = "${env:ProgramFiles(x86)}\Git\bin\bash.exe"
    if (Test-Path $git32) { return $git32 }
    return $null
}

$bash = Find-Bash
if (-not $bash) {
    Write-Host @"

  No 'bash' found. Options:

  1) Install Git for Windows (includes Git Bash): https://git-scm.com/download/win
     Then open Git Bash in this repo and run:
       bash scripts/run_masternoder2d.sh

  2) Use WSL: wsl -e bash -c "cd /mnt/<drive>/path/to/Masternoder.dk && bash scripts/run_masternoder2d.sh"

  3) Production daemon runs on Linux — SSH to the server:
       ssh user@server
       cd /var/www/html && bash scripts/run_masternoder2d.sh

  See docs/MN2_DAEMON_SETUP.md

"@ -ForegroundColor Yellow
    exit 1
}

# PowerShell env vars are passed to child processes
Set-Location $RepoRoot
Write-Host "Using: $bash" -ForegroundColor DarkGray
Write-Host "Repo:  $RepoRoot" -ForegroundColor DarkGray
& $bash -lc "chmod +x scripts/run_masternoder2d.sh 2>/dev/null; exec bash scripts/run_masternoder2d.sh"
