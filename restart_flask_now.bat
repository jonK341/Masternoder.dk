@echo off
echo ========================================
echo RESTARTING FLASK APPLICATION
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
    echo Process stopped.
) else (
    echo No process found on port 5000.
)

echo.
echo Starting Flask application...
echo.
echo The application will start in a new window.
echo Close this window after Flask starts.
echo.

start "Flask App" cmd /k "python run.py"

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo Flask application restart initiated!
echo ========================================
echo.
echo Please check the Flask window for startup messages.
echo Once Flask is running, refresh your browser to see updates.
echo.
pause
