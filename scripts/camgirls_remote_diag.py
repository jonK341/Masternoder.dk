#!/usr/bin/env python3
"""Remote diagnostics for camgirls API 500."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import deploy_host, deploy_user, remote_py_prefix, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--ask-pass", action="store_true")
    args = p.parse_args()

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"Connected {user}@{host}\n")

    web = "/var/www/html"
    py = remote_py_prefix(web)
    checks = [
        ("files", f"ls -la {web}/backend/routes/camgirls_routes.py {web}/data/camgirls_performers.json 2>&1"),
        ("register_blueprints", f"grep -n camgirls {web}/backend/register_blueprints.py | head -8"),
        (
            "import service",
            f"{py}$PY -c 'import sys; sys.path.insert(0,\"{web}\"); "
            "from backend.services.camgirls_service import list_performers_catalog; "
            "print(list_performers_catalog(user_id=\"test\"))' 2>&1",
        ),
        (
            "import routes",
            f"{py}$PY -c 'import sys; sys.path.insert(0,\"{web}\"); "
            "from backend.routes.camgirls_routes import camgirls_bp; print(camgirls_bp.name)' 2>&1",
        ),
        ("curl local", "curl -s -w '\\nHTTP:%{{http_code}}' 'http://127.0.0.1:5000/api/camgirls/performers?user_id=test'"),
        ("curl local debug", "curl -s 'http://127.0.0.1:5000/api/camgirls/performers?user_id=test&debug=1'"),
        (
            "flask routes",
            f"{py}$PY -c 'import sys; sys.path.insert(0,\"{web}\"); "
            "from backend.routes.camgirls_routes import camgirls_bp; "
            "print(\"camgirls_bp\", camgirls_bp.name)' 2>&1",
        ),
        ("uwsgi camgirl", "journalctl -u uwsgi-vidgenerator -n 100 --no-pager 2>&1 | grep -i camgirl || echo '(no camgirl in journal)'"),
        ("uwsgi error tail", "journalctl -u uwsgi-vidgenerator -n 40 --no-pager 2>&1 | tail -25"),
    ]
    for label, cmd in checks:
        print(f"=== {label} ===")
        print(sh(ssh, cmd))
        print()

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
