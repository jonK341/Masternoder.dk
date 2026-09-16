@echo off
call "%~dp0_daemon_env.cmd"
python scripts\daemon_inventory.py %*
