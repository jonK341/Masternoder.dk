@echo off
cd /d "%~dp0"
echo Checking if server is already running...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:5000/' -UseBasicParsing -TimeoutSec 2 | Out-Null; Write-Host 'Server already running at http://127.0.0.1:5000'; pause; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% equ 0 exit /b 0
echo Starting Flask server...
call .venv\Scripts\activate.bat
python run.py
pause
