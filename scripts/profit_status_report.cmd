@echo off
call "%~dp0_daemon_env.cmd"
python scripts\profit_status_report.py --save %*
