#!/usr/bin/env bash
# Fresh 10 Jon Film appointments every day + Discord vote refresh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export LITE_APP="${LITE_APP:-1}"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi
"$PY" "$ROOT/scripts/jon_film_daily_tick.py" >>"$ROOT/logs/jon_film_daily.log" 2>&1 || true
# Also hit HTTP cron if app is up (auth optional when secret unset locally).
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
TOKEN=""
if [[ -f "$ENV" ]]; then
  TOKEN=$(grep '^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"' || true)
fi
if [[ -n "${TOKEN:-}" ]]; then
  curl -sS -m 30 -X POST -H "X-Agent-Cron-Token: $TOKEN" \
    "http://127.0.0.1:5000/api/landing/monitor/jon-film/cron" >/dev/null || true
else
  curl -sS -m 30 -X POST "http://127.0.0.1:5000/api/landing/monitor/jon-film/cron" >/dev/null || true
fi
