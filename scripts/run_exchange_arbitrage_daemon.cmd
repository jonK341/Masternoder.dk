@echo off
call "%~dp0_daemon_env.cmd"
echo [redirect] arbitrage-only script -^> unified ALL profit daemons
call "%~dp0run_all_profit_daemons.cmd" --skip-casino %*
