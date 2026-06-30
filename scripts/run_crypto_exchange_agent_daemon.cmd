@echo off
call "%~dp0_daemon_env.cmd"
echo [redirect] cross-trade-only script -^> unified ALL profit daemons
echo            includes arb + AI + cross-trade + marketplace + casino
call "%~dp0run_all_profit_daemons.cmd" %*
