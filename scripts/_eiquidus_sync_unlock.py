#!/usr/bin/env python3
"""Kill stuck eiquidus sync lock and run clean index update."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
cd /var/www/explorer
echo '== kill stuck sync =='
pgrep -af 'sync.js' || true
pkill -f 'sync.js index check' 2>/dev/null || true
sleep 2
rm -f tmp/index.pid tmp/sync_index.lock 2>/dev/null
pgrep -af 'sync.js' || echo none

echo '== index update (foreground 180s max) =='
timeout 180 node scripts/sync.js index update 2>&1 | tail -25

echo '== cron log tail =='
tail -5 tmp/cron_index.log 2>/dev/null

echo '== richlist probe =='
curl -sS -m 12 http://127.0.0.1:3000/ext/getrichlist?page=0 2>/dev/null | head -c 250; echo
curl -sS -m 12 http://127.0.0.1:3000/ext/getaddresslist?page=0 2>/dev/null | head -c 250; echo
ENDSCRIPT"""


def _health() -> dict:
    try:
        req = urllib.request.Request("https://masternoder.dk/api/mn2/health", headers={"User-Agent": "SyncFix/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=200)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

    print("\n--- health (immediate) ---")
    h = _health()
    _print_health(h)

    print("\n--- health (after 20s) ---")
    time.sleep(20)
    h2 = _health()
    _print_health(h2)
    return 0


def _print_health(h: dict) -> None:
    print("status:", h.get("status"), "| success:", h.get("success"))
    probe = (h.get("components") or {}).get("explorer_probe") or {}
    rl = ((probe.get("detail") or {}).get("checks") or {}).get("rich_list") or {}
    print("rich_list:", rl)
    print("supply_ok:", ((probe.get("detail") or {}).get("iquidus") or {}).get("supply_ok"))


if __name__ == "__main__":
    raise SystemExit(main())
