#!/usr/bin/env bash
# systemd / cron healthcheck for masternoder-profit-daemon.service
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HB="$ROOT/logs/daemon_all_profit_heartbeat.json"
STALE="${PROFIT_DAEMON_STALE_SEC:-300}"

if [[ ! -f "$HB" ]]; then
  echo "FAIL: missing heartbeat $HB"
  exit 1
fi

python3 - <<'PY' "$HB" "$STALE"
import json, sys
from datetime import datetime, timezone

path, stale_sec = sys.argv[1], float(sys.argv[2])
with open(path, encoding="utf-8") as f:
    hb = json.load(f)
updated = hb.get("updated_at") or ""
try:
    ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - ts).total_seconds()
except Exception:
    print("FAIL: invalid heartbeat timestamp")
    raise SystemExit(1)
if age > stale_sec:
    print(f"FAIL: heartbeat stale {age:.0f}s > {stale_sec}s")
    raise SystemExit(1)
if hb.get("profit_kill"):
    print("WARN: EXCHANGE_PROFIT_KILL active")
loops = hb.get("loops") or {}
ex = loops.get("exchange") or {}
ex_age = ex.get("updated_at") or ""
print(f"OK: heartbeat age={age:.0f}s exchange={ex_age[:19]}")
PY
