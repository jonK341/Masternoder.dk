#!/usr/bin/env python3
"""Deploy treasury sign-off code and record sign-off on production server.

Usage:
  python scripts/treasury_signoff_remote.py --approver "Jon" --cold-wallet MxColdAddr...
  python scripts/treasury_signoff_remote.py --approver "Jon" --cold-wallet MxCold... --skip-deploy
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import dotenv
    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Deploy + record treasury sign-off on server")
    p.add_argument("--approver", required=True)
    p.add_argument("--cold-wallet", required=True)
    p.add_argument("--hot-cap-mn2", type=float, default=None)
    p.add_argument("--max-batch-mn2", type=float, default=600000)
    p.add_argument("--notes", default="MN2_OPS §8.6 treasury sign-off")
    p.add_argument("--skip-deploy", action="store_true")
    p.add_argument("--require-reconcile", action="store_true")
    args = p.parse_args()

    if not args.skip_deploy:
        import subprocess
        print("== Deploy mn2_staking (treasury sign-off files) ==")
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "deploy.py"), "mn2_staking"],
            cwd=ROOT,
        )
        if r.returncode != 0:
            print("Deploy failed — fix deploy or use --skip-deploy if already uploaded.")
            return r.returncode

    host, user = deploy_host(), deploy_user()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=require_deploy_pass(), timeout=30)
    print(f"\n== Connected {user}@{host} ==\n")

    web = "/var/www/html"
    cmd = (
        f"cd {web} && ./venv/bin/python scripts/treasury_signoff.py "
        f"--approver {json.dumps(args.approver)} "
        f"--cold-wallet {json.dumps(args.cold_wallet)} "
        f"--max-batch-mn2 {args.max_batch_mn2} "
        f"--notes {json.dumps(args.notes)}"
    )
    if args.hot_cap_mn2 is not None:
        cmd += f" --hot-cap-mn2 {args.hot_cap_mn2}"
    if args.require_reconcile:
        cmd += " --require-reconcile"

    print("-- record sign-off on server --")
    out = sh(ssh, cmd, timeout=180)
    print(out)

    print("\n-- verify GET sign-off (localhost) --")
    verify = sh(
        ssh,
        f"curl -s http://127.0.0.1:5000/api/agents/treasury/sign-off 2>/dev/null || "
        f"curl -s http://127.0.0.1:5001/api/agents/treasury/sign-off",
    )
    print(verify)

    ssh.close()
    try:
        data = json.loads(verify)
        if data.get("signed"):
            print("\n[OK] Treasury sign-off is ACTIVE on production.")
            return 0
    except Exception:
        pass
    print("\n[WARN] Could not confirm sign-off via HTTP — check CLI output above.")
    return 0 if "success" in out and '"success": true' in out.replace(" ", "") else 1


if __name__ == "__main__":
    raise SystemExit(main())
