#!/usr/bin/env python3
"""One-shot tick for all local daemon engines (exchange + casino)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one tick on all bot engines")
    parser.add_argument("--include-casino", action="store_true",
                        help="Also tick casino agents (slow: loads Flask app)")
    parser.add_argument("--casino-dry-run", action="store_true",
                        help="Casino dry_run when --include-casino")
    parser.add_argument("--skip-exchange", action="store_true")
    args = parser.parse_args()

    results: dict = {}

    if not args.skip_exchange:
        try:
            import importlib.util
            path = os.path.join(ROOT, "scripts", "exchange_master_daemon.py")
            spec = importlib.util.spec_from_file_location("exchange_master_daemon", path)
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            results["exchange_master"] = mod.run_once(auto_sweep=False)
        except Exception as exc:
            results["exchange_master"] = {"success": False, "error": str(exc)}

    if args.include_casino:
        try:
            from backend.services import casino_agents_service as casino
            results["casino_agents"] = casino.run_all(dry_run=args.casino_dry_run)
        except Exception as exc:
            results["casino_agents"] = {"success": False, "error": str(exc)}

    print(json.dumps(results, indent=2, default=str))
    ok = all(isinstance(v, dict) and v.get("success", True) for v in results.values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
