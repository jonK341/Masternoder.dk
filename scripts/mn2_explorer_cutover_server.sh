#!/usr/bin/env bash
# Run ON the Masternoder production host (as root) to flip MN2 explorer to self-hosted eiquidus.
# Does NOT deploy Python/JS — run deploy.py mn2_staking static_pages first for new APIs (/api/mn2/services, in-page tx).
set -euo pipefail

APP_ROOT="${APP_ROOT:-/var/www/html}"
ENV_FILE="${ENV_FILE:-$APP_ROOT/.env}"
CONFIG="$APP_ROOT/data/mn2_config.json"
EXPLORER_HOST="${MN2_EXPLORER_HOST:-https://camgirls.masternoder.dk}"

echo "== MN2 explorer cutover =="
echo "App root: $APP_ROOT"

if [[ ! -f "$CONFIG" ]]; then
  echo "ERROR: $CONFIG not found" >&2
  exit 1
fi

python3 << PY
import json
from pathlib import Path
p = Path("$CONFIG")
c = json.loads(p.read_text())
c["explorer_base_url"] = "${EXPLORER_HOST%/}/"
c["explorer_kind"] = "iquidus"
c["explorer_local_api_url"] = "http://127.0.0.1:3000"
c["explorer_fallback_base_url"] = "https://chainz.cryptoid.info/mn2/"
c["explorer_use_local_stats"] = True
p.write_text(json.dumps(c, indent=2) + "\n")
print("Updated", p)
PY

touch "$ENV_FILE"
set_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

set_kv MN2_EXPLORER_BASE_URL "${EXPLORER_HOST%/}/"
set_kv MN2_EXPLORER_KIND iquidus
set_kv MN2_EXPLORER_LOCAL_API_URL http://127.0.0.1:3000
set_kv MN2_EXPLORER_FALLBACK_BASE_URL https://chainz.cryptoid.info/mn2/

echo "== Local eiquidus smoke =="
curl -sf --max-time 5 "http://127.0.0.1:3000/ext/getmoneysupply" | head -c 80 || echo "(local eiquidus not reachable on :3000)"
echo

echo "== Restart uwsgi =="
for svc in uwsgi-vidgenerator uwsgi-vidgenerator-5001; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    systemctl restart "$svc" && echo "restarted $svc"
  fi
done

sleep 2
echo "== Verify (public) =="
curl -sf "https://masternoder.dk/api/mn2/network-overview" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('explorer_kind:', d.get('explorer_kind'))
print('explorer_base_url:', d.get('explorer_base_url'))
print('source:', d.get('source'))
"
