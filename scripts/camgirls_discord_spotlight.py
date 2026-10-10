#!/usr/bin/env python3
"""Post Discord partner spotlight for camgirls roster (M8 #54)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from project_env import load_project_dotenv

DEFAULT_PAYLOAD = {
    "title": "Live AI performers",
    "summary": "Nova, Luna, Sage, Ember, Iris — studio voice, gifts, fan club · /camgirls/",
    "href": "/camgirls/",
}


def spotlight_local(base: str = "http://127.0.0.1:5000") -> int:
    import urllib.request

    load_project_dotenv()
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("MN2_SCAN_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or ""
    ).strip()
    if not secret:
        print("Set MN2_OPS_SECRET in .env", file=sys.stderr)
        return 1
    body = json.dumps(DEFAULT_PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/discord/m8/partner-spotlight",
        data=body,
        headers={"Content-Type": "application/json", "X-Ops-Secret": secret},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode(errors="replace")
            print(text)
            return 0 if resp.status == 200 else 1
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1


def spotlight_remote(*, force_prompt: bool) -> int:
    try:
        import paramiko
    except ImportError:
        print("paramiko required", file=sys.stderr)
        return 1
    load_project_dotenv()
    from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

    pw = require_deploy_pass(force_prompt=force_prompt)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    payload = json.dumps(DEFAULT_PAYLOAD).replace("'", "'\\''")
    cmd = (
        "cd /var/www/html && source cron/mn2_read_ops_secret.sh 2>/dev/null || true; "
        "SECRET=$(mn2_read_ops_secret 2>/dev/null || "
        "grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\\r\"'); "
        f"curl -s -X POST -H \"X-Ops-Secret: $SECRET\" -H 'Content-Type: application/json' "
        f"-d '{payload}' http://127.0.0.1:5000/api/discord/m8/partner-spotlight"
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    print(stdout.read().decode(errors="replace"))
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    ssh.close()
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Discord partner spotlight for camgirls")
    parser.add_argument("--remote", action="store_true", help="POST via SSH on production")
    parser.add_argument("--ask-pass", action="store_true")
    parser.add_argument("--local", action="store_true", help="POST to 127.0.0.1 (on server)")
    args = parser.parse_args()
    if args.remote:
        return spotlight_remote(force_prompt=args.ask_pass)
    if args.local:
        return spotlight_local()
    return spotlight_remote(force_prompt=args.ask_pass)


if __name__ == "__main__":
    raise SystemExit(main())
