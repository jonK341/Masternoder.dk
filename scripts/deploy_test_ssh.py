#!/usr/bin/env python3
"""Test SSH deploy credentials — use before deploy.py if auth fails.

  python scripts/deploy_test_ssh.py --ask-pass
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass


def main() -> int:
    p = argparse.ArgumentParser(description="Test SSH to production deploy host")
    p.add_argument("--ask-pass", action="store_true")
    args = p.parse_args()
    pw = require_deploy_pass(force_prompt=args.ask_pass) if args.ask_pass else None
    if not pw and not args.ask_pass:
        from deploy_ssh_env import _load_deploy_pass_from_dotenv
        _load_deploy_pass_from_dotenv()
        pw = os.environ.get("DEPLOY_PASS") or None
    print(f"Testing {deploy_user()}@{deploy_host()} ...")
    ssh, method = connect_deploy_ssh(pw)
    _, stdout, _ = ssh.exec_command("hostname && pwd", timeout=15)
    print(stdout.read().decode(errors="replace").strip())
    print(f"OK — authenticated via {method}")
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
