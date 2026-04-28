import paramiko, time

HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=20)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

# Wait for active
for i in range(8):
    s = run("systemctl is-active uwsgi-vidgenerator", t=5)
    print(f"  Service: {s}")
    if s == "active":
        break
    time.sleep(5)

# Get error body
o = run("curl -s 'https://masternoder.dk/vidgenerator/api/agent/automation/ai-diagnose' --max-time 15", t=20)
print("\nResponse body:", o[:400])

# Also check the Python syntax of the new missing_endpoints
o = run("python3 -m py_compile /var/www/html/backend/routes/missing_endpoints_routes.py && echo 'OK' || echo 'SYNTAX ERROR'")
print("Syntax check:", o)

# Check function definition in ROOT file
o = run("grep -A 3 'def agent_ai_diagnose_compat' /var/www/html/backend/routes/missing_endpoints_routes.py | head -5")
print("Function def:", o)

import os
ssh.close()
