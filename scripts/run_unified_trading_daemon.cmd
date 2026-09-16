@echo off
setlocal
cd /d "%~dp0.."
if not exist "scripts\unified_trading_daemon.py" (
  echo ERROR: unified_trading_daemon.py missing
  exit /b 1
)
if "%EXCHANGE_PROFIT_PROFILE%"=="" set EXCHANGE_PROFIT_PROFILE=max
echo [unified] exchange + grid + stuck inventory + casino + portal micro-chain
echo [unified] one process — Business Control ^> Unified ops tab
python scripts\unified_trading_daemon.py %*
