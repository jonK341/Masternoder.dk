#!/usr/bin/env python3
"""
Add nginx upstream for 5000+5001 so traffic is spread across both backends.
Run from your PC:  python scripts/enable_nginx_upstream.py

Reads /etc/nginx/sites-enabled/masternoder.dk, adds upstream flask_backend with
server 127.0.0.1:5000 and server 127.0.0.1:5001, and replaces proxy_pass
http://127.0.0.1:5000 with proxy_pass http://flask_backend. If 5001 is down,
nginx will use only 5000.
"""
import os
import re
import sys

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
NGINX_CONFIG = "/etc/nginx/sites-enabled/masternoder.dk"

UPSTREAM_BLOCK = """upstream flask_backend {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
}
"""


def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def main():
    dry_run = "--dry-run" in sys.argv
    print("=" * 60)
    print("Nginx: add upstream flask_backend (5000 + 5001)")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        return 1

    out, err = run(ssh, f"cat {NGINX_CONFIG} 2>/dev/null")
    if not out:
        print(f"[ERROR] Could not read {NGINX_CONFIG}")
        ssh.close()
        return 1

    content = out
    if "upstream flask_backend" in content:
        print("[OK] Config already has upstream flask_backend. Nothing to change.")
        ssh.close()
        return 0

    # Insert upstream at the beginning (before first server {)
    if "server {" in content:
        content = UPSTREAM_BLOCK + "\n" + content
    else:
        content = UPSTREAM_BLOCK + content

    # Replace proxy_pass http://127.0.0.1:5000 with proxy_pass http://flask_backend
    content = re.sub(
        r"proxy_pass\s+http://127\.0\.0\.1:5000\s*;",
        "proxy_pass http://flask_backend;",
        content,
    )

    if dry_run:
        print("(dry-run) New config would be:")
        print(content[:2000] + ("..." if len(content) > 2000 else ""))
        ssh.close()
        return 0

    run(ssh, f"cp {NGINX_CONFIG} {NGINX_CONFIG}.backup.upstream.$(date +%Y%m%d_%H%M%S)")
    sftp = ssh.open_sftp()
    with sftp.open(NGINX_CONFIG, "w") as f:
        f.write(content.encode("utf-8"))
    sftp.close()

    out, err = run(ssh, "nginx -t 2>&1")
    if "syntax is ok" not in out and "syntax is ok" not in err:
        print(f"[ERROR] nginx -t failed: {out or err}")
        ssh.close()
        return 1
    run(ssh, "systemctl reload nginx", timeout=10)
    print("[OK] Nginx reloaded. Traffic now goes to flask_backend (5000 + 5001).")
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
