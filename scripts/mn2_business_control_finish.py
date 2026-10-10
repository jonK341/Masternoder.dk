#!/usr/bin/env python3
"""Phase 6 finish — unit tests, preflight, deploy checklist (optional deploy).

Typical release on app host:

  cd /var/www/html
  DAEMON_QUIET=1 LITE_APP=1 python3 scripts/mn2_business_control_finish.py --local
  python3 scripts/mn2_business_control_finish.py --deploy

With remote HTTP verify (after deploy):

  python3 scripts/mn2_business_control_finish.py --http --base $BUSINESS_CONTROL_BASE
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

PHASE6_UNIT_TESTS = (
    "tests/unit/test_business_control_preflight.py",
    "tests/unit/test_trading_bots_control.py",
    "tests/unit/test_exchange_control_board.py",
    "tests/unit/test_supervisor_fleet.py",
)


def _run_pytest(tests: tuple[str, ...]) -> dict:
    cmd = [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = (proc.stdout or "") + (proc.stderr or "")
    lines = tail.strip().splitlines()
    summary = lines[-1] if lines else ""
    return {
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "summary": summary,
        "output_tail": "\n".join(lines[-12:]),
    }


def _run_preflight(*, http: bool, base: str) -> dict:
    from scripts.daemon_env import load_dotenv

    load_dotenv()
    from backend.services.business_control_preflight_service import run_http_preflight, run_preflight

    out: dict = {"local": run_preflight()}
    ok = bool(out["local"].get("success"))
    if http:
        key = (os.environ.get("EXCHANGE_ADMIN_KEY") or "").strip()
        b = (base or os.environ.get("BUSINESS_CONTROL_BASE") or "").strip()
        if not b or not key:
            out["http"] = {"success": False, "error": "missing base or EXCHANGE_ADMIN_KEY"}
            ok = False
        else:
            out["http"] = run_http_preflight(b, key)
            ok = ok and bool(out["http"].get("success"))
    out["success"] = ok
    return out


def _run_deploy() -> dict:
    deploy_py = os.path.join(ROOT, "scripts", "deploy.py")
    cmd = [sys.executable, deploy_py, "business_control"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
    return {
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "output_tail": "\n".join(tail[-20:]),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Business Control Phase 6 finish pipeline")
    p.add_argument("--local", action="store_true", help="Alias for default (tests + local preflight)")
    p.add_argument("--skip-tests", action="store_true")
    p.add_argument("--skip-preflight", action="store_true")
    p.add_argument("--http", action="store_true", help="HTTP preflight after local checks")
    p.add_argument("--base", default="", help="App base for --http")
    p.add_argument("--deploy", action="store_true", help="Run scripts/deploy.py business_control")
    p.add_argument("--prod-tick", action="store_true", help="Run local supervisor fleet smoke (risk only)")
    args = p.parse_args()

    report: dict = {"phase": 6, "steps": {}}
    ok = True

    if not args.skip_tests:
        report["steps"]["unit_tests"] = _run_pytest(PHASE6_UNIT_TESTS)
        ok &= report["steps"]["unit_tests"]["success"]

    if not args.skip_preflight:
        report["steps"]["preflight"] = _run_preflight(http=args.http, base=args.base)
        ok &= report["steps"]["preflight"]["success"]

    if args.prod_tick:
        from backend.services.trading_bots_control_service import run_supervisor_fleet

        tick = run_supervisor_fleet(kind="risk")
        report["steps"]["prod_tick"] = tick
        ok &= bool(tick.get("success"))

    if args.deploy:
        report["steps"]["deploy"] = _run_deploy()
        ok &= report["steps"]["deploy"]["success"]

    report["success"] = ok
    report["deploy_hint"] = "python3 scripts/deploy.py business_control"
    report["activate_hint"] = "python3 scripts/mn2_business_control_activate.py --local"
    print(json.dumps(report, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
