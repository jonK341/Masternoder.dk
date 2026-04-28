"""Full verification of the agent system."""
import paramiko, os, json

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
USER_ID = "user_b4984c3befca47a7"

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())\

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print(f"=== Test 1: my-agents for {USER_ID} ===")
r = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id={USER_ID}' 2>&1")
try:
    d = json.loads(r)
    print(f"  success={d.get('success')}, agents={len(d.get('agents',[]))}")
    for ag in d.get('agents', []):
        print(f"    {ag.get('icon','')} {ag.get('name')}: level={ag.get('level')}, xp={ag.get('xp')}, actions={ag.get('total_actions')}, skills={ag.get('skill_count')}")
except Exception as e:
    print("  ERROR:", e, r[:200])

print(f"\n=== Test 2: Record an agent action ===")
r2 = run(ssh, f"""curl -s -X POST 'http://127.0.0.1:5000/vidgenerator/api/agents/record-action' \
  -H 'Content-Type: application/json' \
  -d '{{"user_id":"{USER_ID}","agent_id":"content_generator_agent","action":"generate_video","skill":"generate_video","xp_gained":30,"points_gained":25.0}}' 2>&1""")
try:
    d2 = json.loads(r2)
    print(f"  success={d2.get('success')}, xp_gained={d2.get('xp_gained')}")
except Exception as e:
    print("  ERROR:", e, r2[:200])

print(f"\n=== Test 3: Activity feed ===")
r3 = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/activity-feed?user_id={USER_ID}&limit=5' 2>&1")
try:
    d3 = json.loads(r3)
    print(f"  success={d3.get('success')}, activities={len(d3.get('activities',[]))}")
    for act in d3.get('activities', [])[:3]:
        print(f"    {act.get('icon','')} [{act.get('agent_name')}] {act.get('label')} +{act.get('xp_gained')} XP")
except Exception as e:
    print("  ERROR:", e, r3[:200])

print(f"\n=== Test 4: my-agents updated after action ===")
r4 = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id={USER_ID}' 2>&1")
try:
    d4 = json.loads(r4)
    for ag in d4.get('agents', []):
        print(f"    {ag.get('icon','')} {ag.get('name')}: level={ag.get('level')}, xp={ag.get('xp')}, actions={ag.get('total_actions')}, last_action={ag.get('last_action')}")
except Exception as e:
    print("  ERROR:", e, r4[:200])

print(f"\n=== Test 5: Sync endpoint ===")
r5 = run(ssh, f"""curl -s -X POST 'http://127.0.0.1:5000/vidgenerator/api/agents/sync' \
  -H 'Content-Type: application/json' \
  -d '{{"user_id":"{USER_ID}"}}' 2>&1""")
try:
    d5 = json.loads(r5)
    print(f"  success={d5.get('success')}, rows_synced={d5.get('rows_synced')}")
except Exception as e:
    print("  ERROR:", e, r5[:200])

ssh.close()
print("\nAll tests complete!")
