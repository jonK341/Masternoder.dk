@echo off
REM Build MN2 Private Control into a standalone Windows .exe using a dedicated build venv.
REM   trader_app\build_exe.bat
setlocal
set ROOT=%~dp0..
set VENV=%ROOT%\.build-venv

if not exist "%VENV%\Scripts\python.exe" (
  echo [build] creating build venv at %VENV%
  python -m venv "%VENV%"
)
"%VENV%\Scripts\python" -m pip install --upgrade pip
echo [build] installing build deps (pyinstaller, flask, requests, cryptography)...
"%VENV%\Scripts\python" -m pip install pyinstaller flask requests cryptography
echo [build] running PyInstaller...
"%VENV%\Scripts\python" "%ROOT%\trader_app\build_exe.py"
echo [build] done -^> %ROOT%\dist\MN2PrivateControl\MN2PrivateControl.exe
endlocal
