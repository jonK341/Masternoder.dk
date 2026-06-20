#!/usr/bin/env python3
"""Seed queued platform masternode hosts (platform-mn-2 …) on production."""
import argparse
import json
import os
import sys

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

HOSTS = [
    {"id": "platform-mn-2", "label": "Masternoder.dk fleet #2", "status": "queued"},
    {"id": "platform-mn-3", "label": "Masternoder.dk fleet #3", "status": "queued"},
    {"id": "platform-mn-4", "label": "Masternoder.dk fleet #4", "status": "queued"},
    {"id": "platform-mn-5", "label": "Masternoder.dk fleet #5", "status": "queued"},
]


def sh(ssh, cmd, timeout=120):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main():
    p = argparse.ArgumentParser(description="Seed queued platform masternode hosts on production")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"== Connected {user}@{host} ==\n")

    for h in HOSTS:
        h = dict(h)
        h["notes"] = "Queued for collateral provisioning — platform expansion slot"
        body = json.dumps(h)
        if args.dry_run:
            print("[DRY-RUN]", body)
            continue
        cmd = f'''
cd /var/www/html
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\\r"')
curl -s -X POST -H "Content-Type: application/json" -H "X-Ops-Secret: $SECRET" \\
  -d '{body.replace("'", "'\"'\"'")}' \\
  http://127.0.0.1:5000/api/mn2/masternode/hosts
echo ""
'''
        out = sh(ssh, cmd, timeout=30)
        print(f"-- {h['id']} --")
        print(out)

    if not args.dry_run:
        status = sh(ssh, "curl -s http://127.0.0.1:5000/api/mn2/masternode/service | head -c 2000")
        print("\n== service status ==\n")
        print(status)

    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
