"""Deploy Moves 6-10."""
import os, time, paramiko
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "/var/www/html/vidgenerator"

FILES = [
    # Move 6: Pika 2.2
    "backend/services/pika_service.py",
    "backend/services/video_generator_service.py",
    # Move 7: Leaderboard AI
    "backend/routes/leaderboard_routes.py",
    # Move 8: Shop AI
    "backend/routes/shop_routes.py",
    # Move 9: Agent automation AI
    "backend/routes/agent_automation_routes.py",
    # Move 10: TTS upgrade + voices
    "backend/services/tts_service.py",
    # Shared: ai_providers_routes (Pika status + TTS voices)
    "backend/routes/ai_providers_routes.py",
    # Register leaderboard blueprint
    "backend/register_blueprints.py",
]

VERIFY = [
    "/vidgenerator/api/leaderboard/top10",
    "/vidgenerator/api/leaderboard",
    "/vidgenerator/api/leaderboard/ai-insights",
    "/vidgenerator/api/shop/recommendations",
    "/vidgenerator/api/shop/daily-deal",
    "/vidgenerator/api/agent/automation/ai-diagnose",
    "/vidgenerator/api/ai/video-providers",
]

def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()

def deploy():
    print("=" * 60)
    print("Deploy: Moves 6-10")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    ok = fail = 0
    for rel in FILES:
        local  = os.path.join(BASE_DIR, rel.replace("/", os.sep))
        remote = REMOTE_BASE + "/" + rel
        if not os.path.exists(local):
            print(f"  [SKIP] {rel}")
            continue
        run(ssh, "mkdir -p " + remote.rsplit("/", 1)[0])
        try:
            sftp.put(local, remote)
            print(f"  [OK]   {rel}")
            ok += 1
        except Exception as e:
            print(f"  [FAIL] {rel} -> {e}")
            fail += 1

    print(f"\n[UPLOAD] {ok} ok, {fail} failed.")
    print("[RELOAD] Restarting uWSGI...")
    run(ssh, "systemctl restart uwsgi 2>/dev/null || true", t=30)
    time.sleep(5)

    print(f"\n[VERIFY] {len(VERIFY)} endpoints...")
    for ep in VERIFY:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        flag = "[OK]" if code == "200" else "[WARN]"
        print(f"  {flag}  {ep} -> {code}")

    sftp.close(); ssh.close()
    print("\n[DONE] Moves 6-10 deployed!")
    print("\nNew endpoints:")
    print("  GET  /vidgenerator/api/leaderboard")
    print("  GET  /vidgenerator/api/leaderboard/top10")
    print("  GET  /vidgenerator/api/leaderboard/ai-insights")
    print("  GET  /vidgenerator/api/leaderboard/player/<id>")
    print("  POST /vidgenerator/api/leaderboard/rivalry")
    print("  GET  /vidgenerator/api/shop/recommendations")
    print("  GET  /vidgenerator/api/shop/daily-deal")
    print("  GET  /vidgenerator/api/agent/automation/ai-strategy")
    print("  GET  /vidgenerator/api/agent/automation/ai-diagnose")
    print("  Pika 2.2 wired into video generator pipeline")
    print("  TTS: 7 ElevenLabs voices + gTTS fallback")

if __name__ == "__main__":
    deploy()
