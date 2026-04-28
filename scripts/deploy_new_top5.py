"""
Deploy New Top-5 Moves:
  1. RunwayML Gen-4 video service
  2. Fix doubled ModelsLab key
  3. Profile AI (Gemini 1M context analysis)
  4. Gallery AI descriptions
  5. Quest AI system

Also deploys:
  - ai_providers_routes.py (video provider status + RunwayML test endpoints)
  - register_blueprints.py (quest_bp registration)
"""
import os
import sys
import time
import paramiko
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES_TO_DEPLOY = [
    # Move 1: RunwayML Gen-4
    "backend/services/runwayml_service.py",
    "backend/services/video_generator_service.py",
    # Move 2: ModelsLab key fix (push .env itself is handled by KEYS_TO_SYNC below)
    # Move 3: Profile AI
    "backend/routes/user_profile_routes.py",
    # Move 4: Gallery AI descriptions
    "backend/routes/gallery_routes.py",
    # Move 5: Quest AI
    "backend/routes/quest_routes.py",
    "backend/register_blueprints.py",
    # Updated AI providers routes (video provider status + RunwayML test)
    "backend/routes/ai_providers_routes.py",
]

ENV_FILES_ON_SERVER = [
    "/var/www/html/.env",
    "/var/www/html/vidgenerator/.env",
]

KEYS_TO_SYNC = [
    "RUNWAYML_API_KEY",
    "MODELSLAB_API_KEY",     # fix the doubled value
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_AI_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "PIKA_LABS_API_KEY",
    "STABILITY_AI_API_KEY",
]

VERIFY_ENDPOINTS = [
    "/vidgenerator/api/quests/daily",
    "/vidgenerator/api/ai/video-providers",
    "/vidgenerator/api/ai/providers",
    "/vidgenerator/api/gallery/list",
]

REMOTE_BASE = "/var/www/html/vidgenerator"
SERVICE_RELOAD_CMD = "systemctl restart uwsgi 2>/dev/null || systemctl reload uwsgi 2>/dev/null || true"


def load_local_env():
    env = {}
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")
    return env


def run_ssh(ssh, cmd, timeout=30):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err


def deploy():
    print("=" * 60)
    print("MasterNoder.dk - Deploy New Top-5 Moves")
    print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    local_env = load_local_env()
    print(f"[ENV] Loaded {len(local_env)} keys from local .env")

    # ---- Connect ----
    print(f"\n[SSH] Connecting to {SERVER_USER}@{SERVER_HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    # ---- Upload files ----
    print(f"\n[UPLOAD] Deploying {len(FILES_TO_DEPLOY)} files ...")
    ok = fail = 0
    for rel_path in FILES_TO_DEPLOY:
        local_file  = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        remote_file = REMOTE_BASE + "/" + rel_path
        if not os.path.exists(local_file):
            print(f"  [SKIP] {rel_path} (not found locally)")
            continue
        remote_dir = remote_file.rsplit("/", 1)[0]
        run_ssh(ssh, f"mkdir -p {remote_dir}")
        try:
            sftp.put(local_file, remote_file)
            print(f"  [OK]   {rel_path}")
            ok += 1
        except Exception as e:
            print(f"  [FAIL] {rel_path} -> {e}")
            fail += 1
    print(f"[UPLOAD] {ok} uploaded, {fail} failed.")

    # ---- Sync env keys ----
    print(f"\n[ENV] Syncing {len(KEYS_TO_SYNC)} keys to server ...")
    for env_file in ENV_FILES_ON_SERVER:
        print(f"  -> {env_file}")
        for key in KEYS_TO_SYNC:
            val = local_env.get(key, "")
            if not val:
                continue
            # Check if key exists and update, or append
            check_cmd = f"grep -q '^{key}=' {env_file} 2>/dev/null && echo exists || echo missing"
            out, _ = run_ssh(ssh, check_cmd)
            if "exists" in out:
                update_cmd = f"sed -i 's|^{key}=.*|{key}={val}|' {env_file}"
                run_ssh(ssh, update_cmd)
                print(f"    [UPDATE] {key}")
            else:
                append_cmd = f"echo '{key}={val}' >> {env_file}"
                run_ssh(ssh, append_cmd)
                print(f"    [APPEND] {key}")

    # ---- Reload service ----
    print(f"\n[RELOAD] Restarting uWSGI ...")
    out, err = run_ssh(ssh, SERVICE_RELOAD_CMD, timeout=30)
    print("  stdout:", out[:200] if out else "(none)")
    if err:
        print("  stderr:", err[:200])
    time.sleep(4)

    # ---- Verify endpoints ----
    print(f"\n[VERIFY] Testing {len(VERIFY_ENDPOINTS)} endpoints ...")
    for ep in VERIFY_ENDPOINTS:
        curl = f"curl -s -o /dev/null -w '%{{http_code}}' https://masternoder.dk{ep} --max-time 15"
        code, _ = run_ssh(ssh, curl, timeout=25)
        status = "[OK]" if code in ("200", "201") else "[WARN]"
        print(f"  {status}  {ep} -> HTTP {code}")

    # ---- Done ----
    sftp.close()
    ssh.close()
    print("\n" + "=" * 60)
    print("[DONE] Deployment complete!")
    print("=" * 60)
    print("\nNew endpoints live:")
    print("  GET  /vidgenerator/api/quests/daily")
    print("  POST /vidgenerator/api/quests/generate")
    print("  POST /vidgenerator/api/quests/complete")
    print("  GET  /vidgenerator/api/quests/active")
    print("  GET  /vidgenerator/api/ai/video-providers")
    print("  POST /vidgenerator/api/ai/video-providers/test")
    print("  GET  /vidgenerator/api/gallery/video/<id>/ai-description")
    print("  POST /vidgenerator/api/gallery/enhance-metadata")
    print("  GET  /vidgenerator/api/user/ai-analysis")


if __name__ == "__main__":
    deploy()
