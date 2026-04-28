import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# Simple: just grep the URL map
test_cmd = r"""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html')
from src.app import create_app
app = create_app()
found = [str(r)+' -> '+r.endpoint for r in app.url_map.iter_rules() if 'overview' in str(r) or 'overview' in r.endpoint]
print('FOUND:', found)
bp_names = list(app.blueprints.keys())
has_missing = 'missing_endpoints' in bp_names
has_sysov = 'system_overview' in bp_names
print('missing_endpoints registered:', has_missing)
print('system_overview registered:', has_sysov)
" 2>&1 | tail -10"""

import os
o, e = run(test_cmd, t=30)
print("Result:", o)
print("Err:", e[:200] if e else "(none)")
ssh.close()
