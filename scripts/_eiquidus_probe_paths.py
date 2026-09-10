#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== eiquidus API routes for richlist =='
grep -rn 'getrichlist\|richlist' /var/www/explorer/routes/api.js /var/www/explorer/routes/ext.js /var/www/explorer/routes 2>/dev/null | head -40

echo '== probe richlist paths =='
for p in \
  '/ext/getrichlist?limit=5' \
  '/getrichlist?limit=5' \
  '/ext/getrichlistdata?limit=5' \
  '/ext/getrichlistbalance?limit=5' \
  '/ext/getdistribution' \
  ; do
  code=$(curl -sS -m 8 -o /tmp/p.txt -w '%{http_code}' "http://127.0.0.1:3000$p")
  sample=$(head -c 150 /tmp/p.txt | tr '\n' ' ')
  echo "$code $p :: $sample"
done

echo '== settings richlist =='
python3 -c "import json; s=json.load(open('/var/www/explorer/settings.json')); print('richlist_page', s.get('richlist_page',{}).get('enabled')); print('db keys', list((s.get('dbsettings') or s.get('database') or {}).keys()))"

echo '== dbsettings =='
python3 -c "import json; s=json.load(open('/var/www/explorer/settings.json')); import pprint; pprint.pp(s.get('dbsettings',{}))" 2>/dev/null | head -15

echo '== sync richlist subcommand =='
grep -n richlist /var/www/explorer/scripts/sync.js | head -20

echo '== app probe via flask =='
curl -sS -m 10 http://127.0.0.1:5000/api/mn2/explorer/rich-list?limit=3 2>/dev/null | head -c 400; echo
ENDSCRIPT"""

def main():
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=90)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

if __name__ == "__main__":
    main()
