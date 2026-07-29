@echo off
title MasterNoder — grid bot daemon
call "%~dp0_daemon_env.cmd"
echo Grid daemon — uses trader_app\config.json (copy from trader_app\config.example.json)
echo Live: EXCHANGE_GRID_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 in config or .env
python scripts\grid_bot_daemon.py %*
