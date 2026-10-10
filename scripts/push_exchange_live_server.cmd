@echo off
call "%~dp0_daemon_env.cmd"
echo Pushing exchange live keys to masternoder.dk server...
python scripts\push_exchange_live_server.py
pause
