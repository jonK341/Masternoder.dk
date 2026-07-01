#!/usr/bin/env python3
"""Check prod Binance payout wiring (masked, no secrets)."""
from __future__ import annotations

import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, _load_deploy_env_from_dotenv

REMOTE = r"""
import json, os
from pathlib import Path
for line in Path(".env").read_text(encoding="utf-8", errors="ignore").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
out = {}
for k in [
    "EXCHANGE_PAYOUT_BINANCE_ADDRESS",
    "EXCHANGE_PAYOUT_BINANCE_NETWORK",
    "EXCHANGE_PAYOUT_BINANCE_LIVE",
    "EXCHANGE_ARBITRAGE_LIVE",
]:
    val = os.environ.get(k) or ""
    if not val:
        out[k] = "(not set)"
    elif "ADDRESS" in k:
        out[k] = "(set, len=%d)" % len(val)
    else:
        out[k] = val
try:
    from backend.services.exchange_payout_service import payout_status
    st = payout_status()
    out["payout_binance"] = {
        k: st["binance"].get(k)
        for k in [
            "wired",
            "withdraw_address_masked",
            "withdraw_network",
            "withdraw_live_enabled",
            "sales_pool_usdt",
            "keys_present",
        ]
    }
except Exception as exc:
    out["status_err"] = str(exc)[:120]
print(json.dumps(out, indent=2))
"""


def main() -> int:
    _load_deploy_env_from_dotenv()
    ssh, auth, _ = connect_deploy_ssh(None)
    b64 = base64.b64encode(REMOTE.encode()).decode()
    cmd = (
        "cd /var/www/html && PYTHONPATH=/var/www/html python3 -c "
        f"\"import base64; exec(base64.b64decode('{b64}').decode())\""
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print("STDERR:", err[:300], file=sys.stderr)
    print("AUTH:", auth, file=sys.stderr)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
