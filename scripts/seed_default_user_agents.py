"""Seed default_user with agent assignments for demo purposes."""
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

# Check if default_user already has agent skills
print("=== Check default_user agent skills ===")
r = run(ssh, "python3 -c \"\nimport sys; sys.path.insert(0,'/var/www/html')\nfrom backend.services.user_agent_skills import user_agent_skills\ndata = user_agent_skills.get_user_skills('default_user')\nimport json; print('assigned_agents:', data.get('assigned_agents', []))\n\" 2>&1")
print(r)

# Seed if empty
print("\n=== Seeding default_user agent skills ===")
data = json.dumps({
    "user_id": "default_user",
    "assigned_agents": ["content_generator_agent", "analytics_agent"],
    "skills": [
        {"agent_id": "content_generator_agent", "skill": "generate_video", "level": 1, "experience": 0, "usage_count": 0},
        {"agent_id": "analytics_agent", "skill": "track_metrics", "level": 1, "experience": 0, "usage_count": 0}
    ],
    "skill_path": "balanced"
})
print(run(ssh, f"cat > /var/www/html/logs/user_agent_skills/default_user.json << 'EOF'\n{data}\nEOF\necho seeded"))

# Test
print("\n=== Test default_user my-agents ===")
r2 = run(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | python3 -c \"import sys,json; d=json.load(sys.stdin); print('agents:', len(d.get('agents',[])), [a.get('name') for a in d.get('agents',[])])\"")
print(r2)

print("\n=== Full end-to-end: record action then check feed ===")
print(run(ssh, """curl -s -X POST 'http://127.0.0.1:5000/vidgenerator/api/agents/record-action' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"default_user","agent_id":"content_generator_agent","action":"generate_video","skill":"generate_video","xp_gained":30}' 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print('recorded:', d.get('success'))" """))

print(run(ssh, """curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/activity-feed?user_id=default_user&limit=3' 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); acts=d.get('activities',[]); print('activities:', len(acts)); [print(' label:', a.get('label'), '+',a.get('xp_gained'),'xp') for a in acts]" """))

ssh.close()
print("Done.")
