@echo off
call "%~dp0_daemon_env.cmd"
echo [once] single tick — ALL profit engines (exchange + casino)
python scripts\all_profit_daemons.py --once %*
