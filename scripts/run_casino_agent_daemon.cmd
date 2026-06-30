@echo off
call "%~dp0_daemon_env.cmd"
echo [casino-agent] autonomous casino bots — Nova, Luna, Sage, Ember, Iris
echo [casino-agent] spectator feed -> logs/casino_agent_spectator.jsonl
if "%CASINO_AGENT_DRY_RUN%"=="1" (
  echo [casino-agent] DRY_RUN — set CASINO_AGENT_DRY_RUN=0 for live bets
  python scripts\casino_agent_daemon.py --dry-run --interval 300 %*
) else (
  python scripts\casino_agent_daemon.py --interval 300 %*
)
