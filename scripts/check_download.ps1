# Quick download status checker
Write-Host "Download Status Check" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path ".\server_backup\html") {
    $files = (Get-ChildItem ".\server_backup\html" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    $size = [math]::Round((Get-ChildItem ".\server_backup\html" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    
    Write-Host "Total Files: $files" -ForegroundColor White
    Write-Host "Total Size: $size MB" -ForegroundColor White
    Write-Host ""
    
    if (Test-Path ".\server_backup\html\vidgenerator") {
        Write-Host "OK: vidgenerator EXISTS!" -ForegroundColor Green
        $vgFiles = (Get-ChildItem ".\server_backup\html\vidgenerator" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
        $vgDirs = (Get-ChildItem ".\server_backup\html\vidgenerator" -Recurse -Directory -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "   Files: $vgFiles" -ForegroundColor White
        Write-Host "   Directories: $vgDirs" -ForegroundColor White
        Write-Host ""
        Write-Host "READY: Ready for integration!" -ForegroundColor Green
    } else {
        Write-Host "WAIT: vidgenerator still downloading..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Directories downloaded:" -ForegroundColor Cyan
        Get-ChildItem ".\server_backup\html" -Directory | Select-Object -First 5 Name | ForEach-Object {
            Write-Host "   Directory: $($_.Name)" -ForegroundColor White
        }
    }
} else {
    Write-Host "ERROR: Server backup directory not found" -ForegroundColor Red
}

Write-Host ""
