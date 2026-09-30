@echo off
call "%~dp0_daemon_env.cmd"
if not defined CASINO_AGENT_DRY_RUN set "CASINO_AGENT_DRY_RUN=1"
if not defined CASINO_AGENT_INTERVAL set "CASINO_AGENT_INTERVAL=300"
echo [casino-agent] autonomous casino bots — Nova, Luna, Sage, Ember, Iris
echo [casino-agent] spectator feed -> logs/casino_agent_spectator.jsonl
echo [casino-agent] interval=%CASINO_AGENT_INTERVAL%s dry_run=%CASINO_AGENT_DRY_RUN%
if "%CASINO_AGENT_DRY_RUN%"=="1" (
  echo [casino-agent] DRY_RUN — set CASINO_AGENT_DRY_RUN=0 or pass --live for real bets
  python scripts\casino_agent_daemon.py --dry-run %*
) else (
  python scripts\casino_agent_daemon.py --live %*
)
