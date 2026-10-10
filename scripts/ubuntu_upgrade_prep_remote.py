#!/usr/bin/env python3
"""Run ubuntu_upgrade_prep.sh on production via SSH (from your PC)."""

from __future__ import annotations

import argparse
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
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Remote Ubuntu upgrade prep on masternoder.dk")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--backup-only", action="store_true", help="Backup tarball only; do not print upgrade hints block")
    args = p.parse_args()

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"Connected {user}@{host}\n")

    flag = " --backup-only" if args.backup_only else ""
    print(sh(ssh, f"cd {WEB} && bash scripts/ubuntu_upgrade_prep.sh{flag}", timeout=900))

    check = sh(ssh, f"test -f {WEB}/scripts/ubuntu_upgrade_prep.sh && echo OK || echo MISSING")
    if "MISSING" in check:
        print("\n[WARN] Prep script not on server — deploy scripts first:")
        print("  python scripts/deploy.py --files scripts/ubuntu_upgrade_prep.sh scripts/ubuntu_upgrade_post_verify.sh --ask-pass")

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
