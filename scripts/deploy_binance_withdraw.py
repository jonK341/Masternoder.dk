#!/usr/bin/env python3
"""Deploy Binance withdraw wiring to production."""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_BASE = "/var/www/html"
FILES = [
    "backend/services/exchange_binance_withdraw_service.py",
    "backend/services/exchange_payout_service.py",
    "backend/routes/crypto_exchange_routes.py",
    ".env.example",
    "tests/unit/test_exchange_binance_withdraw.py",
]


def main() -> int:
    print("=" * 70)
    print("DEPLOY BINANCE WITHDRAW WIRING")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    pw = require_deploy_pass()
    ssh, auth, _ = connect_deploy_ssh(pw)
    print(f"Connected ({auth})")
    sftp = ssh.open_sftp()
    deployed = 0
    for rel in FILES:
        local = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.isfile(local):
            print(f"  [SKIP] {rel}")
            continue
        remote = f"{REMOTE_BASE}/{rel.replace(chr(92), '/')}"
        remote_dir = os.path.dirname(remote)
        ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=10)
        with open(local, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        with sftp.file(remote, "w") as rf:
            rf.write(content)
        print(f"  [OK] {rel}")
        deployed += 1
    sftp.close()
    print(f"Deployed {deployed}/{len(FILES)} files")

    for svc in ("uwsgi-vidgenerator", "python-proxy", "uwsgi-vidgenerator-5001"):
        ssh.exec_command(f"systemctl restart {svc} 2>&1", timeout=30)
        time.sleep(2)
    print("Services restarted")
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
