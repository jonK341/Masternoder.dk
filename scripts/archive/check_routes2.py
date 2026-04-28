import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password='eD)2[K+[S#m_#$3!', timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

o, e = run(r"""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html')
from src.app import create_app
app = create_app()
# find overview routes
hits = []
for r in app.url_map.iter_rules():
    if 'system' in str(r) or 'overview' in str(r):
        hits.append(str(r) + ' -> ' + r.endpoint)
print('OVERVIEW_ROUTES:', hits)
# also check the auto_fix module
try:
    from backend.services.auto_fix_endpoints import auto_fix_endpoints as ae
    print('AUTO_FIX_TYPE:', type(ae).__name__)
    print('AUTO_FIX_KNOWN:', '/api/system/overview' in str(ae.__dict__))
except Exception as ex:
    print('AUTO_FIX_ERR:', ex)
" 2>&1 | grep -E "OVERVIEW_ROUTES|AUTO_FIX"
""", t=30)
print("Output:", o)
print("Stderr:", e[:200] if e else "none")
ssh.close()
