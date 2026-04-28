@echo off
echo ========================================
echo Restarting Flask Application
echo ========================================
echo.

REM Check if port 5000 is in use
netstat -ano | findstr :5000 >nul
if %errorlevel% == 0 (
    echo Port 5000 is in use. Finding and stopping process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
        echo Stopping process %%a
        taskkill /PID %%a /F >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

echo.
echo Starting Flask application...
echo.
python run.py

