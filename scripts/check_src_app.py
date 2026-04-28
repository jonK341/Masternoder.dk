#!/usr/bin/env python3
"""Check src/app/__init__.py on server and test blueprint registration."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=60):
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
    print("CHECK SRC/APP/__INIT__.PY ON SERVER")
    print("=" * 60)

    print("\n[1] src/app/__init__.py content:")
    print(sh(ssh, "cat /var/www/html/src/app/__init__.py 2>&1"))

    print("\n[2] Check if register_all_blueprints is called:")
    print(sh(ssh, "grep -n 'register.*blueprint\\|register_all' /var/www/html/src/app/__init__.py 2>&1"))

    print("\n[3] Test creating app and listing routes with gallery:")
    test_code = '''
import sys
sys.path.insert(0, "/var/www/html")
sys.path.insert(0, "/var/www/html/vidgenerator")
import os
os.chdir("/var/www/html/vidgenerator")

# Suppress output
import contextlib
with open(os.devnull, 'w') as devnull:
    with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        from src.app import create_app
        app = create_app()

# Now print routes
routes = [r.rule for r in app.url_map.iter_rules() if 'gallery' in r.rule or 'shop-v3' in r.rule or '/lab' in r.rule]
for r in sorted(set(routes))[:20]:
    print(r)
print(f"Total matching: {len(routes)}")
'''
    print(sh(ssh, f"cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python3 -c '{test_code}' 2>&1", timeout=120))

    print("\n[4] Check uwsgi error log:")
    print(sh(ssh, "tail -50 /var/www/html/vidgenerator/uwsgi.log 2>&1 | grep -i 'error\\|gallery\\|shop\\|blueprint' || echo 'no matches'"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
