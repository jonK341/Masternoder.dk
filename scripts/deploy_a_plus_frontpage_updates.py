#!/usr/bin/env python3
"""
Deploy targeted A++ frontpage/points/agent-skill updates to production.
"""
import os
import sys
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"


def main() -> int:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        "vidgenerator/index.html",
        "vidgenerator/static/js/unified-point-counters.js",
        "vidgenerator/static/js/agent-skill-sets.js",
    ]

    ssh = None
    sftp = None
    try:
        print(f"Connecting to {SERVER_HOST}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()

        uploaded = 0
        for rel in files:
            local_path = os.path.join(base, rel)
            remote_path = f"{REMOTE_BASE}/{rel.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote_path)
            ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=10)
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            with sftp.file(remote_path, "w") as rf:
                rf.write(content)
            print(f"[OK] {rel}")
            uploaded += 1

        print(f"Uploaded {uploaded} files.")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


if __name__ == "__main__":
    sys.exit(main())
