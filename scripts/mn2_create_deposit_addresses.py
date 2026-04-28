#!/usr/bin/env python3
"""Create N MN2 deposit addresses via the daemon RPC and save as pool_1, pool_2, ...
Usage: python scripts/mn2_create_deposit_addresses.py [count]
Default count=1. Max 100. Requires MN2_RPC_* in env (or .env). Addresses are used when users request deposit-address.
"""
import os
import sys

# Load .env from project root so MN2_RPC_* are set
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(os.path.join(_root, ".env")):
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_root, ".env"))
    except ImportError:
        pass

def main():
    count = 1
    if len(sys.argv) > 1:
        try:
            count = max(1, min(int(sys.argv[1]), 100))
        except ValueError:
            print("Usage: python scripts/mn2_create_deposit_addresses.py [count]")
            sys.exit(2)
    os.chdir(_root)
    sys.path.insert(0, _root)
    from backend.services.mn2_wallet_service import create_deposit_addresses
    result = create_deposit_addresses(count)
    if result.get("success"):
        print(f"Created {result['count']} deposit address(es):")
        for item in result.get("created", []):
            print(f"  {item['user_id']}: {item['deposit_address']}")
        print("They will be assigned to users when they request deposit-address.")
        return 0
    else:
        print("Error:", result.get("error", "Unknown"))
        return 1

if __name__ == "__main__":
    sys.exit(main())
