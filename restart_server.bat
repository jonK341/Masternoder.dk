@echo off
REM Quick server restart script
echo ========================================
echo RESTARTING FLASK ON UBUNTU SERVER
echo ========================================
echo.
echo This will restart Flask/uWSGI services on masternoder.dk
echo.
pause

python auto_restart_server_flask.py

echo.
echo ========================================
echo Restart complete!
echo ========================================
echo.
echo Visit: https://masternoder.dk/vidgenerator/
echo Hard refresh: Ctrl+F5
echo.
pause
