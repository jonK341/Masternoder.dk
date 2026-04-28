"""
Deploy ALL new/updated route files to ROOT /var/www/html/backend/routes/
This ensures Python finds the correct versions first (ROOT path has priority).
"""
import os, time, paramiko
from datetime import datetime

HOST = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = "/var/www/html"

# All files that need to reach ROOT (Python's primary import path)
FILES = [
    # Routes with AI upgrades
    "backend/routes/missing_endpoints_routes.py",
    "backend/routes/shop_routes.py",
    "backend/routes/agent_automation_routes.py",
    "backend/routes/gallery_routes.py",
    "backend/routes/user_profile_routes.py",
    "backend/routes/ai_providers_routes.py",
    "backend/register_blueprints.py",
    # New route files (also deploy to ROOT so path order doesn't matter)
    "backend/routes/leaderboard_routes.py",
    "backend/routes/quest_routes.py",
    "backend/routes/system_overview_routes.py",
    # Services
    "backend/services/tts_service.py",
    "backend/services/runwayml_service.py",
    "backend/services/pika_service.py",
    "backend/services/video_generator_service.py",
    # Frontend
    "vidgenerator/debugger/index.html",
]


def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()


def fire(ssh, cmd):
    try:
        ssh.exec_command(cmd, timeout=3)
    except Exception:
        pass


def deploy():
    print("=" * 60)
    print("Deploy ALL to ROOT — comprehensive fix")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    ok = 0
    for rel in FILES:
        local = os.path.join(BASE, rel.replace("/", os.sep))
        if not os.path.exists(local):
            print(f"  [SKIP] {rel} (not found locally)")
            continue
        remote = ROOT + "/" + rel
        run(ssh, "mkdir -p " + remote.rsplit("/", 1)[0])
        sftp.put(local, remote)
        print(f"  [OK]  {rel}")
        ok += 1
    print(f"\n  Deployed {ok} files to ROOT")

    # Clean ALL pyc caches
    print("\n[CLEANUP] Clearing ALL pyc caches...")
    for d in ["/var/www/html/backend", "/var/www/html/src", "/var/www/html/vidgenerator/backend"]:
        run(ssh, f"find {d} -name '*.pyc' -delete 2>/dev/null; find {d} -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null; true", t=8)

    # Restart the CORRECT service (fire-and-forget to avoid SSH timeout)
    print("\n[RELOAD] Restarting uwsgi-vidgenerator.service (fire-and-forget)...")
    fire(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; sleep 3; systemctl start uwsgi-vidgenerator 2>/dev/null")
    ssh.close()

    print("Waiting 18s for workers to spin up...")
    time.sleep(18)

    # Reconnect and verify
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)

    status = run(ssh, "systemctl is-active uwsgi-vidgenerator", t=8)
    print(f"  Service: {status}")

    print("\n[VERIFY]")
    tests = [
        "/vidgenerator/api/system/overview?compact=1",
        "/vidgenerator/api/leaderboard/top10",
        "/vidgenerator/api/quests/daily",
        "/vidgenerator/api/shop/daily-deal",
        "/vidgenerator/api/shop/recommendations",
        "/vidgenerator/api/agent/automation/ai-diagnose",
        "/vidgenerator/api/ai/video-providers",
        "/vidgenerator/debugger/",
    ]
    passed = 0
    for ep in tests:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        ok_flag = code == "200"
        if ok_flag:
            passed += 1
        print(f"  {'[OK]' if ok_flag else '[WARN]'}  {ep} -> {code}")

    # Full overview payload
    p = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "
import sys,json
d=json.load(sys.stdin)
h=d.get('health',{})
llm=d.get('llm',{})
vid=d.get('video_providers',[])
tts=d.get('tts',{})
print()
print('=== MISSION CONTROL SNAPSHOT ===')
print('Health Score :', h.get('score'), '/ 100  Grade:', h.get('grade'), ' -', h.get('label'))
print('LLM Providers:', llm.get('available',0), 'ready /', llm.get('total',0), 'configured')
print('Video Provdrs:', sum(1 for p in vid if p.get('available')), 'ready /', len(vid), 'total')
print('TTS          :', tts.get('active_provider','none'))
print('Daily Deal   :', d.get('daily_deal',{}).get('name','(no deal today)'))
print('AI Quests    :', len(d.get('daily_quests',[])), 'active quests')
print('================================')
" """, t=20)
    if p:
        print(p)

    sftp.close(); ssh.close()
    print(f"\n[DONE] {passed}/{len(tests)} endpoints verified")
    print("\nMission Control: https://masternoder.dk/vidgenerator/debugger/")
    print("System Overview: https://masternoder.dk/vidgenerator/api/system/overview")


if __name__ == "__main__":
    deploy()
