"""
Deploy AI Providers — Multi-provider LLM system + 6 new free AI keys.

Deploys:
  - backend/services/llm_service.py           (full rewrite: 7 providers, smart routing)
  - backend/routes/ai_providers_routes.py      (new: status/test/reset/chat endpoints)
  - backend/routes/chat_routes.py              (task_type=speed → Groq)
  - backend/services/agent_ai_orchestrator.py  (task_type=reason → DeepSeek R1)
  - backend/services/video_generator_service.py (task_type=speed/context, provider-agnostic)
  - backend/services/ai_content_generator.py   (task_type routing per content type)

Syncs env keys (set in local .env; pushed to server .env files):
  LLM: OPENAI_*, GROQ_*, GOOGLE_AI_*, GOOGLE_GEMINI_*, OPENROUTER_*, CEREBRAS_*,
  DEEPSEEK_*, MISTRAL_*, TOGETHER_*, ANTHROPIC_*, COHERE_*, AZURE_OPENAI_*,
  Video/TTS: MODELSLAB_*, ELEVENLABS_*, HEYGEN_*, REPLICATE_API_TOKEN
"""
import os
import sys
import time
import paramiko
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES_TO_DEPLOY = [
    # Core AI layer
    "backend/services/llm_service.py",
    "backend/routes/ai_providers_routes.py",
    "backend/register_blueprints.py",
    # Move 3: TTS
    "backend/services/tts_service.py",
    # Move 4: Debugger AI panel
    "vidgenerator/debugger/index.html",
    # Move 5: Streaming chat
    "backend/routes/chat_routes.py",
    "vidgenerator/chat/index.html",
    # Move 6: Free image generation
    "backend/services/free_image_service.py",
    "backend/services/video_generator_service.py",
    # Move 7: Battle AI
    "backend/routes/battle_routes.py",
    # Other updated services
    "backend/services/agent_ai_orchestrator.py",
    "backend/services/ai_content_generator.py",
    "requirements.txt",
]

ENV_FILES_ON_SERVER = [
    "/var/www/html/.env",
    "/var/www/html/vidgenerator/.env",
]

# Keys to sync from local .env to server .env files
KEYS_TO_SYNC = [
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_MODEL_BEST",
    "GROQ_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "MODELSLAB_API_KEY",
    "ELEVENLABS_API_KEY",
    "HEYGEN_API_KEY",
    "REPLICATE_API_TOKEN",
    "RUNWAYML_API_KEY",
    "PIKA_LABS_API_KEY",
    "STABILITY_AI_API_KEY",
]

VERIFY_ENDPOINTS = [
    "/api/ai/providers",
    "/vidgenerator/api/ai/providers",
]


def load_local_env() -> dict:
    """Load key=value pairs from local .env file."""
    env_path = os.path.join(BASE_DIR, ".env")
    result = {}
    if not os.path.exists(env_path):
        print("  [WARN] Local .env not found")
        return result
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and val:
                result[key] = val
    return result


def sync_env_key(ssh, env_file: str, key: str, value: str) -> str:
    """Upsert a key=value in a remote .env file. Returns 'updated'|'appended'|'skipped'|'error'."""
    # Check if file exists
    stdin, stdout, stderr = ssh.exec_command(f"test -f {env_file} && echo yes || echo no")
    exists = stdout.read().decode().strip()
    if exists != "yes":
        return "skipped"

    # Check if key already present
    stdin, stdout, stderr = ssh.exec_command(f"grep -c '^{key}=' {env_file} 2>/dev/null || echo 0")
    count = stdout.read().decode().strip()
    try:
        count = int(count)
    except ValueError:
        count = 0

    safe_value = value.replace("'", "'\\''")  # escape single quotes for sed

    if count > 0:
        # Update existing
        stdin, stdout, stderr = ssh.exec_command(f"sed -i 's|^{key}=.*|{key}={safe_value}|' {env_file}")
        stdout.channel.recv_exit_status()
        return "updated"
    else:
        # Append new
        stdin, stdout, stderr = ssh.exec_command(f"echo '{key}={safe_value}' >> {env_file}")
        stdout.channel.recv_exit_status()
        return "appended"


def deploy():
    print("=" * 70)
    print("DEPLOY: AI Providers — Multi-provider LLM + 6 free keys")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # ── Connect ────────────────────────────────────────────────────────
        print("[1/5] Connecting to masternoder.dk...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()

        # ── Upload files ───────────────────────────────────────────────────
        print("[2/5] Uploading files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0

        for local_rel in FILES_TO_DEPLOY:
            local_path = os.path.join(BASE_DIR, local_rel)
            if not os.path.exists(local_path):
                print(f"  [SKIP] {local_rel} (not found locally)")
                skipped += 1
                continue
            try:
                remote_path = f"/var/www/html/{local_rel}"
                remote_dir = remote_path.rsplit("/", 1)[0]
                ssh.exec_command(f"mkdir -p {remote_dir}")
                # Backup existing file
                ssh.exec_command(
                    f"cp {remote_path} {remote_path}.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"
                )
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with sftp.file(remote_path, "w") as rf:
                    rf.write(content)
                print(f"  [OK] {local_rel}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_rel}: {e}")

        sftp.close()
        print(f"  Deployed: {deployed} | Skipped: {skipped}")
        print()

        # ── Sync env keys ──────────────────────────────────────────────────
        print("[3/5] Syncing AI provider keys to server .env files...")
        local_env = load_local_env()
        synced_any = False

        for env_file in ENV_FILES_ON_SERVER:
            print(f"  {env_file}:")
            for key in KEYS_TO_SYNC:
                val = local_env.get(key, "")
                if not val:
                    print(f"    [SKIP] {key} — not set locally")
                    continue
                action = sync_env_key(ssh, env_file, key, val)
                masked = val[:6] + "..." if len(val) > 8 else val
                print(f"    [{action.upper()}] {key}={masked}")
                synced_any = True

        if not synced_any:
            print("  [WARN] No keys synced — check local .env values")
        print()

        # ── Install new Python deps ────────────────────────────────────────
        print("[3b/5] Installing gTTS on server (free TTS fallback)...")
        venv = "/var/www/html/vidgenerator/.venv"
        pip = f"{venv}/bin/pip"
        stdin, stdout, stderr = ssh.exec_command(
            f"{pip} install gTTS>=2.5.0 --quiet 2>&1 || pip3 install gTTS>=2.5.0 --quiet 2>&1",
            timeout=60,
        )
        out = stdout.read().decode().strip()
        if "Successfully installed" in out or "already satisfied" in out:
            print("  [OK] gTTS ready")
        else:
            print("  [OK] gTTS install attempted")
        print()

        # ── Clear Python cache ─────────────────────────────────────────────
        print("[4/5] Clearing Python cache + restarting services...")
        ssh.exec_command(
            "find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true"
        )
        ssh.exec_command(
            "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true"
        )

        # Restart
        for service in ["uwsgi", "uwsgi-vidgenerator", "python-proxy"]:
            ssh.exec_command(f"systemctl stop {service} 2>/dev/null || true")
        time.sleep(3)
        for service in ["uwsgi", "uwsgi-vidgenerator", "python-proxy"]:
            ssh.exec_command(f"systemctl start {service} 2>/dev/null || true")
        print("  [WAIT] Services restarting...")
        time.sleep(10)

        for service in ["uwsgi", "uwsgi-vidgenerator", "python-proxy"]:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>/dev/null")
            status = stdout.read().decode().strip()
            icon = "[OK]" if status == "active" else "[WARN]"
            print(f"  {icon} {service}: {status}")
        print()

        # ── Verify new endpoints ───────────────────────────────────────────
        print("[5/5] Verifying new AI provider endpoints...")
        passed = 0
        for ep in VERIFY_ENDPOINTS:
            cmd = f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 10"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            code = stdout.read().decode().strip()
            if code == "200":
                print(f"  [OK]   {ep} -> {code}")
                passed += 1
            else:
                print(f"  [WARN] {ep} -> {code or 'no response'}")

        ssh.close()

        # ── Summary ────────────────────────────────────────────────────────
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print(f"  Files deployed : {deployed}")
        print(f"  Endpoints live : {passed}/{len(VERIFY_ENDPOINTS)}")
        print()
        print("  Test all providers:")
        print("  https://masternoder.dk/api/ai/providers")
        print("  https://masternoder.dk/api/ai/providers/test")
        print()

        return deployed > 0

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = deploy()
    sys.exit(0 if ok else 1)
