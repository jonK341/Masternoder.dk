@echo off
set EXCHANGE_PROFIT_PROFILE=live-only
call "%~dp0run_all_profit_daemons.cmd" --skip-casino %*
