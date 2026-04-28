"""Debug why agents return empty."""
import paramiko, os, json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
USER_ID = "user_b4984c3befca47a7"

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== user_agent_skills file location ===")
print(run(ssh, f"find /var/www/html/logs -name '{USER_ID}.json' 2>/dev/null"))
print(run(ssh, f"ls /var/www/html/logs/ 2>/dev/null"))

print("\n=== agent_progress fallback dir ===")
print(run(ssh, "ls /var/www/html/logs/agent_progress/ 2>/dev/null || echo 'empty'"))

print("\n=== Check what user_agent_skills sees ===")
r = run(ssh, f"""cd /var/www/html && python3 -c "
import sys; sys.path.insert(0,'.')
from backend.services.user_agent_skills import user_agent_skills
data = user_agent_skills.get_user_skills('{USER_ID}')
import json; print(json.dumps(data, indent=2))
" 2>&1""", timeout=20)
print(r[:1000])

print("\n=== Check agent_db_service.get_user_agents ===")
r2 = run(ssh, f"""cd /var/www/html && python3 -c "
import sys; sys.path.insert(0,'.')
from backend.services.agent_db_service import agent_db_service
result = agent_db_service.get_user_agents('{USER_ID}')
import json; print('agents count:', len(result))
for ag in result: print(' ', ag.get('name'), ag.get('level'), ag.get('xp'))
" 2>&1""", timeout=20)
print(r2[:1000])

print("\n=== Check agent_progress fallback file ===")
print(run(ssh, f"cat /var/www/html/logs/agent_progress/{USER_ID}.json 2>/dev/null || echo 'no file'"))

ssh.close()
