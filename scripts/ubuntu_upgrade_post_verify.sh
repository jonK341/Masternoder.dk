#!/usr/bin/env bash
# Post-Ubuntu-upgrade verification for masternoder.dk.
# Run ON THE SERVER after reboot and package upgrades complete.
#
# Usage:
#   cd /var/www/html && sudo bash scripts/ubuntu_upgrade_post_verify.sh
#
set -euo pipefail

WEB_ROOT="${WEB_ROOT:-/var/www/html}"
cd "$WEB_ROOT"

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
    return 0
  fi
  echo "FAIL: $name"
  FAIL=$((FAIL + 1))
  return 1
}

warn() {
  echo "WARN: $1"
  WARN=$((WARN + 1))
}

echo "=== MN2 post-Ubuntu-upgrade verify ==="
echo "WEB_ROOT=$WEB_ROOT"
if [[ -f /etc/os-release ]]; then
  grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release || true
fi
uname -r
echo

echo "--- Core services ---"
for u in nginx masternoder2d uwsgi-vidgenerator uwsgi-vidgenerator-5001; do
  if systemctl is-active --quiet "$u" 2>/dev/null; then
    echo "PASS: systemd $u active"
    PASS=$((PASS + 1))
  else
    echo "FAIL: systemd $u not active"
    FAIL=$((FAIL + 1))
    echo "  Try: systemctl start $u && journalctl -u $u -n 30 --no-pager"
  fi
done
echo

echo "--- uWSGI / Python ---"
if [[ -x "$WEB_ROOT/scripts/uwsgi_diagnose_server.sh" ]]; then
  bash "$WEB_ROOT/scripts/uwsgi_diagnose_server.sh" | tail -30 || warn "uwsgi_diagnose had errors"
else
  warn "uwsgi_diagnose_server.sh missing"
fi
echo

echo "--- MN2 daemon RPC ---"
DAEMON_VER=$(/opt/masternoder2d/masternoder2d -version 2>/dev/null || echo "unknown")
echo "daemon: $DAEMON_VER"
if command -v masternoder2-cli >/dev/null 2>&1 || [[ -x /opt/masternoder2d/masternoder2-cli ]]; then
  CLI=/opt/masternoder2d/masternoder2-cli
  [[ -x "$CLI" ]] || CLI=masternoder2-cli
  $CLI -datadir="$WEB_ROOT/config" getblockcount 2>/dev/null | head -1 || warn "getblockcount failed"
else
  warn "masternoder2-cli not in PATH"
fi
echo

echo "--- Local HTTP smoke ---"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 http://127.0.0.1:5000/api/health 2>/dev/null || echo 000)
if [[ "$CODE" == "200" || "$CODE" == "503" ]]; then
  echo "PASS: /api/health HTTP $CODE (503 = degraded/wallet locked — run restore-staking)"
  PASS=$((PASS + 1))
else
  echo "FAIL: /api/health HTTP $CODE"
  FAIL=$((FAIL + 1))
fi

CODE2=$(curl -s -o /dev/null -w '%{http_code}' --max-time 45 'http://127.0.0.1:5000/api/camgirls/performers?user_id=verify&lite=1' 2>/dev/null || echo 000)
if [[ "$CODE2" == "200" ]]; then
  echo "PASS: camgirls performers lite HTTP 200"
  PASS=$((PASS + 1))
else
  echo "FAIL: camgirls performers HTTP $CODE2"
  FAIL=$((FAIL + 1))
fi
echo

echo "--- Cron still installed ---"
NCRON=$(ls /etc/cron.d/masternoder* 2>/dev/null | wc -l | tr -d ' ')
if [[ "${NCRON:-0}" -ge 1 ]]; then
  echo "PASS: $NCRON masternoder cron.d file(s)"
  PASS=$((PASS + 1))
else
  warn "No /etc/cron.d/masternoder* files — re-run mn2_next_ops_remote.py --optionals"
fi
echo

echo "--- .env and wallet datadir ---"
[[ -f "$WEB_ROOT/.env" ]] && echo "PASS: .env present" && PASS=$((PASS + 1)) || { echo "FAIL: .env missing"; FAIL=$((FAIL + 1)); }
[[ -d "$WEB_ROOT/config" ]] && echo "PASS: config/ present" && PASS=$((PASS + 1)) || { echo "FAIL: config/ missing"; FAIL=$((FAIL + 1)); }
echo

echo "=== Summary: $PASS passed, $FAIL failed, $WARN warnings ==="
echo
if [[ "$FAIL" -gt 0 ]]; then
  echo "Recovery hints:"
  echo "  systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001"
  echo "  systemctl restart masternoder2d"
  echo "  cd $WEB_ROOT && bash scripts/uwsgi_diagnose_server.sh"
  echo "From PC: python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking"
  exit 1
fi

echo "Local checks OK. From PC run public verify:"
echo "  python scripts/camgirls_post_deploy_verify.py --base-url https://masternoder.dk"
echo "  python scripts/shop_v4_production_smoke.py --full-line"
exit 0
