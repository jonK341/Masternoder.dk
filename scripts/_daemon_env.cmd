@echo off

REM Shared env for all local daemon wrappers (Windows cmd). Usage: call "%~dp0_daemon_env.cmd"

cd /d "%~dp0.."

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set "PYTHONPATH=%CD%"

REM Quiet daemon output — no 154-line blueprint spam per tick
set "DAEMON_QUIET=1"
set "LITE_APP=1"
set "PYTHONUNBUFFERED=1"

REM Load .env into this shell (simple parser — values without embedded =)

if exist ".env" (

  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (

    if not "%%~A"=="" set "%%~A=%%~B"

  )

)

if "%EXCHANGE_ARBITRAGE_LIVE%"=="1" set "EXCHANGE_DAEMON_MODE=live"

if "%EXCHANGE_PAYOUT_PAYPAL_LIVE%"=="1" set "EXCHANGE_DAEMON_MODE=live"

