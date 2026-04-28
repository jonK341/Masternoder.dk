#!/usr/bin/env python3
"""List all routes containing gallery, shop, or lab on the server."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=120):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out + ("\n" + err if err else "")
    except Exception as e:
        return f"ERROR: {e}"


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("LIST ROUTES ON SERVER")
    print("=" * 60)

    # Use heredoc for multiline Python code
    print("\n[1] Routes containing gallery, shop-v3, or /lab:")
    result = sh(ssh, '''cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python3 << 'PYCODE'
import sys
sys.path.insert(0, "/var/www/html")
sys.path.insert(0, "/var/www/html/vidgenerator")
import os
os.chdir("/var/www/html/vidgenerator")

import contextlib
with open(os.devnull, "w") as devnull:
    with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        from src.app import create_app
        app = create_app()

for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    rule = r.rule
    if "gallery" in rule or "shop-v3" in rule or "/lab" in rule:
        print(f"{rule} [{list(r.methods - {'OPTIONS', 'HEAD'})}]")
PYCODE
''', timeout=180)
    print(result)

    print("\n[2] Check if /vidgenerator/api/gallery/list exists:")
    result = sh(ssh, '''cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python3 << 'PYCODE'
import sys
sys.path.insert(0, "/var/www/html")
sys.path.insert(0, "/var/www/html/vidgenerator")
import os
os.chdir("/var/www/html/vidgenerator")

import contextlib
with open(os.devnull, "w") as devnull:
    with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        from src.app import create_app
        app = create_app()

# Check specific routes
routes_to_check = ["/vidgenerator/api/gallery/list", "/vidgenerator/lab", "/vidgenerator/api/shop-v3/items"]
all_rules = [r.rule for r in app.url_map.iter_rules()]
for r in routes_to_check:
    exists = r in all_rules
    print(f"{r}: {'EXISTS' if exists else 'NOT FOUND'}")
PYCODE
''', timeout=180)
    print(result)

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
