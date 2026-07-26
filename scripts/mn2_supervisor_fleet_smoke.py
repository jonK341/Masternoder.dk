#!/usr/bin/env python3
"""Phase 5 smoke: supervisor fleet tick (local or HTTP run-fleet).

Exit 0 when fleet tick reports success.

  python3 scripts/mn2_supervisor_fleet_smoke.py --local
  python3 scripts/mn2_supervisor_fleet_smoke.py --base http://127.0.0.1:5000 --kind risk
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


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


def smoke_local(kind: str | None) -> dict:
    from backend.services.trading_bots_control_service import run_supervisor_fleet

    return run_supervisor_fleet(kind=kind)


def smoke_http(base: str, key: str, kind: str | None) -> dict:
    url = base.rstrip("/") + "/api/exchange/control-board/run-fleet"
    body = {"kind": kind} if kind else {}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"X-Exchange-Admin-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    p = argparse.ArgumentParser(description="Supervisor fleet smoke test")
    p.add_argument("--local", action="store_true", help="Run via Python services (not HTTP)")
    p.add_argument("--base", default="http://127.0.0.1:5000", help="API base for HTTP mode")
    p.add_argument("--kind", default="", help="Optional fleet kind (analytics, extended_profit, …)")
    args = p.parse_args()
    kind = (args.kind or "").strip() or None

    try:
        if args.local:
            out = smoke_local(kind)
        else:
            key = _admin_key()
            if not key:
                print(json.dumps({"success": False, "error": "missing EXCHANGE_ADMIN_KEY"}))
                return 2
            out = smoke_http(args.base, key, kind)
    except urllib.error.HTTPError as exc:
        print(exc.read().decode()[:500])
        return 1
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1

    print(json.dumps(out, indent=2)[:8000])
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
