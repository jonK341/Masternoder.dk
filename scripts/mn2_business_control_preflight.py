#!/usr/bin/env python3
"""Business Control preflight — local or HTTP JSON report (exit 0 when hard checks pass)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _admin_key() -> str:
    k = (os.environ.get("EXCHANGE_ADMIN_KEY") or "").strip()
    if k:
        return k
    env_path = os.path.join(ROOT, ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("EXCHANGE_ADMIN_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    from scripts.daemon_env import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser(description="Business Control preflight")
    p.add_argument("--http", action="store_true", help="Also hit running app (needs --base + admin key)")
    p.add_argument("--base", default="", help="App base URL for --http")
    args = p.parse_args()

    from backend.services.business_control_preflight_service import run_http_preflight, run_preflight

    report: dict = {"local": run_preflight()}
    ok = bool(report["local"].get("success"))

    if args.http:
        base = (args.base or os.environ.get("BUSINESS_CONTROL_BASE") or "").strip()
        key = _admin_key()
        if not base or not key:
            report["http"] = {
                "success": False,
                "error": "need --base and EXCHANGE_ADMIN_KEY for --http",
            }
            ok = False
        else:
            report["http"] = run_http_preflight(base, key)
            ok = ok and bool(report["http"].get("success"))

    report["success"] = ok
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
