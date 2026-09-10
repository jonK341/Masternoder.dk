#!/usr/bin/env python3
"""Build eiquidus rich list and verify MN2 health."""
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
echo '== sync.js topics =='
node scripts/sync.js 2>&1 | head -25
echo '== try addresslist / richlist endpoints =='
curl -sS -m 10 http://127.0.0.1:3000/ext/getaddresslist?page=0 | head -c 200; echo
curl -sS -m 10 http://127.0.0.1:3000/ext/getrichlist?page=0 | head -c 200; echo
echo '== mongo counts =='
mongosh --quiet explorerdb --eval 'printjson({blocks:db.blocks.estimatedDocumentCount(),addresses:db.addresses.estimatedDocumentCount(),richlist:db.richlist.estimatedDocumentCount(),stats:db.stats.findOne()})' 2>/dev/null | head -8
echo '== run index update 120s (addresses/richlist) =='
flock -n tmp/sync_index.lock bash -c 'cd /var/www/explorer && timeout 120 node scripts/sync.js index update 2>&1 | tail -20' || echo lock_busy
echo '== mongo after =='
mongosh --quiet explorerdb --eval 'printjson({addresses:db.addresses.estimatedDocumentCount(),richlist:db.richlist.estimatedDocumentCount()}); if(db.richlist.estimatedDocumentCount()>0) printjson(db.richlist.find().limit(2).toArray())' 2>/dev/null | head -12
ENDSCRIPT"""


def _health() -> dict:
    try:
        req = urllib.request.Request("https://masternoder.dk/api/mn2/health", headers={"User-Agent": "RichListCheck/1.0"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=180)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

    h = _health()
    print("\n--- MN2 health ---")
    print("status:", h.get("status"))
    probe = (h.get("components") or {}).get("explorer_probe") or {}
    rl = ((probe.get("detail") or {}).get("checks") or {}).get("rich_list") or {}
    print("rich_list ok:", rl.get("ok"), "| synced:", rl.get("index_synced"), "| count:", rl.get("sample_count"))
    print("note:", rl.get("note", ""))
    print("supply_ok:", ((probe.get("detail") or {}).get("iquidus") or {}).get("supply_ok"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
