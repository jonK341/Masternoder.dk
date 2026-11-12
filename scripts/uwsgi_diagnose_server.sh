#!/usr/bin/env bash
# Run ON THE SERVER (SSH). Diagnose uwsgi exit 1 / curl timeout on :5000.
# Usage: cd /var/www/html && sudo bash scripts/uwsgi_diagnose_server.sh

set -euo pipefail

WEB_ROOT="${WEB_ROOT:-/var/www/html}"
cd "$WEB_ROOT"

echo "=== uwsgi_diagnose_server ==="
echo "WEB_ROOT=$WEB_ROOT"
echo

echo "--- CRLF check (should be empty) ---"
for f in uwsgi.ini uwsgi_common.ini uwsgi_5001.ini; do
  if [[ -f "$f" ]]; then
    if grep -q $'\r' "$f" 2>/dev/null; then
      echo "[BAD] $f contains CR — fix: sed -i 's/\\r\$//' $f"
    else
      echo "[OK] $f (no CR)"
    fi
  else
    echo "[MISS] $f"
  fi
done
echo

echo "--- uWSGI binary ---"
command -v uwsgi && uwsgi --version || echo "[FAIL] uwsgi not in PATH"
echo

echo "--- Python3 import wsgi (as www-data, same as workers) ---"
if sudo -u www-data env PYTHONPATH="$WEB_ROOT" python3 -c "
import os, sys
os.chdir('$WEB_ROOT')
sys.path.insert(0, '$WEB_ROOT')
import wsgi
print('application:', type(wsgi.application).__name__)
" 2>&1; then
  echo "[OK] python3 can load wsgi.application"
else
  echo "[FAIL] Import failed — see traceback above (missing dep, wrong Python, permission)."
fi
echo

echo "--- systemd (last 15 lines per unit) ---"
for u in uwsgi-vidgenerator uwsgi-vidgenerator-5001; do
  if systemctl cat "${u}.service" &>/dev/null; then
    echo "--- journalctl -u $u ---"
    journalctl -u "$u" -n 15 --no-pager 2>/dev/null || true
  fi
done
echo

echo "--- tail uwsgi.log (last 40 lines) ---"
if [[ -f uwsgi.log ]]; then
  tail -40 uwsgi.log
else
  echo "[MISS] uwsgi.log"
fi
echo

echo "--- listeners 5000 / 5001 ---"
ss -tlnp | grep -E ':5000|:5001' || true
echo

echo "=== done ==="
echo "If master exits with 1: run foreground (see docs/UWSGI_EXIT1_TROUBLESHOOTING.md):"
echo "  sudo systemctl stop uwsgi-vidgenerator"
echo "  sudo -u www-data bash -c 'cd $WEB_ROOT && uwsgi --ini $WEB_ROOT/uwsgi.ini'"
