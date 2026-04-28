"""Seed agent assignments and DB for the production user, then verify."""
import paramiko, os, json, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
USER_ID = "user_b4984c3befca47a7"

def run(ssh, cmd, timeout=25):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

# Seed user_agent_skills on server
user_skills_data = json.dumps({
    "user_id": USER_ID,
    "assigned_agents": ["content_generator_agent", "analytics_agent"],
    "skills": [
        {"agent_id": "content_generator_agent", "skill": "generate_video", "level": 1, "experience": 30, "usage_count": 1},
        {"agent_id": "content_generator_agent", "skill": "generate_image", "level": 1, "experience": 0, "usage_count": 0},
        {"agent_id": "analytics_agent", "skill": "track_metrics", "level": 1, "experience": 15, "usage_count": 1},
        {"agent_id": "analytics_agent", "skill": "analyze_user_behavior", "level": 1, "experience": 15, "usage_count": 1}
    ],
    "skill_path": "balanced",
    "assigned_at": "2026-01-23T14:09:57.774181",
    "updated_at": "2026-02-24T22:00:00.000000"
})

print("=== Seeding user_agent_skills ===")
print(run(ssh, f"""cat > /var/www/html/logs/user_agent_skills/{USER_ID}.json << 'JSONEOF'
{user_skills_data}
JSONEOF
echo seeded"""))

# Seed agent_progress fallback
agent_progress_data = json.dumps({
    "agents": {
        "content_generator_agent": {
            "xp": 67, "level": 1, "total_actions": 3,
            "last_action": "generate_video", "last_action_at": "2026-02-17T16:44:51.881998"
        },
        "analytics_agent": {
            "xp": 57, "level": 1, "total_actions": 2,
            "last_action": "track_metrics", "last_action_at": "2026-02-17T16:44:00.000000"
        }
    },
    "activity": [
        {"agent_id": "content_generator_agent", "action": "generate_video", "skill": "generate_video",
         "xp_gained": 30, "points_gained": 25.0, "created_at": "2026-02-17T16:44:51.881998"},
        {"agent_id": "analytics_agent", "action": "track_metrics", "skill": "track_metrics",
         "xp_gained": 15, "points_gained": 10.0, "created_at": "2026-02-17T16:44:00.000000"}
    ]
})
print("\n=== Seeding agent_progress fallback ===")
print(run(ssh, f"""mkdir -p /var/www/html/logs/agent_progress && cat > /var/www/html/logs/agent_progress/{USER_ID}.json << 'JSONEOF'
{agent_progress_data}
JSONEOF
echo seeded"""))

# Sync via API
time.sleep(1)
print("\n=== Sync via API ===")
print(run(ssh, f"""curl -s -X POST 'http://127.0.0.1:5000/vidgenerator/api/agents/sync' \
  -H 'Content-Type: application/json' \
  -d '{{"user_id":"{USER_ID}"}}' 2>&1"""))

# Test full flow
print("\n=== Final test: my-agents ===")
r = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id={USER_ID}' 2>&1")
try:
    d = json.loads(r)
    print(f"success={d.get('success')}, agents={len(d.get('agents', []))}")
    for ag in d.get('agents', []):
        print(f"  {ag.get('icon','')} {ag.get('name')}: level {ag.get('level')}, {ag.get('xp')} XP, {ag.get('total_actions')} actions, {ag.get('skill_count')} skills")
except Exception as e:
    print("ERROR:", e, r[:300])

print("\n=== Final test: activity-feed ===")
r2 = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/activity-feed?user_id={USER_ID}&limit=5' 2>&1")
try:
    d2 = json.loads(r2)
    print(f"success={d2.get('success')}, activities={len(d2.get('activities', []))}")
    for act in d2.get('activities', [])[:3]:
        print(f"  {act.get('icon','')} [{act.get('agent_name')}] {act.get('label')} +{act.get('xp_gained')} XP")
except Exception as e:
    print("ERROR:", e, r2[:300])

ssh.close()
print("\nDone!")
