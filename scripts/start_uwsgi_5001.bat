@echo off
REM =============================================================================
REM  Start remote: systemd uwsgi-vidgenerator-5001 (port 5001 backend)
REM  Doc: docs\UWSGI_SECOND_INSTANCE.md
REM  Server: systemd\uwsgi-vidgenerator-5001.service  (uwsgi --ini uwsgi_5001.ini)
REM  If the service exits with status 1: deploy uwsgi_5001.ini + uwsgi.ini (separate pidfiles).
REM =============================================================================
title Start uwsgi-vidgenerator-5001

cd /d "%~dp0.." || (
  echo [ERROR] Could not cd to project root.
  pause
  exit /b 1
)

set "SYSTEMD_UNIT=uwsgi-vidgenerator-5001"
REM Optional: set DEPLOY_HOST=  DEPLOY_USER=  DEPLOY_PASS=  before double-click

chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"

echo.
echo  SYSTEMD_UNIT=%SYSTEMD_UNIT%
echo  Project: %CD%
echo.

set "SCRIPT=%~dp0start_uwsgi_5001.py"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "%SCRIPT%"
  goto :after
)
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" "%SCRIPT%"
  goto :after
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%SCRIPT%"
  goto :after
)

python "%SCRIPT%"
if errorlevel 1 (
  echo.
  echo [ERROR] Python not found or script failed. Use Python 3: pip install paramiko
)

:after
if errorlevel 1 (
  echo.
  pause
)
exit /b
