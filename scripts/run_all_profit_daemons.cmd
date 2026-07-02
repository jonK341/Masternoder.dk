@echo off

title MasterNoder — ALL profit daemons

REM Optional: --auto-sweep  (needs EXCHANGE_AUTO_PAYPAL_SWEEP=1 + EXCHANGE_PAYOUT_PAYPAL_LIVE=1 for real PayPal)
REM Optional: EXCHANGE_AUTO_SWEEP_MIN_USD=500  overrides payout_config min_sweep_usd threshold

call "%~dp0_daemon_env.cmd"



REM Profile: max (default) | standard | fast | live-only

if not "%EXCHANGE_PROFIT_PROFILE%"=="" set "PROFILE=%EXCHANGE_PROFIT_PROFILE%"

if "%PROFILE%"=="" set "PROFILE=max"



if "%EXCHANGE_DAEMON_MODE%"=="live" (

  echo ========================================================================

  echo  ALL PROFIT DAEMONS — LIVE  profile=%PROFILE%

  echo  12 arb agents + AI trader + 7 cross-trade + extended strategies + casino

  echo ========================================================================

) else (

  echo ========================================================================

  echo  ALL PROFIT DAEMONS — paper  profile=%PROFILE%

  echo  Run enable_live_daemons.cmd for real venue orders

  echo ========================================================================

)



if "%CASINO_AGENT_DRY_RUN%"=="1" (

  python scripts\all_profit_daemons.py --profile %PROFILE% --casino-dry-run %*

) else (

  python scripts\all_profit_daemons.py --profile %PROFILE% %*

)

