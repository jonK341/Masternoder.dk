@echo off
call "%~dp0_daemon_env.cmd"
echo [once-casino] casino agents only — may load Flask (slow first run)
python scripts\casino_agent_daemon.py --once %*
