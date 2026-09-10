#!/usr/bin/env python3
"""Final production status after MN2 recovery."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== DAEMON STATUS =='
echo "masternoder2d: $(systemctl is-active masternoder2d)"
echo "profit-daemon: $(systemctl is-active masternoder-profit-daemon.service)"
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -sS -m 10 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/
echo
echo '== EXPLORER LOCAL =='
curl -sS -m 15 http://127.0.0.1:5000/api/mn2/explorer/status 2>/dev/null | head -c 800
echo
echo '== RICHLIST =='
curl -sS -m 12 'http://127.0.0.1:3000/ext/getrichlist?page=0' 2>/dev/null | head -c 300
echo
echo '== CRON exchange files =='
ls /etc/cron.d/*exchange* 2>/dev/null
echo '== MEM =='
free -h | head -2
echo '== journal mn2 last 5 =='
journalctl -u masternoder2d --no-pager -n 5 2>/dev/null
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=90)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))

    print("\n=== PUBLIC ===")
    url = "https://masternoder.dk/api/mn2/explorer/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FinalCheck/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read().decode())
        c = d.get("checks") or {}
        print(f"status={d.get('status')}")
        print(f"rpc={c.get('rpc')}")
        print(f"rich_list={c.get('rich_list')}")
    except Exception as exc:
        print(f"FAIL: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
