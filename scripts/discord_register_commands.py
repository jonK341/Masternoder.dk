#!/usr/bin/env python3
"""Register global slash commands with Discord (run on server after deploy)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Register Discord slash commands")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads only")
    args = parser.parse_args()
    from backend.services.discord_setup_service import register_global_commands

    out = register_global_commands(dry_run=args.dry_run)
    print(json.dumps(out, indent=2))
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
