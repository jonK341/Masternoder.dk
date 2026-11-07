#!/usr/bin/env python3
"""SSH: move agent_treasury MN2 to preferred hosting wallet + optional collateral UTXO funding."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 900) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def build_remote(*, amount: float, slots: int, dry_run: bool) -> str:
    return f"""
set -e
cd {WEB}
export PYTHONPATH={WEB}
LITE_APP=1 .venv/bin/python - <<'PY'
import json, os, sys
os.chdir({WEB!r})
sys.path.insert(0, {WEB!r})

from backend.services.mn2_hosting_treasury_ops import (
    fund_collateral_utxos,
    preferred_wallet_user_id,
    transfer_agent_treasury_to_preferred,
)
from backend.services.mn2_masternode_service import get_service_status, list_collateral_outputs

AMOUNT = {float(amount)}
SLOTS = {int(slots)}
DRY_RUN = {str(dry_run)}

pref = preferred_wallet_user_id()
xfer = transfer_agent_treasury_to_preferred(AMOUNT, dry_run=DRY_RUN)
fund = fund_collateral_utxos(SLOTS, dry_run=DRY_RUN)
st = get_service_status(fresh=True)
co = list_collateral_outputs()

print(json.dumps({{
    "preferred_wallet_user_id": pref,
    "transfer": xfer,
    "fund_collateral": fund,
    "hosting_status": {{
        "checkout_open": st.get("checkout_open"),
        "slots_available": st.get("slots_available"),
        "collateral_outputs_available": st.get("collateral_outputs_available"),
    }},
    "collateral_scan": {{
        "count": co.get("count"),
        "total_mn2_available": co.get("total_mn2_available"),
        "error": co.get("error"),
    }},
}}, indent=2))
PY
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amount-mn2", type=float, default=0, help="Ledger transfer amount (0 = collateral * slots only if set)")
    parser.add_argument("--slots", type=int, default=4, help="Collateral UTXOs to fund after transfer")
    parser.add_argument(
        "--transfer-slots",
        type=int,
        default=0,
        help="If set, transfer MN2 = collateral_mn2 * this many slots (overrides --amount-mn2 when >0)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for deploy SSH password")
    args = parser.parse_args()

    amount = float(args.amount_mn2 or 0)
    if args.transfer_slots > 0:
        amount = 5000.0 * int(args.transfer_slots)

    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        remote = build_remote(amount=amount, slots=args.slots, dry_run=args.dry_run)
        out = sh(ssh, remote, timeout=600)
        print(out)
        start = out.rfind("\n{")
        if start < 0:
            start = out.find("{")
        payload = json.loads(out[start:].lstrip()) if start >= 0 else {}
        xfer_ok = (payload.get("transfer") or {}).get("success") if amount > 0 else True
        fund = payload.get("fund_collateral") or {}
        if args.dry_run:
            return 0
        fund_ok = args.slots <= 0 or fund.get("success") or (fund.get("funded") or 0) > 0
        if xfer_ok and fund_ok:
            return 0
        if xfer_ok and not fund_ok:
            return 2
        return 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
