#!/usr/bin/env python3
"""Smoke test: winnable pairs supervisor tick (no full Flask app when LITE_APP=1)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def main() -> int:
    from scripts.daemon_env import load_dotenv

    load_dotenv()
    from backend.services.exchange_winnable_pairs_service import enabled, load_config, run_winnable_pairs_tick
    from backend.services.trading_bots_control_service import _supervisor_by_id, _load_controls

    cfg = load_config()
    sup = _supervisor_by_id(_load_controls(), "sup_winnable")
    report = {
        "winnable_enabled": enabled(),
        "supervisor_enabled": bool(sup and sup.get("enabled", True)),
        "config": {k: cfg.get(k) for k in ("min_net_bps", "min_search_score", "max_executions_per_tick", "agent_id")},
    }
    if not report["winnable_enabled"] or not report["supervisor_enabled"]:
        report["tick"] = {"success": False, "error": "disabled"}
        print(json.dumps(report, indent=2))
        return 1

    tick = run_winnable_pairs_tick()
    report["tick"] = {
        "success": tick.get("success"),
        "winnable_count": tick.get("winnable_count"),
        "executed_count": tick.get("executed_count"),
        "error": tick.get("error"),
        "hot_symbols": (tick.get("profit_pair_search") or {}).get("hot_symbols"),
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if tick.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
