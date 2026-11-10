@echo off
set ROOT=%~dp0..
cd /d "%ROOT%"
if not exist ".build-venv\Scripts\python.exe" (
  py -3 -m venv .build-venv
)
.build-venv\Scripts\python -m pip install --upgrade pip
.build-venv\Scripts\python -m pip install -r profit_daemon_jon\requirements.txt pyinstaller
.build-venv\Scripts\python profit_daemon_jon\build_release.py
echo [build] artifact ready under dist\TheProfitDaemonJon\
