import paramiko, time

HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()

status = run("systemctl is-active uwsgi-vidgenerator", t=5)
workers = run("ps aux | grep 'uwsgi.*vidgenerator.ini' | grep -v grep | wc -l", t=5)
print(f"Service: {status}  Workers: {workers}")
print()

endpoints = [
    ("Mission Control API",  "GET /vidgenerator/api/system/overview?compact=1"),
    ("Leaderboard Top 10",   "GET /vidgenerator/api/leaderboard/top10"),
    ("Leaderboard AI Insights", "GET /vidgenerator/api/leaderboard/ai-insights"),
    ("Daily Quests",         "GET /vidgenerator/api/quests/daily"),
    ("Shop Daily Deal",      "GET /vidgenerator/api/shop/daily-deal"),
    ("Shop Recommendations", "GET /vidgenerator/api/shop/recommendations"),
    ("Agent AI Strategy",    "GET /vidgenerator/api/agent/automation/ai-strategy"),
    ("Agent AI Diagnose",    "GET /vidgenerator/api/agent/automation/ai-diagnose"),
    ("Video Providers",      "GET /vidgenerator/api/ai/video-providers"),
    ("AI Providers",         "GET /vidgenerator/api/ai/providers"),
    ("User AI Analysis",     "GET /vidgenerator/api/user/ai-analysis?user_id=default_user"),
    ("Debugger",             "GET /vidgenerator/debugger/"),
]

ok = 0
for label, spec in endpoints:
    method, path = spec.split(" ", 1)
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{path}' --max-time 12", t=20)
    is_ok = code == "200"
    if is_ok:
        ok += 1
    print(f"  {'[OK]' if is_ok else '[--]'} [{code}]  {label}")

print()
p = run(r"""curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "
import sys,json
import os
d=json.load(sys.stdin)
h=d.get('health',{})
llm=d.get('llm',{})
vid=d.get('video_providers',[])
print('=== MISSION CONTROL ===')
print('Health Score :', h.get('score'), '/ 100  [Grade:', h.get('grade'), ']  ', h.get('label'))
print('LLM Providers:', llm.get('available'), '/', llm.get('total'), 'ready')
vid_names = [p['name'] for p in vid if p.get('available')]
print('Video Pipeline:', ' > '.join(vid_names))
print('Daily Deal   :', d.get('daily_deal',{}).get('name','—'))
print('========================')
" """, t=20)
print(p)
print(f"Result: {ok}/{len(endpoints)} endpoints verified")
ssh.close()
