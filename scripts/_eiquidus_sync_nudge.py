#!/usr/bin/env python3
"""Nudge eiquidus sync — quick status + forced index update."""
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
cd /var/www/explorer
echo SYNC_PROCS
pgrep -af 'sync.js' || echo none
echo CRON_LOG
tail -8 tmp/cron_index.log 2>/dev/null || echo empty
echo MONGO
mongosh --quiet explorerdb --eval 'printjson({blocks:db.blocks.estimatedDocumentCount(),addresses:db.addresses.estimatedDocumentCount(),richlist:db.richlist.estimatedDocumentCount()})' 2>/dev/null | head -5
echo FORCE_SYNC
flock -n tmp/sync_index.lock bash -c 'cd /var/www/explorer && timeout 90 node scripts/sync.js index update 2>&1 | tail -12' || echo 'lock busy or timeout'
echo AJAX
curl -sS -m 8 -o /dev/null -w '%{http_code}\n' -H 'Host: camgirls.masternoder.dk' http://127.0.0.1/ext/getlasttxsajax/0
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=150)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))

    print("\n--- health ---")
    with urllib.request.urlopen("https://masternoder.dk/api/mn2/health", timeout=35) as r:
        d = json.loads(r.read().decode())
    print("status:", d.get("status"))
    rl = (((d.get("components") or {}).get("explorer_probe") or {}).get("detail") or {}).get("checks", {}).get("rich_list", {})
    print("rich_list:", rl.get("ok"), rl.get("note", "")[:100])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
