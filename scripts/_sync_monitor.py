#!/usr/bin/env python3
"""Monitor MN2 sync progress and verify public endpoints."""
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
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
echo "== daemon =="
systemctl is-active masternoder2d
echo "== block samples (30s apart) =="
for n in 1 2 3; do
  BC=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null)
  INFO=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockchaininfo","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; d=json.load(sys.stdin).get('result',{}); print(d.get('blocks',''), d.get('headers',''), round(float(d.get('verificationprogress',0))*100,2))" 2>/dev/null)
  echo "sample $n: block=$BC info=$INFO"
  [ "$n" -lt 3 ] && sleep 30
done
echo "== debug tail =="
tail -3 /var/www/html/config/debug.log
echo "== mem =="
free -h | head -2
ps aux --sort=-%mem | grep masternoder2d | grep -v grep | head -2
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=120)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

    print("\n=== PUBLIC ===")
    for url in (
        "https://masternoder.dk/api/mn2/network-overview",
        "https://masternoder.dk/api/mn2/balance?user_id=default_user",
        "https://masternoder.dk/api/mn2/health",
        "https://masternoder.dk/api/mn2/explorer/status",
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SyncMonitor/1.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                d = json.loads(resp.read().decode())
            if "network-overview" in url:
                daemon = d.get("daemon") or {}
                print(
                    f"network-overview: reachable={daemon.get('reachable')} "
                    f"block={d.get('block_height')} headers={daemon.get('headers')}"
                )
            elif "health" in url:
                print(f"health: status={d.get('status')}")
            elif "explorer/status" in url:
                checks = d.get("checks") or {}
                rpc = checks.get("rpc") or d.get("rpc") or {}
                print(f"explorer/status: rpc.ok={rpc.get('ok')} block={rpc.get('block_height')}")
            else:
                print(f"balance: success={d.get('success')}")
        except Exception as exc:
            print(f"{url}: FAIL {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
