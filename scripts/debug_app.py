import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=40):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()

# Full create_app test - see all routes after registration
o, e = run("""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()
# Find all routes with 'overview' or 'system' in URL
hits = []
for r in app.url_map.iter_rules():
    if 'overview' in str(r):
        hits.append(str(r) + ' -> ' + r.endpoint)
print('OVERVIEW_ROUTES:', hits)

# Check which blueprints are registered
bps = list(app.blueprints.keys())
print('MISSING IN BLUEPRINTS:', 'missing_endpoints' in bps)

# Check the missing_endpoints bp routes
import os
if 'missing_endpoints' in app.blueprints:
    bp = app.blueprints['missing_endpoints']
    # Find all URL rules for this blueprint
    bp_rules = [str(r) for r in app.url_map.iter_rules() if r.endpoint.startswith('missing_endpoints.')]
    overview_rules = [r for r in bp_rules if 'overview' in r]
    print('MISSING_BP overview rules:', overview_rules)
    print('MISSING_BP total rules:', len(bp_rules))
" 2>&1 | grep -E "OVERVIEW|MISSING|ERROR|Traceback"
""", t=35)
print("App test:")
print(o)
if e:
    print("STDERR:", e[:200])
ssh.close()
