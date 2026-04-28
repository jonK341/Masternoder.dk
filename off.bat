@echo off
REM Stop Ncixg service (Windows)
REM Usage: off.bat

echo ==========================================
echo STOPPING NCIXG SERVICE
echo ==========================================
echo.

echo [1/3] Stopping nginx...
net stop nginx 2>nul || echo   [INFO] nginx not found or already stopped

echo [2/3] Stopping uwsgi-vidgenerator...
net stop uwsgi-vidgenerator 2>nul || echo   [INFO] uwsgi-vidgenerator not found or already stopped

echo [3/3] Stopping python-proxy...
net stop python-proxy 2>nul || echo   [INFO] python-proxy not found or already stopped

echo.
echo ==========================================
echo SERVICE STOPPED
echo ==========================================

pause
