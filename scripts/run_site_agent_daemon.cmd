@echo off
call "%~dp0_daemon_env.cmd"
echo [site-agent] POST /api/agents/daemon/tick — requires Flask on port 5000 + AGENT_DAEMON_SECRET
python scripts\agent_daemon.py %*
