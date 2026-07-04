"""Profit daemon monitor — heartbeat, payout, PPP summary for UI/API."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_HEARTBEAT = os.path.join(ex._BASE, "logs", "daemon_all_profit_heartbeat.json")
_STATE = os.path.join(ex._DATA_DIR, "profit_daemon_server_state.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_summary_kv(summary: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for part in (summary or "").split():
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip()
    return out


def _age_sec(ts: str) -> Optional[float]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


def _stale_threshold_sec() -> float:
    return float(os.environ.get("PROFIT_DAEMON_STALE_SEC", "300"))


def monitor_status() -> Dict[str, Any]:
    hb = ex._read_json(_HEARTBEAT, {})
    loops = hb.get("loops") if isinstance(hb.get("loops"), dict) else {}
    stale_sec = _stale_threshold_sec()
    loop_rows: List[Dict[str, Any]] = []
    any_recent = False

    for name in ("exchange", "fast", "casino"):
        row = loops.get(name) if isinstance(loops.get(name), dict) else {}
        updated = str(row.get("updated_at") or "")
        age = _age_sec(updated)
        recent = age is not None and age <= stale_sec
        any_recent = any_recent or recent
        parsed = _parse_summary_kv(str(row.get("summary") or ""))
        loop_rows.append({
            "loop": name,
            "updated_at": updated,
            "age_sec": round(age, 1) if age is not None else None,
            "stale": not recent,
            "summary": row.get("summary"),
            "metrics": parsed,
        })

    server_state = ex._read_json(_STATE, {})
    payout = {}
    treasury = {}
    ppp = {}
    try:
        from backend.services.exchange_payout_service import payout_status
        payout = payout_status()
    except Exception as exc:
        payout = {"success": False, "error": str(exc)}
    try:
        from backend.services.exchange_treasury_service import treasury_status
        treasury = treasury_status()
    except Exception as exc:
        treasury = {"success": False, "error": str(exc)}
    try:
        from backend.services.exchange_profit_path_service import profit_path_summary
        ppp = profit_path_summary(hours=24)
    except Exception as exc:
        ppp = {"success": False, "error": str(exc)}

    exchange_m = next((r for r in loop_rows if r["loop"] == "exchange"), {})
    em = exchange_m.get("metrics") or {}
    arb_exec = str(em.get("arb_exec") or "")
    m = re.match(r"(\d+)/(\d+)", arb_exec)
    arb_fills = int(m.group(1)) if m else 0
    arb_agents = int(m.group(2)) if m else 0

    return {
        "success": True,
        "host": os.environ.get("DEPLOY_HOST", "masternoder.dk"),
        "running": any_recent,
        "stale_threshold_sec": stale_sec,
        "mode": hb.get("mode") or server_state.get("mode"),
        "profile": hb.get("profile") or server_state.get("profile"),
        "heartbeat_updated_at": hb.get("updated_at"),
        "loops": loop_rows,
        "highlights": {
            "arb_exec": arb_exec or None,
            "arb_fills": arb_fills,
            "arb_agents": arb_agents,
            "best_bps": _float_or_none(em.get("best_bps")),
            "cross_actions": _int_or_none(em.get("cross_actions")),
            "ext_exec": _int_or_none(em.get("ext_exec")),
            "ai_exec": em.get("ai_exec"),
            "funded": em.get("funded"),
            "sweep": em.get("sweep"),
        },
        "payout": {
            "mode": payout.get("mode"),
            "auto_sweep": payout.get("auto_sweep"),
            "min_sweep_usd": payout.get("min_sweep_usd"),
            "paypal_live": (payout.get("paypal") or {}).get("live_enabled"),
            "paypal_sweepable_usd": payout.get("paypal_sweepable_usd"),
            "ready_to_sweep": payout.get("ready_to_sweep"),
        },
        "treasury": {
            "live_stash_usd": treasury.get("ledger_stashed_usd_live") or treasury.get("live_stash_usd"),
            "compound_enabled": treasury.get("compound_on_trade"),
        },
        "ppp_24h": {
            "fill_count": ppp.get("fill_count"),
            "profit_usd": ppp.get("profit_usd"),
            "hit_rate_pct": ppp.get("hit_rate_pct"),
        },
        "server": server_state,
        "checked_at": _iso(),
    }


def _float_or_none(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _int_or_none(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def record_server_install(*, profile: str = "max", mode: str = "live") -> Dict[str, Any]:
    state = {
        "installed_at": _iso(),
        "profile": profile,
        "mode": mode,
        "systemd_unit": "masternoder-profit-daemon.service",
    }
    ex._write_json(_STATE, state)
    return {"success": True, "state": state}
