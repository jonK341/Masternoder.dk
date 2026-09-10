#!/usr/bin/env python3
"""Restart camgirls.masternoder.dk eiquidus explorer (PM2 + port 3000)."""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '========== EXPLORER RESTART =========='
date -u

EXPLORER_DIR=""
for d in /var/www/explorer /root/Iexplorer /root/explorer ~/Iexplorer; do
  if [ -f "$d/package.json" ] || [ -f "$d/settings.json" ]; then
    EXPLORER_DIR="$d"
    break
  fi
done
echo "explorer_dir=${EXPLORER_DIR:-NOT_FOUND}"

echo '== before =='
pm2 list 2>/dev/null || echo 'pm2 missing'
ss -tlnp 2>/dev/null | grep ':3000' || echo 'port 3000: closed'
curl -sS -m 5 -o /dev/null -w 'local_ext=%{http_code}\n' http://127.0.0.1:3000/ext/getmoneysupply 2>/dev/null || echo 'local_ext=000'

if [ -z "$EXPLORER_DIR" ]; then
  echo 'FAIL: explorer directory not found'
  exit 2
fi

cd "$EXPLORER_DIR" || exit 3
echo "cwd=$(pwd)"
ls -la bin/cluster 2>/dev/null || true
chmod +x ./bin/cluster 2>/dev/null || true

# Ensure mongod up (eiquidus depends on Mongo)
systemctl is-active mongod 2>/dev/null || systemctl start mongod 2>/dev/null
sleep 2
systemctl is-active mongod 2>/dev/null

# Restart via PM2 (eiquidus expects bin/cluster, not bare app.js)
pm2 delete explorer 2>/dev/null
if [ -x ./bin/cluster ]; then
  pm2 start ./bin/cluster --name explorer --node-args="--stack-size=10000" -- 1
elif [ -f app.js ]; then
  pm2 start app.js --name explorer --node-args="--stack-size=10000"
else
  pm2 start npm --name explorer -- start
fi
pm2 save 2>/dev/null
sleep 15

echo '== after =='
pm2 list 2>/dev/null
ss -tlnp 2>/dev/null | grep ':3000' || echo 'port 3000: still closed'
curl -sS -m 12 -o /dev/null -w 'local_ext=%{http_code}\n' http://127.0.0.1:3000/ext/getmoneysupply 2>/dev/null || echo 'local_ext=000'
curl -sS -m 12 -o /dev/null -w 'nginx_ajax=%{http_code}\n' -H 'Host: camgirls.masternoder.dk' http://127.0.0.1/ext/getlasttxsajax/0 2>/dev/null || echo 'nginx_ajax=000'
curl -sS -m 12 -o /dev/null -w 'nginx_home=%{http_code}\n' -H 'Host: camgirls.masternoder.dk' http://127.0.0.1/ 2>/dev/null || echo 'nginx_home=000'
pm2 logs explorer --lines 8 --nostream 2>/dev/null | tail -12
echo '== error log =='
tail -15 /root/.pm2/logs/explorer-error.log 2>/dev/null
echo '== settings port =='
grep -E '"port"|webserver' settings.json 2>/dev/null | head -3
ENDSCRIPT"""


def _public_check(url: str) -> tuple[int, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ExplorerRestartCheck/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.getcode(), "ok"
    except urllib.error.HTTPError as e:
        return e.code, "http_error"
    except Exception as exc:
        return -1, str(exc)[:120]


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=180)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    if err.strip():
        sys.stdout.buffer.write(b"STDERR: ")
        sys.stdout.buffer.write(err[:600].encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")

    print("\n--- Public HTTPS ---")
    for label, url in [
        ("home", "https://camgirls.masternoder.dk/"),
        ("ajax", "https://camgirls.masternoder.dk/ext/getlasttxsajax/0"),
        ("supply", "https://camgirls.masternoder.dk/ext/getmoneysupply"),
        ("mn2_health", "https://masternoder.dk/api/mn2/health"),
    ]:
        code, detail = _public_check(url)
        print(f"  {label}: HTTP {code} ({detail})")

    ok = "local_ext=200" in out or "nginx_home=200" in out
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
