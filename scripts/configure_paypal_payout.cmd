@echo off
REM Configure exchange profit payout to your PayPal (reads EXCHANGE_PAYOUT_PAYPAL_EMAIL from .env)
cd /d "%~dp0.."
call scripts\_daemon_env.cmd 2>nul
python scripts\configure_paypal_payout.py %*
