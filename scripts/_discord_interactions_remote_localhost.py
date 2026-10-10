"""Remote localhost probe for Discord interactions (no secrets printed)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_PY = r"""
import json, os, urllib.request

def load_env(path):
    if not os.path.isfile(path):
        return
    for line in open(path, encoding='utf-8'):
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env('/var/www/html/.env')
pk=bool((os.environ.get('DISCORD_PUBLIC_KEY') or '').strip())
print('public_key_set', pk)

body=json.dumps({'type':1}).encode()
req=urllib.request.Request(
    'http://127.0.0.1:5000/api/discord/interactions',
    data=body,
    headers={'Content-Type':'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('unsigned_status', resp.status)
        print('unsigned_body', resp.read()[:120].decode())
except Exception as e:
    if hasattr(e, 'code'):
        print('unsigned_status', e.code)
        print('unsigned_body', e.read()[:120].decode())
    else:
        print('error', type(e).__name__, str(e)[:120])

try:
    import cryptography
    print('cryptography_ok', cryptography.__version__)
except Exception as e:
    print('cryptography_ok', False, type(e).__name__)
"""


def main() -> None:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("ssh auth:", auth)
    _, stdout, stderr = ssh.exec_command(f"python3 - <<'PY'\n{REMOTE_PY}\nPY", timeout=30)
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print("stderr:", err[:300])
    ssh.close()


if __name__ == "__main__":
    main()
