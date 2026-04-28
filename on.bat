@echo off
REM Start Ncixg service (Windows)
REM Usage: on.bat

echo ==========================================
echo STARTING NCIXG SERVICE
echo ==========================================
echo.

echo [1/4] Starting python-proxy...
net start python-proxy 2>nul || echo   [INFO] python-proxy not found or already started

echo [2/4] Starting uwsgi-vidgenerator...
net start uwsgi-vidgenerator 2>nul || echo   [INFO] uwsgi-vidgenerator not found or already started

timeout /t 2 /nobreak >nul

echo [3/4] Starting nginx...
net start nginx 2>nul || (
    echo   [ERROR] nginx failed to start!
    echo   Check Windows Services or Event Viewer
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul

echo [4/4] Verifying services...
echo.
echo Service Status:
echo ----------------------------------------

sc query python-proxy | findstr "RUNNING" >nul && echo   [OK] python-proxy: running || echo   [WARN] python-proxy: not running
sc query uwsgi-vidgenerator | findstr "RUNNING" >nul && echo   [OK] uwsgi-vidgenerator: running || echo   [WARN] uwsgi-vidgenerator: not running
sc query nginx | findstr "RUNNING" >nul && echo   [OK] nginx: running || (
    echo   [ERROR] nginx: not running
    pause
    exit /b 1
)

echo.
echo ==========================================
echo SERVICE STARTED
echo ==========================================

pause
