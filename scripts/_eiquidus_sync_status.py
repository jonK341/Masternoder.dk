#!/usr/bin/env python3
"""Diagnose eiquidus sync progress and nudge index if stuck."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
cd /var/www/explorer
echo '== sync processes =='
pgrep -af 'sync.js' || echo none
echo '== locks =='
ls -la tmp/*.lock tmp/*.pid 2>/dev/null | head -10
echo '== cron index log tail =='
tail -25 tmp/cron_index.log 2>/dev/null || echo no_cron_index_log
echo '== sync.js help (index) =='
node scripts/sync.js index 2>&1 | head -20
echo '== index check =='
node scripts/sync.js index check 2>&1 | tail -15
echo '== mongo stats =='
mongosh --quiet --eval 'db=db.getSiblingDB("explorerdb"); print("blocks", db.blocks.countDocuments()); print("addresses", db.addresses.countDocuments()); print("richlist", db.richlist.countDocuments()); print("stats", JSON.stringify(db.stats.findOne()||{}).slice(0,200))' 2>/dev/null || echo mongo_fail
echo '== nginx ajax =='
curl -sS -m 10 -o /dev/null -w 'nginx_ajax=%{http_code}\n' -H 'Host: camgirls.masternoder.dk' http://127.0.0.1/ext/getlasttxsajax/0
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=120)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

    print("\n--- MN2 health ---")
    try:
        with urllib.request.urlopen("https://masternoder.dk/api/mn2/health", timeout=30) as r:
            d = json.loads(r.read().decode())
            print("status:", d.get("status"))
            rl = (((d.get("components") or {}).get("explorer_probe") or {}).get("detail") or {}).get("checks", {}).get("rich_list", {})
            print("rich_list:", rl)
    except Exception as e:
        print("fail:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
