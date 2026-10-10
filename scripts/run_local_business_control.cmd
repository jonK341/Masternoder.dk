@echo off
title Local Business Control (port 8800)
cd /d "%~dp0.."
call "%~dp0_daemon_env.cmd"
echo Local bridge for Business Control tab — http://127.0.0.1:8800/
python scripts\local_business_control_server.py
