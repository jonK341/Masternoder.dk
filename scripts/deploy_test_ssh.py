#!/usr/bin/env python3
"""Test deploy SSH auth (keys first, then password)."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user


def main() -> int:
    p = argparse.ArgumentParser(description="Test SSH to deploy host")
    p.add_argument("--ask-pass", action="store_true")
    args = p.parse_args()
    host, user = deploy_host(), deploy_user()
    print(f"Connecting to {user}@{host} ...")
    ssh, method, _ = connect_deploy_ssh(force_prompt=args.ask_pass)
    _, stdout, _ = ssh.exec_command("echo ok && hostname", timeout=15)
    out = (stdout.read() or b"").decode().strip()
    ssh.close()
    print(f"Auth: {method}")
    print(f"Remote: {out}")
    print("SSH OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
