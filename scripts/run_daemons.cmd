@echo off
title MasterNoder daemons
call "%~dp0_daemon_env.cmd"

:menu
cls
echo ========================================================================
echo  MasterNoder — daemons, bots and agents (local Windows cmd)
echo  Repo: %CD%
echo ========================================================================
echo.
echo  ALL PROFIT (recommended — one process, exchange + casino)
echo    a  ALL profit daemons         profile=max (default)
echo    b  ALL profit FAST profile    120s ticks, aggressive scans
echo    d  ALL profit LIVE only       exchange live farm, no casino
echo.
echo  UTILITIES
echo    i  Inventory — bots/agents status
echo    h  Health — preflight + last heartbeat
echo    s  Status report — full live profit snapshot
echo    4  One tick — all profit engines (quick test)
echo    5  One tick — casino agents only
echo.
echo  SEPARATE WINDOWS
echo    7  Open ALL profit window
echo    8  Open casino-only loop window
echo.
echo  SITE (needs Flask: start_server.bat first)
echo    6  Site agent daemon          POST /api/agents/daemon/tick
echo.
echo  LIVE SETUP
echo    l  Live trading readiness + vault key import
echo    m  Configure LIVE profit MAX (tune + vault + faster scans)
echo    e  Enable LIVE daemon mode (real cash transfer)
echo.
echo  LEGACY / DEV ONLY (real DB writes — staging)
echo    p  Production agent runner    20 simulated players
echo.
set "CHOICE="
set /p CHOICE="Pick: "

if /i "%CHOICE%"=="a" goto mall
if /i "%CHOICE%"=="b" goto mfast
if /i "%CHOICE%"=="d" goto mlive
if /i "%CHOICE%"=="i" goto inv
if /i "%CHOICE%"=="h" goto health
if /i "%CHOICE%"=="s" goto status
if "%CHOICE%"=="4" goto m4
if "%CHOICE%"=="5" goto mc
if "%CHOICE%"=="6" goto m6
if "%CHOICE%"=="7" goto m7
if "%CHOICE%"=="8" goto m8
if /i "%CHOICE%"=="p" goto leg
if /i "%CHOICE%"=="l" goto live
if /i "%CHOICE%"=="m" goto livemax
if /i "%CHOICE%"=="e" goto enablelive
if "%CHOICE%"=="0" exit /b 0
echo Invalid choice.
timeout /t 2 >nul
goto menu

:mall
call "%~dp0run_all_profit_daemons.cmd"
goto menu

:mfast
call "%~dp0run_all_profit_fast.cmd"
goto menu

:mlive
call "%~dp0run_all_profit_live.cmd"
goto menu

:inv
call "%~dp0daemon_inventory.cmd"
pause
goto menu

:health
python scripts\daemon_preflight.py
if exist "logs\daemon_all_profit_heartbeat.json" (
  echo.
  type logs\daemon_all_profit_heartbeat.json
)
pause
goto menu

:status
call "%~dp0profit_status_report.cmd"
goto menu

:m4
call "%~dp0run_daemons_once.cmd"
pause
goto menu

:mc
call "%~dp0run_casino_once.cmd"
pause
goto menu

:m6
call "%~dp0run_site_agent_daemon.cmd"
goto menu

:m7
start "ALL Profit Daemons" cmd /k "%~dp0run_all_profit_daemons.cmd"
echo Started ALL profit daemons in new window.
pause
goto menu

:m8
start "Casino Agent Daemon" cmd /k "%~dp0run_casino_agent_daemon.cmd"
echo Started casino agents only in new window.
pause
goto menu

:live
call "%~dp0configure_live_trading.cmd" --import-keys
pause
goto menu

:livemax
call "%~dp0configure_live_profit_max.cmd"
goto menu

:enablelive
call "%~dp0enable_live_daemons.cmd"
goto menu

:leg
echo WARNING: production_agent_runner writes to the real database.
set /p OK="Type YES to continue: "
if /not "%OK%"=="YES" goto menu
python scripts\production_agent_runner.py
pause
goto menu
