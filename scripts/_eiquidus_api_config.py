#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
grep -rn 'getdistribution\|getrichlist\|getmoneysupply' /var/www/explorer/plugins /var/www/explorer/lib /var/www/explorer/settings.json 2>/dev/null | head -40
echo '--- public_apis ext ---'
python3 -c "
import json
s=json.load(open('/var/www/explorer/settings.json'))
pa=s.get('public_apis',{}).get('ext',{})
for k,v in pa.items():
    if 'rich' in k.lower() or 'distrib' in k.lower() or 'address' in k.lower() or 'money' in k.lower():
        print(k, v)
"
echo '--- _explorer_http_get impl ---'
sed -n '198,250p' /var/www/html/backend/services/mn2_explorer_data.py
echo '--- explorer config ---'
python3 -c "
import json, os
sys_path='/var/www/html/data/mn2_explorer_config.json'
if os.path.isfile(sys_path):
    print(open(sys_path).read()[:800])
else:
    print('no config', sys_path)
"
ENDSCRIPT"""

def main():
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=60)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

if __name__ == "__main__":
    main()
