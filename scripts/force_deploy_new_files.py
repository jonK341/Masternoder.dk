"""Force deploy new/changed files to production."""
import paramiko
import os

SERVER = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"
LOCAL_BASE = os.path.join(os.path.dirname(__file__), "..")

FILES = [
    "backend/services/stability_image_service.py",
    "backend/services/video_generator_service.py",
    "backend/services/llm_service.py",
    "backend/services/modelslab_video_service.py",
    "backend/services/generator_context_service.py",
    "backend/services/tts_service.py",
]


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASS, timeout=10)
    sftp = ssh.open_sftp()

    for f in FILES:
        local = os.path.join(LOCAL_BASE, f.replace("/", os.sep))
        remote = f"{REMOTE_BASE}/{f}"
        if not os.path.exists(local):
            print(f"  SKIP (not found): {f}")
            continue
        remote_dir = os.path.dirname(remote)
        ssh.exec_command(f"mkdir -p {remote_dir}")
        sftp.put(local, remote)
        print(f"  UPLOADED: {f}")

    sftp.close()

    print("\nRestarting Flask...")
    stdin, stdout, stderr = ssh.exec_command(
        "systemctl restart uwsgi 2>/dev/null; "
        "systemctl restart flask-app 2>/dev/null; "
        "pkill -f 'uwsgi.*vidgenerator' 2>/dev/null; "
        "sleep 1; "
        "cd /var/www/html && uwsgi --ini vidgenerator/uwsgi.ini --daemonize /var/log/uwsgi/vidgenerator.log 2>/dev/null; "
        "echo DONE"
    )
    print(stdout.read().decode().strip())

    print("\nVerifying providers...")
    stdin, stdout, stderr = ssh.exec_command(
        "cd /var/www/html && python3 -c \""
        "from backend.services.llm_service import configured_providers; "
        "print('LLM providers:', configured_providers()); "
        "from backend.services.stability_image_service import is_available; "
        "print('Stability AI:', is_available())\""
    )
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(out)
    if err:
        print(f"  WARN: {err[:200]}")

    ssh.close()
    print("\nDeploy complete.")


if __name__ == "__main__":
    main()
