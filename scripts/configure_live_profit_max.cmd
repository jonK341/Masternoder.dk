@echo off
title Configure LIVE profit MAX
call "%~dp0_daemon_env.cmd"
python scripts\configure_live_profit_max.py
pause
