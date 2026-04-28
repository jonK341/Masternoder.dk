import paramiko, time

HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def new_ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(HOST, username=USER, password=PASS, timeout=30)
    return s

def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()

def fire(ssh, cmd):
    try:
        ssh.exec_command(cmd, timeout=3)
    except Exception:
        pass

# Keep checking until active
print("Waiting for service to be active...")
for attempt in range(12):
    ssh = new_ssh()
    s = run(ssh, "systemctl is-active uwsgi-vidgenerator", t=5)
    print(f"  [{attempt+1}] {s}")
    if s == "active":
        break
    if s == "inactive" or s == "failed":
        print("  Starting service...")
        fire(ssh, "systemctl start uwsgi-vidgenerator")
    ssh.close()
    time.sleep(5)

ssh = new_ssh()

endpoints = [
    "/vidgenerator/api/system/overview?compact=1",
    "/vidgenerator/api/leaderboard/top10",
    "/vidgenerator/api/quests/daily",
    "/vidgenerator/api/shop/daily-deal",
    "/vidgenerator/api/shop/recommendations",
    "/vidgenerator/api/agent/automation/ai-diagnose",
    "/vidgenerator/api/agent/automation/ai-strategy",
    "/vidgenerator/api/ai/video-providers",
    "/vidgenerator/api/user/ai-analysis",
    "/vidgenerator/debugger/",
]

print("\nFinal Verification:")
ok_count = 0
for ep in endpoints:
    code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
    ok = code == "200"
    if ok:
        ok_count += 1
    print(f"  {'[OK]' if ok else '[!!]'}  {ep} -> {code}")

p = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "
import sys,json
import os
d=json.load(sys.stdin)
h=d.get('health',{})
llm=d.get('llm',{})
vid=d.get('video_providers',[])
tts=d.get('tts',{})
deal=d.get('daily_deal',{})
print()
print('=== MISSION CONTROL ===')
print('Health:  Score', h.get('score'), '/', 100, 'Grade:', h.get('grade'), '-', h.get('label'))
print('LLM:    ', llm.get('available'), 'ready /', llm.get('total'), 'configured')
print('Video:  ', sum(1 for p in vid if p.get('available')), 'ready /', len(vid), 'total')
print('TTS:    ', tts.get('active_provider','none'))
print('Deal:   ', deal.get('name','none'), '-', deal.get('discount_pct','?'), '% off')
print('======================')
" """, t=20)
print(p)
print(f"\n{ok_count}/{len(endpoints)} endpoints passing")
ssh.close()
