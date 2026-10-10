#!/usr/bin/env python3
"""Phase 0: enable all Business Control supervisors + bots, kill switch off, run one tick.

Run on the app host (loads .env for EXCHANGE_ADMIN_KEY if using HTTP), or locally with
ADMIN_KEY env set:

  cd /var/www/html && python3 scripts/mn2_business_control_activate.py
  python3 scripts/mn2_business_control_activate.py --local   # import services directly
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
    k = (os.environ.get("EXCHANGE_ADMIN_KEY") or os.environ.get("COGS_ADMIN_REPORT_KEY") or "").strip()
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


def _api(base: str, key: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-Exchange-Admin-Key": key,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def activate_local(*, run_tick: bool, force: bool) -> dict:
    from backend.services.trading_bots_control_service import (
        business_overview,
        run_all_bots,
        set_bot_enabled,
        set_kill_switch,
        set_supervisor_enabled,
        _load_controls,
        _save_controls,
    )

    report: dict = {"mode": "local", "steps": []}

    set_kill_switch(False)
    report["steps"].append("kill_switch_off")

    controls = _load_controls()
    for s in controls.get("supervisors") or []:
        sid = s.get("id")
        if sid:
            set_supervisor_enabled(sid, True)
    report["steps"].append("supervisors_enabled")

    overrides = controls.get("bot_overrides") or {}
    if overrides:
        controls = _load_controls()
        controls["bot_overrides"] = {}
        _save_controls(controls)
        report["steps"].append("bot_overrides_cleared")
    else:
        report["steps"].append("bot_overrides_already_empty")

    ov_before = business_overview()
    for b in ov_before.get("bots") or []:
        if not b.get("enabled"):
            set_bot_enabled(b["id"], True)
    report["steps"].append("bots_enabled")

    ov = business_overview()
    report["overview"] = {
        "active_bots": ov.get("totals", {}).get("active_bots"),
        "bot_count": ov.get("totals", {}).get("bot_count"),
        "kill_switch": ov.get("kill_switch"),
        "supervisors": [
            {"id": s.get("id"), "enabled": s.get("enabled"), "active": s.get("active_bot_count")}
            for s in ov.get("supervisors") or []
        ],
    }

    if run_tick:
        report["run"] = run_all_bots(force=force)
        report["steps"].append("run_all_bots")

    return report


def activate_http(base: str, key: str, *, run_tick: bool, force: bool) -> dict:
    if not key:
        raise SystemExit("EXCHANGE_ADMIN_KEY not set")

    report: dict = {"mode": "http", "base": base, "steps": []}

    _api(base, key, "/api/exchange/control-board/kill-switch", "POST", {"on": False})
    report["steps"].append("kill_switch_off")

    ov = _api(base, key, "/api/exchange/control-board/overview")
    for s in ov.get("supervisors") or []:
        sid = s.get("id")
        if sid and not s.get("enabled", True):
            _api(base, key, "/api/exchange/control-board/supervisor", "POST",
                 {"supervisor_id": sid, "enabled": True})
    report["steps"].append("supervisors_enabled")

    for b in ov.get("bots") or []:
        if not b.get("enabled"):
            _api(base, key, "/api/exchange/control-board/bot", "POST",
                 {"bot_id": b["id"], "enabled": True})
    report["steps"].append("bots_enabled")

    ov2 = _api(base, key, "/api/exchange/control-board/overview")
    report["overview"] = {
        "active_bots": ov2.get("totals", {}).get("active_bots"),
        "bot_count": ov2.get("totals", {}).get("bot_count"),
        "kill_switch": ov2.get("kill_switch"),
    }

    if run_tick:
        report["run"] = _api(base, key, "/api/exchange/control-board/run", "POST", {"force": force})
        report["steps"].append("run_all_bots")

    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Business Control Phase 0 activation")
    p.add_argument("--local", action="store_true", help="Use in-process services (on app host)")
    p.add_argument("--base", default=os.environ.get("MN2_API_BASE", "http://127.0.0.1:5000"))
    p.add_argument("--no-run", action="store_true", help="Skip run_all_bots tick")
    p.add_argument("--force", action="store_true", help="Force cross-trade tick")
    args = p.parse_args()

    try:
        if args.local:
            from scripts.daemon_env import load_dotenv
            load_dotenv()
            report = activate_local(run_tick=not args.no_run, force=args.force)
        else:
            key = _admin_key()
            report = activate_http(args.base, key, run_tick=not args.no_run, force=args.force)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(json.dumps({"error": f"HTTP {e.code}", "body": body}, indent=2))
        raise SystemExit(1) from e

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
