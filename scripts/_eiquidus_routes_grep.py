#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
grep -rn 'getdistribution\|getrichlist\|router.get' /var/www/explorer/routes/index.js | head -60
echo '--- ext router ---'
grep -rn 'router\|getdistribution\|richlist' /var/www/explorer/routes/ext.js 2>/dev/null | head -40
echo '--- app.js routes mount ---'
grep -n 'ext\|api\|routes' /var/www/explorer/app.js | head -30
echo '--- _explorer_http_get ---'
grep -n '_explorer_http_get\|def rich_list\|getrichlist\|getdistribution' /var/www/html/backend/services/mn2_explorer_data.py | head -30
sed -n '350,470p' /var/www/html/backend/services/mn2_explorer_data.py
ENDSCRIPT"""

def main():
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=60)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

if __name__ == "__main__":
    main()
