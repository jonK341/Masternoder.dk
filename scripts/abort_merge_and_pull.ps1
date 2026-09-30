# Unblock "MERGE_HEAD exists" so you can sync with origin/main.
# Run from repo root:  powershell -ExecutionPolicy Bypass -File scripts\abort_merge_and_pull.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "Repo:" (Get-Location)
Write-Host ""
git status

if (Test-Path .git\MERGE_HEAD) {
    Write-Host ""
    Write-Host "Aborting unfinished merge..."
    git merge --abort
}

Write-Host ""
Write-Host "Pulling origin main..."
git fetch origin
git pull origin main

Write-Host ""
Write-Host "Done. Latest commits:"
git log --oneline -3
