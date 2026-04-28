#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy trophies page fix + points API fix, then apply updates.
Uploads: vidgenerator/trophies/index.html, backend/routes/points_routes.py
Then runs apply_updates.py (clear cache, restart services, reload nginx).
"""
import os
import sys

# Files changed for trophies loading + points 500 fix
FILES_TO_DEPLOY = [
    "vidgenerator/trophies/index.html",
    "backend/routes/points_routes.py",
]

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = os.getenv("REMOTE_BASE", "/var/www/html")


def deploy():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        return False

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ssh = None
    try:
        print("=" * 60)
        print("DEPLOY: Trophies + Points fix")
        print("=" * 60)
        print("Host:", SERVER_HOST)
        print("Files:", FILES_TO_DEPLOY)
        print("Base:", base)
        print()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

        sftp = ssh.open_sftp()
        deployed = 0
        for rel_path in FILES_TO_DEPLOY:
            local_path = os.path.join(base, rel_path.replace("/", os.sep))
            if not os.path.exists(local_path):
                print("[SKIP]", rel_path, "(not found at", local_path, ")")
                continue
            remote_path = os.path.join(REMOTE_BASE, rel_path.replace("\\", "/")).replace("\\", "/")
            remote_dir = os.path.dirname(remote_path)
            # Ensure remote dir exists (block until done)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=10)
            stdout.channel.recv_exit_status()
            try:
                sftp.put(local_path, remote_path)
                print("[OK]", rel_path)
                deployed += 1
            except Exception as e:
                print("[ERROR]", rel_path, e)
        sftp.close()
        print()
        print("Deployed", deployed, "file(s).")
        ssh.close()

        print()
        if deployed > 0:
            print("Running apply_updates.py...")
            import subprocess
            r = subprocess.run(
                [sys.executable, os.path.join(base, "scripts", "apply_updates.py")],
                cwd=base,
                env={**os.environ, "DEPLOY_HOST": SERVER_HOST, "DEPLOY_PASS": SERVER_PASS},
            )
            if r.returncode != 0:
                print("[WARN] apply_updates.py exited with", r.returncode)
        else:
            print("[WARN] No files deployed; skipping apply_updates.")
        print()
        print("Done. Open https://" + SERVER_HOST.split(":")[0] + "/vidgenerator/trophies and press Ctrl+F5")
        return True
    except Exception as e:
        print("[ERROR]", e)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(0 if deploy() else 1)
