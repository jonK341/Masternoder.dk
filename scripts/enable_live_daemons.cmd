@echo off
call "%~dp0_daemon_env.cmd"
echo Enabling LIVE exchange daemon mode (real venue orders + PayPal sweeps)...
python scripts\enable_live_daemons.py
pause
