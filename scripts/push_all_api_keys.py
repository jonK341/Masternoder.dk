"""Push all API keys from local .env to production .env files."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

KEYS_TO_PUSH = [
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
    "STABILITY_AI_API_KEY",
    "STABLE_API_KEY",
    "STABLE_VIDEO_API_KEY",
    "MODELSLAB_API_KEY",
    "RUNWAYML_API_KEY",
    "PIKA_LABS_API_KEY",
    "ELEVENLABS_API_KEY",
    "HEYGEN_API_KEY",
    "REPLICATE_API_TOKEN",
]


def load_local_env():
    """Read local .env to get values."""
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def main():
    local = load_local_env()
    keys = {k: local[k] for k in KEYS_TO_PUSH if k in local and local[k]}

    print(f"Found {len(keys)} keys to push:")
    for k in keys:
        print(f"  {k}={keys[k][:8]}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    env_files = ["/var/www/html/.env", "/var/www/html/vidgenerator/.env"]

    for ef in env_files:
        print(f"\n--- Updating {ef} ---")
        for key_name, key_val in keys.items():
            ssh.exec_command(f"sed -i '/^{key_name}=/d' {ef}")
            import time; time.sleep(0.1)
            cmd = f"echo '{key_name}={key_val}' >> {ef}"
            ssh.exec_command(cmd)
            time.sleep(0.1)

        stdin, stdout, stderr = ssh.exec_command(f"grep -c '=' {ef}")
        count = stdout.read().decode().strip()
        print(f"  Total env vars: {count}")

    print("\n--- Verification ---")
    stdin, stdout, stderr = ssh.exec_command(
        r"grep '_API_KEY=\|_MODEL' /var/www/html/.env | sed 's/=.\{8\}/=***.../' | sort"
    )
    lines = stdout.read().decode().strip()
    for line in lines.split("\n"):
        print(f"  {line}")

    print(f"\n  Keys pushed: {len(keys)}")
    ssh.close()
    print("\nDone. Restart Flask to activate.")


if __name__ == "__main__":
    main()
