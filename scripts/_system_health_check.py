#!/usr/bin/env python3
"""One-shot system health check (SSH + public HTTPS)."""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '========== SYSTEM HEALTH CHECK =========='
echo '== Host / uptime =='
hostname; uname -r; uptime
echo
echo '== Disk / memory =='
df -h / /var/www 2>/dev/null | head -5
free -h | head -2
echo
echo '== systemd services =='
for s in nginx uwsgi-vidgenerator python-proxy uwsgi masternoder2d pm2-root docker mn2-fleet-autostart; do
  st=$(systemctl is-active "$s" 2>/dev/null)
  en=$(systemctl is-enabled "$s" 2>/dev/null)
  printf '  %-24s active=%-10s enabled=%s\n' "$s" "$st" "$en"
done
echo
echo '== failed units =='
systemctl --failed --no-pager 2>/dev/null | head -15
echo
echo '== listeners =='
ss -tlnp 2>/dev/null | grep -E ':5000|:80 |:443 |:9332 ' || true
echo
echo '== nginx config test =='
nginx -t 2>&1 | tail -2
echo
echo '== uWSGI / app (localhost :5000) =='
for p in / /api/health /api/version /api/generator/test; do
  c=$(curl -sS -m 12 -o /dev/null -w '%{http_code}' "http://127.0.0.1:5000$p" 2>/dev/null || echo 000)
  echo "  $p -> HTTP $c"
done
echo
echo '== MN2 daemon =='
if systemctl is-active --quiet masternoder2d; then
  /opt/masternoder2d/masternoder2-cli -datadir=/root/.masternoder2 getblockcount 2>/dev/null || echo '  (cli failed)'
else
  echo '  masternoder2d inactive'
fi
echo
echo '== pm2 =='
pm2 status 2>/dev/null | head -10 || echo '  pm2 not available'
echo
echo '== docker =='
docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | head -6 || echo '  no containers'
echo
echo '== Node / Playwright =='
node -v 2>/dev/null; npm -v 2>/dev/null
CH=$(ls -d /root/.cache/ms-playwright/chromium-* 2>/dev/null | head -1)
if [ -n "$CH" ]; then
  echo "chromium: $CH"
  ldd "$CH/chrome-linux/chrome" 2>&1 | grep 'not found' | head -10 || echo '  (no missing shared libs)'
else
  echo '  no chromium cache'
fi
if [ -d /root/my-playwright-project ]; then
  echo '== Playwright smoke test =='
  cd /root/my-playwright-project && npx playwright test --project=chromium 2>&1 | tail -12
fi
echo
echo '== recent uwsgi log =='
tail -3 /var/www/html/uwsgi.log 2>/dev/null
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=180)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    print(out)
    if err.strip():
        print("STDERR:", err[:500])

    print()
    print("========== PUBLIC HTTPS CHECKS ==========")
    base = "https://masternoder.dk"
    paths = [
        "/",
        "/api/health",
        "/api/version",
        "/generator",
        "/api/camgirls/performers?user_id=default_user",
    ]
    ok = True
    for p in paths:
        url = base + p
        try:
            r = urllib.request.urlopen(url, timeout=25)
            print(f"  {p} -> HTTP {r.status}")
        except Exception as exc:
            ok = False
            print(f"  {p} -> FAIL: {exc}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
