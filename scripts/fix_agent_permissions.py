"""Fix permissions for agent_progress logs directory."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

# Fix permissions - uWSGI runs as www-data
print("=== Fix permissions ===")
print(run(ssh, "chown -R www-data:www-data /var/www/html/logs/agent_progress && chmod -R 775 /var/www/html/logs/agent_progress && echo ok"))
print(run(ssh, "chown -R www-data:www-data /var/www/html/logs/user_agent_skills && chmod -R 775 /var/www/html/logs/user_agent_skills && echo ok"))
# Also fix the whole logs directory
print(run(ssh, "chown -R www-data:www-data /var/www/html/logs && chmod -R 775 /var/www/html/logs && echo logs_fixed"))

# Retest
print("\n=== Retest record + feed ===")
print(run(ssh, """curl -s -X POST 'http://127.0.0.1:5000/vidgenerator/api/agents/record-action' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"default_user","agent_id":"content_generator_agent","action":"generate_video","skill":"generate_video","xp_gained":30}' 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print('recorded:', d.get('success'))" """))

import time; time.sleep(1)

print(run(ssh, """curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/activity-feed?user_id=default_user&limit=5' 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); acts=d.get('activities',[]); print('activities:', len(acts)); [print(' ', a.get('label'), '+', a.get('xp_gained'), 'XP') for a in acts[:3]]" """))

print("\n=== Check fallback file ===")
print(run(ssh, "cat /var/www/html/logs/agent_progress/default_user.json 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print('agents:', list(d.get('agents',{}).keys()), 'activities:', len(d.get('activity',[])))\""))

ssh.close()
print("Done.")
