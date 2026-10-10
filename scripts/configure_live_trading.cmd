@echo off
call "%~dp0_daemon_env.cmd"
python scripts\configure_live_trading.py %*
