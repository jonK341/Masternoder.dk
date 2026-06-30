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
echo  INVENTORY
echo    i  Show all bots/agents status
echo.
echo  ALL PROFIT (recommended — one window, everything)
echo    a  ALL profit daemons         profile=max (default)
echo    b  ALL profit FAST profile    120s ticks, aggressive scans
echo    c  ALL profit LIVE only       exchange live farm, no casino
echo.
echo  EXCHANGE (legacy — redirect to ALL profit)
echo    1  Exchange MASTER daemon     same as (a) exchange side
echo    2  Exchange arbitrage only    redirects to ALL profit
echo    3  Cross-trade agents only    redirects to ALL profit
echo    4  One tick (test)            exchange bots once (fast)
echo    c  Casino one tick            casino agents only (slow)
echo.
echo  CASINO
echo    5  Casino agent daemon        Nova, Luna, Sage, Ember, Iris
echo.
echo  SITE (needs Flask: start_server.bat first)
echo    6  Site agent daemon          POST /api/agents/daemon/tick
echo.
echo  START ALL (separate cmd windows)
echo    7  Open ALL profit window      exchange + casino unified
echo    8  Open casino only window
echo    9  Open ALL profit + legacy    same as 7 (unified)
echo.
echo  LEGACY / DEV ONLY (real DB writes — staging)
echo    p  Production agent runner    20 simulated players
echo.
echo    l  Live trading readiness + vault key import
    e  Enable LIVE daemon mode (real cash transfer)
echo.
set "CHOICE="
set /p CHOICE="Pick: "

if /i "%CHOICE%"=="a" goto mall
if /i "%CHOICE%"=="b" goto mfast
if /i "%CHOICE%"=="c" goto mlive
if /i "%CHOICE%"=="i" goto inv
if "%CHOICE%"=="1" goto m1
if "%CHOICE%"=="2" goto m2
if "%CHOICE%"=="3" goto m3
if "%CHOICE%"=="4" goto m4
if /i "%CHOICE%"=="c" goto mc
if "%CHOICE%"=="5" goto m5
if "%CHOICE%"=="6" goto m6
if "%CHOICE%"=="7" goto m7
if "%CHOICE%"=="8" goto m8
if "%CHOICE%"=="9" goto m9
if /i "%CHOICE%"=="p" goto leg
if /i "%CHOICE%"=="l" goto live
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

:m1
call "%~dp0run_exchange_master_daemon.cmd"
goto menu

:m2
call "%~dp0run_exchange_arbitrage_daemon.cmd"
goto menu

:m3
call "%~dp0run_crypto_exchange_agent_daemon.cmd"
goto menu

:m4
call "%~dp0run_daemons_once.cmd"
pause
goto menu

:mc
call "%~dp0run_casino_once.cmd"
pause
goto menu

:m5
call "%~dp0run_casino_agent_daemon.cmd"
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

:m9
start "ALL Profit Daemons" cmd /k "%~dp0run_all_profit_daemons.cmd"
echo Started ALL profit daemons in new window.
pause
goto menu

:live
call "%~dp0configure_live_trading.cmd" --import-keys
pause
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
