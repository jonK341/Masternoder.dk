import paramiko

HOST, USER, PASS = "masternoder.dk", "root", "eD)2[K+[S#m_#$3!"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=20)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

# Hit it 3 times to see if it's consistent
for i in range(3):
    code = run("curl -s -o /dev/null -w '%{http_code}' 'https://masternoder.dk/vidgenerator/api/agent/automation/ai-diagnose' --max-time 12", t=20)
    print(f"  attempt {i+1}: {code}")

# Check agent_automation blueprint registration
o = run(r"""python3 -c "
import sys, os
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()
diag = [str(r) + ' -> ' + r.endpoint for r in app.url_map.iter_rules() if 'diagnose' in str(r)]
agent_bps = [k for k in app.blueprints.keys() if 'agent' in k.lower() or 'automation' in k.lower()]
print('DIAG:', diag)
print('AGENT BPS:', agent_bps)
" 2>&1 | grep -E "DIAG|AGENT"
""", t=30)
print("\nApp check:", o)

# Check if the VIDGEN agent_automation_routes.py has diagnose
o = run("grep -c 'ai-diagnose' /var/www/html/vidgenerator/backend/routes/agent_automation_routes.py 2>/dev/null || echo 0")
print("VIDGEN agent_automation ai-diagnose count:", o)

# Check ROOT agent_automation_routes.py
o = run("grep -c 'ai-diagnose' /var/www/html/backend/routes/agent_automation_routes.py 2>/dev/null || echo 0")
print("ROOT agent_automation ai-diagnose count:", o)

# Check if maybe there are two agent_automation_bp registrations with same endpoint conflict
o = run("grep -c 'agent_automation_bp' /var/www/html/backend/register_blueprints.py")
print("register_blueprints agent_automation_bp count:", o)

ssh.close()
