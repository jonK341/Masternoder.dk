@echo off
call "%~dp0_daemon_env.cmd"
echo [redirect] exchange master -^> unified ALL profit daemons (exchange+casino)
call "%~dp0run_all_profit_daemons.cmd" %*
