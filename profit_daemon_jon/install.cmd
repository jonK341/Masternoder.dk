@echo off
REM Install The Profit Daemon Jon on Windows
set ROOT=%~dp0..
cd /d "%ROOT%"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
)
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r profit_daemon_jon\requirements.txt
if not exist ".env" if exist "profit_daemon_jon\.env.example" (
  copy profit_daemon_jon\.env.example .env
  echo [install] wrote .env from profit_daemon_jon\.env.example
)
.venv\Scripts\python profit_daemon_jon\run.py --install-top25
.venv\Scripts\python profit_daemon_jon\run.py --status
echo.
echo Next:
echo   .venv\Scripts\python profit_daemon_jon\run.py --once --profile paper
echo   .venv\Scripts\python profit_daemon_jon\run.py --sales --hours 3
echo   profit_daemon_jon\build_release.cmd
