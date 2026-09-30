@echo off
REM Legacy player-behavior sim — prefer scripts\run_daemons.cmd for exchange/casino bots.
REM WARNING: writes real DB entries. Use only on staging/dev.
cd /d %~dp0..
call scripts\_daemon_env.cmd
echo See scripts\run_daemons.cmd for exchange + casino daemons.
set /p OK="Start legacy production_agent_runner anyway? (YES): "
if /not "%OK%"=="YES" exit /b 1
python scripts\production_agent_runner.py
