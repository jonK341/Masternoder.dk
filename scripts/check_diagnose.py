import paramiko

HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=20)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

# Check if diagnose is in the ROOT file
o = run("grep -c 'ai-diagnose' /var/www/html/backend/routes/agent_automation_routes.py")
print("ROOT agent_automation has ai-diagnose:", o)

# Check the app URL map
o = run(r"""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()
routes = [str(r) for r in app.url_map.iter_rules() if 'diagnose' in str(r)]
print('DIAGNOSE routes:', routes)
strat = [str(r) for r in app.url_map.iter_rules() if 'ai-strategy' in str(r)]
print('STRATEGY routes:', strat[:2])
" 2>&1 | grep -E "DIAGNOSE|STRATEGY"
""", t=30)
print("App map check:", o)

# Try GET request directly on localhost
o = run("curl -s 'http://localhost:5000/vidgenerator/api/agent/automation/ai-diagnose' --max-time 10 -w ' STATUS:%{http_code}'")
print("Localhost test:", o[:200])

import os
ssh.close()
