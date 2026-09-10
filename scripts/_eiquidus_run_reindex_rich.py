#!/usr/bin/env python3
"""Run eiquidus index reindex-rich and verify MN2 health."""
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
pkill -f 'sync.js' 2>/dev/null || true
sleep 2
rm -f tmp/index.pid tmp/sync_index.lock 2>/dev/null

echo '== reindex-rich (300s max) =='
timeout 300 node scripts/sync.js index reindex-rich 2>&1 | tail -40

echo '== distribution still ok? =='
curl -sS -m 10 http://127.0.0.1:3000/ext/getdistribution | head -c 200; echo

echo '== richlist page db check =='
timeout 30 node -e "
const db=require('./lib/database');
const settings=require('./lib/settings');
db.connect(function(){
  db.check_richlist(settings.coin.name, function(exists){
    console.log('richlist_exists', exists);
    db.get_richlist(settings.coin.name, function(rl){
      if(!rl){ console.log('get_richlist null'); process.exit(0); }
      console.log('balance_count', (rl.balance||[]).length);
      if((rl.balance||[]).length) console.log('top1', JSON.stringify(rl.balance[0]));
      process.exit(0);
    });
  });
});
" 2>&1

echo '== probe getrichlist paths again =='
for p in '/ext/getrichlist?limit=3' '/getrichlist?limit=3'; do
  code=$(curl -sS -m 8 -o /tmp/p.txt -w '%{http_code}' "http://127.0.0.1:3000$p")
  echo "$code $p :: $(head -c 120 /tmp/p.txt | tr '\n' ' ')"
done

echo '== flask rich_list direct =='
cd /var/www/html
python3 - <<'PY'
try:
    from backend.services import mn2_explorer_data as ed
    rows = ed.rich_list(limit=3)
    print('rich_list rows', rows)
    st = ed.explorer_status()
    print('explorer_status', st.get('status'))
    print('rich_check', (st.get('checks') or {}).get('rich_list'))
except Exception as e:
    print('err', e)
PY
ENDSCRIPT"""


def _health() -> dict:
    try:
        req = urllib.request.Request("https://masternoder.dk/api/mn2/health", headers={"User-Agent": "ReindexRich/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=320)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

    print("\n--- MN2 health ---")
    h = _health()
    print("status:", h.get("status"))
    probe = (h.get("components") or {}).get("explorer_probe") or {}
    rl = ((probe.get("detail") or {}).get("checks") or {}).get("rich_list") or {}
    print("rich_list:", rl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
