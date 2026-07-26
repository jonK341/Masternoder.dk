"""Public-safe 5D fleet progress monitor — no PII, no admin secrets."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_SENSITIVE_RE = re.compile(
    r"(paypal|email|@|api[_-]?key|secret|password|wallet|0x[a-fA-F0-9]{8,}|user_id)",
    re.I,
)


def monitor_public_enabled() -> bool:
    return os.environ.get("FLEET_PROGRESS_MONITOR_PUBLIC", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def embed_token_required() -> bool:
    return bool((os.environ.get("FLEET_MONITOR_EMBED_TOKEN") or "").strip())


def embed_authorized(got: str) -> bool:
    want = (os.environ.get("FLEET_MONITOR_EMBED_TOKEN") or "").strip()
    if not want:
        return True
    return bool((got or "").strip()) and got.strip() == want


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _scrub_text(text: str, *, max_len: int = 160) -> str:
    t = (text or "").strip()
    if _SENSITIVE_RE.search(t):
        return "Fleet activity signal"
    return t[:max_len]


def _coarse_profit_band(usd: float) -> str:
    v = float(usd or 0)
    sign = "+" if v >= 0 else "−"
    a = abs(v)
    if a < 0.5:
        return f"{sign}under $1"
    if a < 10:
        return f"{sign}~${int(round(a))}"
    if a < 100:
        return f"{sign}~${int(round(a / 5) * 5)}"
    if a < 1000:
        return f"{sign}~${int(round(a / 25) * 25)}"
    return f"{sign}$1k+"


def _sanitize_bot(fb: Dict[str, Any]) -> Dict[str, Any]:
    prog = fb.get("progression") or {}
    return {
        "id": _scrub_text(str(fb.get("id") or "bot"), max_len=48),
        "label": fb.get("label") or "Fleet",
        "kind": fb.get("kind") or "fleet",
        "type_label": fb.get("type_label") or "",
        "role_label": _scrub_text(str(fb.get("role_label") or ""), max_len=80),
        "enabled": bool(fb.get("enabled", True)),
        "last_tick_ok": None if not fb.get("last_run_at") else fb.get("last_run_ok") is not False,
        "level": int(prog.get("level") or 1),
        "rank_title": prog.get("rank_title") or "Recruit",
        "xp_progress_pct": float(prog.get("xp_progress_pct") or 0),
        "rewards_unlocked": int(prog.get("rewards_unlocked_count") or 0),
    }


def _activity_from_fleet_meta(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for h in (meta.get("history") or [])[-12:]:
        out.append(
            {
                "at": h.get("ran_at"),
                "kind": h.get("kind") or "fleet",
                "ok": bool(h.get("ok")),
                "headline": _scrub_text(
                    f"Fleet run {h.get('kind') or 'all'} — {'ok' if h.get('ok') else 'partial'}"
                ),
            }
        )
    lr = meta.get("last_results") or {}
    for kind, row in lr.items():
        if not isinstance(row, dict):
            continue
        bc = row.get("bot_count")
        okc = row.get("ok_count")
        if bc is None:
            continue
        out.append(
            {
                "at": meta.get("last_run_at"),
                "kind": kind,
                "ok": bool(row.get("success")),
                "headline": _scrub_text(f"{kind}: {okc}/{bc} bots reported ok"),
            }
        )
    return out[-20:]


def _public_audit_ticks(limit: int = 12) -> List[Dict[str, Any]]:
    try:
        from backend.services import crypto_exchange_service as ex

        tail = ex.get_audit_tail(limit=80).get("records") or []
    except Exception:
        return []
    safe_actions = {
        "swap",
        "spatial_arbitrage",
        "arb_tick",
        "fleet_tick",
        "risk_denied",
    }
    out: List[Dict[str, Any]] = []
    for rec in reversed(tail):
        action = str(rec.get("action") or "")
        if action not in safe_actions and "arb" not in action and "fleet" not in action:
            continue
        out.append(
            {
                "at": rec.get("ts") or rec.get("at"),
                "action": action,
                "headline": _scrub_text(f"Trade lane · {action.replace('_', ' ')}"),
                "amount_band": _coarse_profit_band(float(rec.get("amount_usd") or 0)),
            }
        )
        if len(out) >= limit:
            break
    return out


def build_narration(payload: Dict[str, Any]) -> str:
    ps = payload.get("progression") or {}
    trades = payload.get("trades") or {}
    fleet = payload.get("fleet") or {}
    mode = "paper simulation" if payload.get("paper_mode") else "live operations"
    return (
        f"Fleet progress monitor. Commander level {ps.get('commander_level', 1)}, "
        f"{ps.get('fleet_total_xp', 0)} total experience. "
        f"{fleet.get('active_bots', 0)} of {fleet.get('bot_count', 0)} bots active. "
        f"Aggregate trades {trades.get('total_trades', 0)}. "
        f"Profit band {trades.get('profit_band', 'under one dollar')}. "
        f"Running in {mode}."
    )


def public_fleet_progress_monitor(*, light: bool = True) -> Dict[str, Any]:
    from backend.services.trading_bots_control_service import _load_controls, list_bots

    controls = _load_controls()
    bots = list_bots(light=light)
    fleet_bots: List[Dict[str, Any]] = []
    sf: Dict[str, Any] = {}
    try:
        from backend.services.exchange_supervisor_fleet_service import fleet_overview
        from backend.services.trading_bots_control_service import _effective_enabled

        sf = fleet_overview(controls, persist_sync=light is False)
        for fb in sf.get("bots") or []:
            fb["enabled"] = _effective_enabled(
                {
                    "id": fb.get("id"),
                    "supervisor": fb.get("supervisor"),
                    "config_enabled": bool(fb.get("enabled", True)),
                },
                controls,
            )
            fleet_bots.append(_sanitize_bot(fb))
    except Exception:
        fleet_bots = [_sanitize_bot({"id": b["id"], "label": b.get("label"), **b}) for b in bots if b.get("fleet")]

    ps = sf.get("progression_summary") or {}
    meta = sf.get("meta") or {}
    total_trades = sum(int(b.get("trade_count") or 0) for b in bots)
    total_pnl = sum(float(b.get("total_pnl_usd") or 0) for b in bots)
    active_fleet = sum(1 for b in fleet_bots if b.get("enabled"))

    hot: List[str] = []
    try:
        from backend.services.exchange_profit_pair_search_service import read_index

        hot = [str(s).upper() for s in (read_index().get("hot_symbols") or [])[:8]]
    except Exception:
        hot = []

    paper = True
    try:
        from backend.services.exchange_arbitrage_service import live_enabled

        paper = not live_enabled()
    except Exception:
        pass

    payload: Dict[str, Any] = {
        "success": True,
        "generated_at": _iso(),
        "privacy": {
            "pii": False,
            "users_redacted": True,
            "financial_precision": "coarse_bands_only",
            "admin_fields": False,
        },
        "paper_mode": paper,
        "kill_switch": bool(controls.get("kill_switch")),
        "fleet": {
            "bot_count": len(fleet_bots),
            "active_bots": active_fleet,
            "mechanics_count": int(sf.get("mechanics_count") or 27),
            "last_run_at": meta.get("last_run_at"),
            "last_run_ok": meta.get("last_run_ok"),
            "bots": fleet_bots,
        },
        "progression": {
            "commander_level": int(ps.get("fleet_commander_level") or 1),
            "commander_rank": ps.get("fleet_commander_rank") or "Recruit",
            "fleet_total_xp": int(ps.get("fleet_total_xp") or 0),
            "avg_bot_level": float(ps.get("avg_bot_level") or 1),
            "rewards_unlocked": int(ps.get("total_rewards_unlocked") or 0),
            "xp_per_level": int(ps.get("xp_per_level") or 200),
        },
        "trades": {
            "total_trades": total_trades,
            "profit_band": _coarse_profit_band(total_pnl),
            "bot_count": len(bots),
        },
        "lanes": {"hot_symbols": hot},
        "activity": _activity_from_fleet_meta(meta) + _public_audit_ticks(),
        "dimensions_5d": {
            "x": "fleet lane spread",
            "y": "supervisor depth",
            "z": "reward tier height",
            "w": "time pulse",
            "v": "experience intensity",
        },
    }
    payload["narration"] = build_narration(payload)
    return payload
