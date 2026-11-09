#!/usr/bin/env bash
# Run ON THE SERVER (SSH). Todo 1: verify DATABASE_URL + systemd EnvironmentFile + DB health.
# Usage: cd /var/www/html && sudo bash scripts/verify_server_env_db.sh
#    or: WEB_ROOT=/var/www/html sudo -E bash /var/www/html/scripts/verify_server_env_db.sh

set -euo pipefail

WEB_ROOT="${WEB_ROOT:-/var/www/html}"
ENV_FILE="${WEB_ROOT}/.env"
UNITS=(uwsgi-vidgenerator uwsgi-vidgenerator-5001)

echo "=== verify_server_env_db (todo 1: DATABASE_URL + systemd) ==="
echo "WEB_ROOT=$WEB_ROOT"
echo

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[FAIL] Missing $ENV_FILE"
  exit 1
fi
echo "[OK] $ENV_FILE exists"
if [[ ! -r "$ENV_FILE" ]]; then
  echo "[FAIL] Not readable: $ENV_FILE"
  exit 1
fi

line="$(grep -E '^[[:space:]]*DATABASE_URL=' "$ENV_FILE" | tail -1 || true)"
if [[ -z "${line}" ]]; then
  echo "[WARN] No DATABASE_URL= in .env (Flask may default to instance/database.db under WEB_ROOT)"
else
  masked="$(echo "$line" | sed -E 's#(postgresql(\+[a-z]+)?|postgres|mysql)://[^:]+:[^@]+@#\1://***:***@#; s#(sqlite:///)([^[:space:]\"]+)#\1<path>#')"
  echo "[INFO] DATABASE_URL (masked): $masked"
fi

for u in "${UNITS[@]}"; do
  if systemctl cat "${u}.service" &>/dev/null; then
    echo
    echo "--- ${u}.service EnvironmentFiles ---"
    systemctl show "${u}.service" -p EnvironmentFiles --no-pager 2>/dev/null || true
    ef="$(systemctl show "${u}.service" -p EnvironmentFiles --value 2>/dev/null || true)"
    if echo "$ef" | grep -q '\.env'; then
      echo "[OK] ${u} loads .env via systemd"
    else
      echo "[WARN] Check unit file: expected EnvironmentFile=-${WEB_ROOT}/.env"
    fi
  else
    echo "[SKIP] ${u}.service not installed"
  fi
done

# SQLite: resolve path like Flask (relative → WEB_ROOT)
if [[ -n "${line}" ]]; then
  raw="${line#DATABASE_URL=}"
  raw="${raw//\"/}"
  raw="${raw//\'/}"
  if [[ "$raw" == sqlite:///* ]]; then
    pathpart="${raw#sqlite:///}"
    if [[ "${pathpart:0:1}" != / ]]; then
      pathpart="${WEB_ROOT}/${pathpart}"
    fi
    dir="$(dirname "$pathpart")"
    echo
    echo "[INFO] SQLite file (resolved): $pathpart"
    [[ -d "$dir" ]] && echo "[OK] dir exists: $dir" || echo "[WARN] missing dir: $dir"
    [[ -f "$pathpart" ]] && ls -la "$pathpart" || echo "[INFO] DB file not created yet (optional)"
  fi
fi

echo
echo "--- GET http://127.0.0.1:5000/api/health/database ---"
HTTP_CODE="$(curl -sS -m 25 -o /tmp/_db_health.json -w '%{http_code}' "http://127.0.0.1:5000/api/health/database" || echo "000")"
echo "HTTP $HTTP_CODE"
head -c 900 /tmp/_db_health.json 2>/dev/null; echo

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "[OK] database health endpoint: 200"
else
  echo "[ACTION] Not 200 — if curl times out or uwsgi restarts: run bash scripts/uwsgi_diagnose_server.sh"
  echo "         See docs/UWSGI_EXIT1_TROUBLESHOOTING.md — check uwsgi.ini CRLF, journalctl, uwsgi.log"
fi

echo
echo "After changing .env:"
echo "  sudo systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001"
echo "=== done ==="
