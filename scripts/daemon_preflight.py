#!/usr/bin/env python3
"""One-shot health check before / during profit daemon runs."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_preflight(*, sync_binance: bool = True) -> Dict[str, Any]:
    from scripts.daemon_env import live_status

    blockers: List[str] = []
    warnings: List[str] = []
    out: Dict[str, Any] = {"success": True, "checked_at": _iso(), "blockers": blockers, "warnings": warnings}

    live = live_status()
    out["live"] = live
    if not live.get("success"):
        blockers.append(f"live_status: {live.get('error')}")
    elif live.get("mode") == "live" and not live.get("can_trade_external"):
        warnings.append("live mode but external arb needs 2+ credentialed venues")

    try:
        from scripts.daemon_env import load_dotenv
        from backend.services import exchange_secrets_vault_service as vault
        load_dotenv()
        if os.environ.get("EXCHANGE_VAULT_KEY", "").strip():
            for vid in ("binance", "nonkyc", "xeggex"):
                key = (os.environ.get(f"{vid.upper()}_API_KEY") or "").strip()
                sec = (os.environ.get(f"{vid.upper()}_API_SECRET") or "").strip()
                if key and sec and not vault.get_secret(f"{vid}_api_key"):
                    vault.set_secret(f"{vid}_api_key", key)
                    vault.set_secret(f"{vid}_api_secret", sec)
    except Exception:
        pass

    if sync_binance:
        try:
            from backend.services.exchange_binance_time_service import clock_status
            clock = clock_status()
            out["binance_clock"] = clock
            if not clock.get("clock_ok"):
                warnings.append(f"binance clock skew {clock.get('offset_ms')}ms — run w32tm /resync")
        except Exception as exc:
            out["binance_clock"] = {"success": False, "error": str(exc)}
            warnings.append(f"binance clock check failed: {exc}")

    try:
        from backend.services import casino_agents_service as casino_agents
        bankroll = casino_agents.ensure_agent_bankrolls()
        out["casino_bankroll"] = bankroll
        if int(bankroll.get("low_balance_agents") or 0) > 0 and not bankroll.get("topped_up"):
            warnings.append(f"{bankroll['low_balance_agents']} casino agents below min coins")
    except Exception as exc:
        out["casino_bankroll"] = {"success": False, "error": str(exc)}

    try:
        hb_path = os.path.join(ROOT, "logs", "daemon_all_profit_heartbeat.json")
        if os.path.isfile(hb_path):
            with open(hb_path, "r", encoding="utf-8") as f:
                out["last_heartbeat"] = json.load(f)
        else:
            warnings.append("no daemon heartbeat yet — start run_all_profit_daemons.cmd")
    except Exception as exc:
        warnings.append(f"heartbeat read failed: {exc}")

    out["success"] = len(blockers) == 0
    return out


def format_preflight(data: Dict[str, Any]) -> str:
    lines = [f"[preflight] ok={data.get('success')} mode={(data.get('live') or {}).get('mode', '?')}"]
    live = data.get("live") or {}
    if live.get("live_venue_count") is not None:
        lines.append(f"  venues_live={live.get('live_venue_count')} can_trade_external={live.get('can_trade_external')}")
    clock = data.get("binance_clock") or {}
    if clock.get("offset_ms") is not None:
        lines.append(f"  binance_clock_offset_ms={clock.get('offset_ms')} ok={clock.get('clock_ok')}")
    bank = data.get("casino_bankroll") or {}
    if bank.get("agent_count") is not None:
        lines.append(
            f"  casino_agents={bank.get('agent_count')} topped_up={bank.get('topped_up', 0)} "
            f"min_coins={bank.get('min_coins')}"
        )
    for w in data.get("warnings") or []:
        lines.append(f"  warn: {w}")
    for b in data.get("blockers") or []:
        lines.append(f"  BLOCK: {b}")
    return "\n".join(lines)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Profit daemon preflight checks")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    data = run_preflight()
    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(format_preflight(data))
    return 0 if data.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
