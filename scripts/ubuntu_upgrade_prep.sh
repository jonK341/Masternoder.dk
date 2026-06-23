#!/usr/bin/env bash
# Pre-Ubuntu-release-upgrade checklist for masternoder.dk production.
# Run ON THE SERVER as root before: do-release-upgrade / apt full-upgrade + reboot.
#
# Usage:
#   cd /var/www/html && sudo bash scripts/ubuntu_upgrade_prep.sh
#   cd /var/www/html && sudo bash scripts/ubuntu_upgrade_prep.sh --backup-only
#
set -euo pipefail

WEB_ROOT="${WEB_ROOT:-/var/www/html}"
BACKUP_DIR="${BACKUP_DIR:-/root/mn2-pre-ubuntu-upgrade}"
BACKUP_ONLY=0
[[ "${1:-}" == "--backup-only" ]] && BACKUP_ONLY=1

stamp() { date -u +%Y%m%dT%H%MZ; }
TS="$(stamp)"

echo "=== MN2 Ubuntu upgrade prep ($TS) ==="
echo "WEB_ROOT=$WEB_ROOT"
echo "BACKUP_DIR=$BACKUP_DIR"
echo

if [[ "$(id -u)" -ne 0 ]]; then
  echo "[FAIL] Run as root (sudo)."
  exit 1
fi

mkdir -p "$BACKUP_DIR"
ARCHIVE="$BACKUP_DIR/mn2-critical-${TS}.tar.gz"

echo "--- Disk space (need >= 5 GB free on / and /var) ---"
df -h / /var /var/www 2>/dev/null || df -h /
AVAIL_KB=$(df -k / | awk 'NR==2 {print $4}')
if [[ "${AVAIL_KB:-0}" -lt 5242880 ]]; then
  echo "[WARN] Less than 5 GB free on /. Run: python scripts/server_cleanup_scan.py --clean (from PC) or free disk before upgrade."
else
  echo "[OK] Root filesystem has enough headroom for upgrade."
fi
echo

echo "--- Current OS ---"
if [[ -f /etc/os-release ]]; then
  grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release || true
fi
uname -r
echo

echo "--- Stopping app workers (daemon keeps running until reboot) ---"
for u in uwsgi-vidgenerator uwsgi-vidgenerator-5001 python-proxy; do
  if systemctl is-active --quiet "$u" 2>/dev/null; then
    echo "Stopping $u ..."
    systemctl stop "$u" || true
  fi
done
# MN2 daemon: optional stop for clean wallet flush (upgrade reboot will stop it anyway)
if systemctl is-active --quiet masternoder2d 2>/dev/null; then
  echo "masternoder2d is active — leaving running (wallet flush on stop is optional)."
  echo "  To stop before backup: systemctl stop masternoder2d"
fi
echo

echo "--- Creating critical backup tarball ---"
# Wallet + app secrets + data — NEVER skip config/ or .env
tar -czf "$ARCHIVE" \
  -C "$WEB_ROOT" \
  --ignore-failed-read \
  .env \
  config \
  data \
  cron \
  systemd \
  uwsgi.ini uwsgi_common.ini uwsgi_5001.ini \
  2>/dev/null || true

if [[ -f "$ARCHIVE" ]]; then
  ls -lh "$ARCHIVE"
  sha256sum "$ARCHIVE" | tee "$ARCHIVE.sha256"
  echo "[OK] Backup: $ARCHIVE"
else
  echo "[FAIL] Backup tarball not created."
  exit 1
fi

# nginx + systemd unit copies (outside WEB_ROOT)
NGINX_SNAP="$BACKUP_DIR/nginx-sites-${TS}.tar.gz"
if [[ -d /etc/nginx ]]; then
  tar -czf "$NGINX_SNAP" /etc/nginx/sites-enabled /etc/nginx/sites-available 2>/dev/null || true
  echo "[OK] Nginx snapshot: $NGINX_SNAP"
fi
UNITS_SNAP="$BACKUP_DIR/systemd-units-${TS}.txt"
{
  for u in uwsgi-vidgenerator uwsgi-vidgenerator-5001 masternoder2d python-proxy nginx; do
    echo "=== $u ==="
    systemctl cat "$u.service" 2>/dev/null || echo "(no unit $u)"
    echo
  done
} > "$UNITS_SNAP" 2>/dev/null || true
echo "[OK] systemd unit dump: $UNITS_SNAP"

echo
echo "--- Enabled cron jobs ---"
ls -la /etc/cron.d/masternoder* 2>/dev/null || echo "(no masternoder cron.d files)"
crontab -l 2>/dev/null | head -20 || true
echo

echo "--- Package hold list (note for post-upgrade) ---"
apt-mark showhold 2>/dev/null || true
echo

echo "--- Record versions ---"
{
  echo "date=$TS"
  python3 --version 2>/dev/null || true
  uwsgi --version 2>/dev/null || true
  nginx -v 2>&1 || true
  /opt/masternoder2d/masternoder2d -version 2>/dev/null || true
} | tee "$BACKUP_DIR/versions-${TS}.txt"
echo

if [[ "$BACKUP_ONLY" -eq 1 ]]; then
  echo "=== Backup-only complete ==="
  exit 0
fi

echo "--- Pre-upgrade apt hygiene (optional, safe) ---"
apt-get update -qq || true
apt-get clean || true
echo

echo "=== PREP COMPLETE ==="
echo
echo "Next steps (as root):"
echo "  1. Copy backup off-server if possible:"
echo "       scp $ARCHIVE user@backup-host:~/"
echo "  2. Upgrade Ubuntu:"
echo "       apt install update-manager-core"
echo "       do-release-upgrade   # or: apt full-upgrade && reboot"
echo "  3. After reboot, on server:"
echo "       cd $WEB_ROOT && sudo bash scripts/ubuntu_upgrade_post_verify.sh"
echo "  4. From PC:"
echo "       python scripts/camgirls_post_deploy_verify.py --base-url https://masternoder.dk"
echo "       python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking"
echo
echo "Restart app now (if you stopped uwsgi and are NOT upgrading yet):"
echo "  systemctl start uwsgi-vidgenerator uwsgi-vidgenerator-5001"
