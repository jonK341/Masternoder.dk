#!/bin/bash
# Kill duplicate or stuck project processes that spike CPU (wsgi, pytest, ffmpeg, agents).
# Safe to run anytime: leaves pod-daemon, exec-daemon, and VNC/desktop alone.
# Usage: bash scripts/kill_stale_processes.sh [--dry-run]

set -u

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

kill_matching() {
  local label="$1"
  local pattern="$2"
  local pids
  pids=$(pgrep -f "$pattern" 2>/dev/null || true)
  if [[ -z "$pids" ]]; then
    echo "[skip] $label — none running"
    return 0
  fi
  echo "[kill] $label — PIDs: $pids"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ps -o pid,ppid,%cpu,etime,cmd -p $pids 2>/dev/null || true
    return 0
  fi
  kill $pids 2>/dev/null || true
  sleep 1
  local survivors
  survivors=$(pgrep -f "$pattern" 2>/dev/null || true)
  if [[ -n "$survivors" ]]; then
    echo "[force] $label — still alive, sending SIGKILL: $survivors"
    kill -9 $survivors 2>/dev/null || true
  fi
}

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -t -i:"$port" 2>/dev/null || true)
  if [[ -z "$pids" ]]; then
    echo "[skip] port $port — nothing listening"
    return 0
  fi
  echo "[kill] port $port — PIDs: $pids"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ps -o pid,ppid,%cpu,etime,cmd -p $pids 2>/dev/null || true
    return 0
  fi
  kill $pids 2>/dev/null || true
  sleep 1
  local survivors
  survivors=$(lsof -t -i:"$port" 2>/dev/null || true)
  if [[ -n "$survivors" ]]; then
    echo "[force] port $port — still listening, sending SIGKILL: $survivors"
    kill -9 $survivors 2>/dev/null || true
  fi
}

echo "=== Stale process cleanup ==="
echo "Dry run: $([[ $DRY_RUN -eq 1 ]] && echo yes || echo no)"
echo ""
echo "--- CPU snapshot (top 10) ---"
ps -eo pid,%cpu,%mem,etime,cmd --sort=-%cpu | head -11
echo ""

kill_port 5000
kill_matching "wsgi dev server" '\.venv/bin/python.*wsgi'
kill_matching "dev app server" '\.venv/bin/python.*(app\.py|run\.py)'
kill_matching "pytest" '\.venv/bin/python.*pytest'
kill_matching "video generator subprocess" 'run_generator_job\.py'
kill_matching "ffmpeg (videos dir)" 'ffmpeg.*videos/'
kill_matching "agent runner" '_agent_runner\.py'

echo ""
echo "--- After cleanup ---"
echo "Port 5000: $(ss -tlnp 2>/dev/null | grep ':5000' || echo 'free')"
echo "Project PIDs: $(pgrep -af 'wsgi|pytest|run_generator_job|ffmpeg.*videos|_agent_runner' 2>/dev/null | wc -l) remaining"
ps -eo pid,%cpu,%mem,etime,cmd --sort=-%cpu | head -6
echo ""
echo "Done. Restart ONE dev server when needed:"
echo "  cd /workspace && .venv/bin/python wsgi.py"
