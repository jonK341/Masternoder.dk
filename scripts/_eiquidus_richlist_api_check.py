#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
grep -n 'richlist\|getrich' /var/www/explorer/lib/settings.js | head -30
grep -n 'richlist\|getrich' /var/www/explorer/settings.json | head -20
echo '--- richlist HTML scrape test ---'
curl -sS -m 10 -H 'Accept: application/json' http://127.0.0.1:3000/richlist 2>/dev/null | grep -o 'a_id[^,]*' | head -3
curl -sS -m 10 http://127.0.0.1:3000/richlist 2>/dev/null | grep -c 'richlist-table\|balance-table\|address' | head -1
echo '--- api page list ---'
curl -sS -m 10 http://127.0.0.1:3000/api 2>/dev/null | grep -o '/ext/[^"< ]*' | sort -u | head -20
ENDSCRIPT"""

def main():
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=60)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

if __name__ == "__main__":
    main()
