#!/usr/bin/env python3
"""
MN2 reconciliation: compare ledger net (deposits - withdrawals - shop_payment) with daemon wallet balance.
Run from project root: python scripts/mn2_reconcile.py
Set MN2_RPC_* in env (or .env) to compare with daemon getbalance. See docs/MN2_OPS.md.
"""
import os
import sys
import json

# Load .env from project root if available
try:
    import dotenv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv.load_dotenv(os.path.join(root, ".env"))
except Exception:
    pass

def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    root = _project_root()
    ledger_path = os.path.join(root, "data", "mn2_ledger.json")
    if not os.path.exists(ledger_path):
        print("Ledger not found:", ledger_path)
        sys.exit(1)
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    total_deposits = sum(e.get("amount", 0) for e in entries if e.get("type") == "deposit")
    total_withdrawals = sum(e.get("amount", 0) for e in entries if e.get("type") == "withdrawal")
    total_shop = sum(e.get("amount", 0) for e in entries if e.get("type") == "shop_payment")
    ledger_net = total_deposits - total_withdrawals - total_shop
    print("MN2 Ledger reconciliation")
    print("  Total deposits:    ", total_deposits)
    print("  Total withdrawals:", total_withdrawals)
    print("  Total shop_payment:", total_shop)
    print("  Ledger net (in-app):", ledger_net)
    # Optional: RPC getbalance
    if os.environ.get("MN2_RPC_URL") or os.environ.get("MN2_RPC_PASSWORD"):
        try:
            sys.path.insert(0, root)
            from backend.services.mn2_rpc_client import getbalance
            r = getbalance()
            if r.get("error"):
                print("  Wallet balance (RPC): error —", r.get("error"))
            else:
                wallet = r.get("result") or 0
                print("  Wallet balance (RPC):", wallet)
                diff = ledger_net - wallet
                if abs(diff) > 0.0001:
                    print("  Difference (ledger - wallet):", diff)
                else:
                    print("  Match (within 0.0001)")
        except Exception as e:
            print("  Wallet balance (RPC): skip —", e)
    else:
        print("  (Set MN2_RPC_* in env to compare with daemon getbalance)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
