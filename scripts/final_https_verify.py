"""Final HTTPS verification of all agent endpoints."""
import paramiko, os, json

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

print("=== HTTPS /api/agents/my-agents (default_user) ===")
r = run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user' | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(a.get('name'), 'L'+str(a.get('level')), str(a.get('xp'))+'xp', str(a.get('total_actions'))+'acts') for a in d.get('agents',[])]\"")
print(r)

print("\n=== HTTPS /api/agents/activity-feed (default_user) ===")
r2 = run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/activity-feed?user_id=default_user&limit=3' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('activities:', len(d.get('activities',[])))\"")
print(r2)

print("\n=== Profile page loads correctly ===")
r3 = run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/profile/' | grep -c 'agent-progress-grid\\|Agent Progress'")
print("'Agent Progress' section found:", r3, "times in HTML")

print("\n=== Check all wired point events (video generation) ===")
r4 = run(ssh, "grep -c 'agent_db_service\\|record_agent_activity' /var/www/html/backend/services/video_generator_service.py 2>/dev/null")
print("agent_db_service refs in video_generator_service:", r4)

print("\n=== Check quest wire ===")
r5 = run(ssh, "grep -c 'agent_db_service\\|record_agent_activity' /var/www/html/backend/routes/quest_routes.py 2>/dev/null")
print("agent_db_service refs in quest_routes:", r5)

print("\n=== Check hunters game wire ===")
r6 = run(ssh, "grep -c 'agent_db_service\\|record_agent_activity' /var/www/html/backend/routes/hunters_game.py 2>/dev/null")
print("agent_db_service refs in hunters_game:", r6)

ssh.close()
print("\nAll checks complete!")
