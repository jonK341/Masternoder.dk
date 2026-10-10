@echo off
title MasterNoder — grid bot daemon
call "%~dp0_daemon_env.cmd"
if not exist "scripts\grid_bot_daemon.py" (
  echo ERROR: scripts\grid_bot_daemon.py not found. Repo root is: %CD%
  echo Pull latest main from GitHub, then run from the repo root folder.
  pause
  exit /b 1
)
if not exist "trader_app\config.json" (
  echo NOTE: trader_app\config.json missing — copy trader_app\config.example.json and set EXCHANGE_GRID_LIVE=1
)
echo Grid daemon — Live: EXCHANGE_GRID_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 in config or .env
python scripts\grid_bot_daemon.py %*
