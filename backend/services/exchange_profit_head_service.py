"""Profit daemon HEAD — steers arms, legs, and tools.

Anatomy
  Arm 1 ``hunter``     — wide BN↔NK spread hunt + backfill
  Arm 2 ``dual_farm``  — dual-venue farm + prefund
  Arm 3 ``courier``    — cross-venue quote balancer
  Tool ``latch``       — skew wait-then-strike
  Tool ``closer``      — finish half-legs + dust harvest
  Leg 1 ``pbook``      — top5 map / techniques ledger
  Leg 2 ``grid``       — maker ladders (thin-quote = fully quiet)

Head Top 10 (see docs/ideation/2026-11-13-profit-daemon-body-head-top10.md):
  1 quote gate · 2 budget · 3 arm enable · 4 leg enable · 5 quarantine
  6 kill-shot pick · 7 prefund hint · 8 heartbeat · 9 learn/log · 10 kill switch
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONTROL_PATH = os.path.join(ex._DATA_DIR, "profit_head_control.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_head_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "profit_head_ledger.jsonl")
_HEARTBEAT_PATH = os.path.join(
    os.path.dirname(ex._DATA_DIR), "..", "logs", "daemon_all_profit_heartbeat.json"
)
# Prefer repo-root logs when running under /var/www/html
_HEARTBEAT_CANDIDATES = [
    os.path.join(ex._BASE, "logs", "daemon_all_profit_heartbeat.json"),
    os.path.join(ex._DATA_DIR, "daemon_all_profit_heartbeat.json"),
]

_LIMBS = ("hunter", "dual_farm", "courier", "latch", "closer", "pbook", "grid")
_ARMS = ("hunter", "dual_farm", "courier")
_TOOLS = ("latch", "closer")
_LEGS = ("pbook", "grid")
_HEAD_AGENT_ID = "arb_profit_head"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_control() -> Dict[str, Any]:
    return {
        "manual_body_pause": False,
        "limbs": {
            "hunter": {"enabled": True},
            "dual_farm": {"enabled": True},
            "courier": {"enabled": True},
            "latch": {"enabled": True},
            "closer": {"enabled": True},
            "pbook": {"enabled": True},
            "grid": {"enabled": True},
        },
        "quote_budget": {
            "arm_reserve_usd": 0.0,
            "leg_reserve_usd": 0.0,
            "notes": "",
        },
        "kill_shot": None,
        "prefund_hint": None,
        "courier_hint": None,
        "updated_at": None,
        "last_decision": None,
    }


def load_control() -> Dict[str, Any]:
    raw = ex._read_json(_CONTROL_PATH, {})
    base = _default_control()
    if not isinstance(raw, dict):
        return base
    base.update({k: raw.get(k, base.get(k)) for k in base.keys()})
    limbs = dict(base["limbs"])
    for name in _LIMBS:
        row = (raw.get("limbs") or {}).get(name) if isinstance(raw.get("limbs"), dict) else None
        if isinstance(row, dict):
            limbs[name] = {"enabled": bool(row.get("enabled", True))}
    base["limbs"] = limbs
    return base


def save_control(ctrl: Dict[str, Any]) -> Dict[str, Any]:
    ctrl = dict(ctrl)
    ctrl["updated_at"] = _iso()
    ex._write_json(_CONTROL_PATH, ctrl)
    return ctrl


def limb_allowed(name: str) -> bool:
    """Arms/legs call this at tick start. Manual body pause disables all except pbook map."""
    ctrl = load_control()
    if ctrl.get("manual_body_pause"):
        return str(name) == "pbook"
    row = (ctrl.get("limbs") or {}).get(str(name))
    if isinstance(row, dict):
        return bool(row.get("enabled", True))
    return True


def get_kill_shot() -> Optional[Dict[str, Any]]:
    ks = load_control().get("kill_shot")
    return ks if isinstance(ks, dict) else None


def clear_kill_shot() -> None:
    ctrl = load_control()
    ctrl["kill_shot"] = None
    save_control(ctrl)


def get_prefund_hint() -> Optional[Dict[str, Any]]:
    """Head assignment for the hunter arm: raise quote toward an unfunded edge."""
    hint = load_control().get("prefund_hint")
    return hint if isinstance(hint, dict) else None


def clear_prefund_hint() -> None:
    ctrl = load_control()
    ctrl["prefund_hint"] = None
    save_control(ctrl)


def get_courier_hint() -> Optional[Dict[str, Any]]:
    hint = load_control().get("courier_hint")
    return hint if isinstance(hint, dict) else None


def set_courier_hint(hint: Optional[Dict[str, Any]]) -> None:
    ctrl = load_control()
    ctrl["courier_hint"] = hint if isinstance(hint, dict) else None
    save_control(ctrl)


def _append_head_event(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "head"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _learn(profit_usd: float, *, note: str = "") -> Dict[str, Any]:
    try:
        from backend.services import exchange_arbitrage_service as arb
        from backend.services.exchange_agent_learning_service import learn_from_profit

        acct = arb.read_account(_HEAD_AGENT_ID)
        if not acct.get("skills"):
            acct["skills"] = [
                "quote_gate", "budget", "arm_control", "leg_control",
                "quarantine", "kill_shot", "prefund", "courier", "latch", "closer",
                "heartbeat", "learning", "kill_switch",
            ]
            acct.setdefault("skill_proficiency", {})
        out = learn_from_profit(acct, max(0.0, float(profit_usd or 0)))
        acct["ticks"] = int(acct.get("ticks") or 0) + 1
        acct["last_action"] = {"note": note, "ts": _iso(), "profit_usd": profit_usd}
        arb.write_account(acct)
        return {"ok": True, **out}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _read_heartbeat() -> Dict[str, Any]:
    for path in _HEARTBEAT_CANDIDATES:
        if os.path.isfile(path):
            data = ex._read_json(path, {})
            if isinstance(data, dict):
                return data
    return {}


def _venue_quote_snapshot() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        from backend.services import exchange_venue_api_service as vapi
    except Exception as exc:
        return {"error": str(exc)}
    for venue in ("binance", "nonkyc", "xeggex"):
        try:
            if not vapi.venue_has_credentials(venue):
                out[venue] = {"ok": False, "reason": "no_credentials"}
                continue
            quote = str(vapi.venue_quote_asset(venue) or "").upper()
            bals = vapi.parse_spot_balances(venue, dry_run=False, force_refresh=True) or {}
            free = float(bals.get(quote) or 0) if quote else 0.0
            out[venue] = {"ok": True, "quote": quote, "free": round(free, 4)}
        except Exception as exc:
            out[venue] = {"ok": False, "error": str(exc)[:120]}
    return out


def _pbook_top() -> Optional[Dict[str, Any]]:
    path = os.path.join(ex._DATA_DIR, "profit_order_book.json")
    data = ex._read_json(path, {})
    if not isinstance(data, dict):
        return None
    top5 = data.get("top5") or []
    if not top5:
        return None
    row = top5[0] if isinstance(top5[0], dict) else None
    return row


def _search_hot_symbols() -> List[str]:
    path = os.path.join(ex._DATA_DIR, "profit_pair_search_index.json")
    data = ex._read_json(path, {})
    if not isinstance(data, dict):
        return []
    hot = data.get("hot_symbols") or data.get("symbols") or []
    if isinstance(hot, list):
        return [str(s).upper() for s in hot[:12]]
    return []


def set_manual_body_pause(paused: bool) -> Dict[str, Any]:
    ctrl = load_control()
    ctrl["manual_body_pause"] = bool(paused)
    save_control(ctrl)
    _append_head_event("kill_switch", manual_body_pause=bool(paused))
    return {"success": True, "manual_body_pause": bool(paused)}


def run_head_tick(*, force: bool = False) -> Dict[str, Any]:
    """One head cycle: read body signals, set limb controls, optional kill-shot, learn, log."""
    ctrl = load_control()
    quotes = _venue_quote_snapshot()
    hb = _read_heartbeat()
    loops = hb.get("loops") if isinstance(hb.get("loops"), dict) else {}
    top = _pbook_top()
    hot = _search_hot_symbols()

    bn_free = float(((quotes.get("binance") or {}).get("free") or 0))
    nk_free = float(((quotes.get("nonkyc") or {}).get("free") or 0))
    total_free = bn_free + nk_free
    thin = total_free < 12.0  # ~2 × default grid order size

    decisions: List[str] = []
    limbs = {name: {"enabled": True} for name in _LIMBS}

    # 10 — kill switch (manual body pause)
    if ctrl.get("manual_body_pause"):
        for name in _LIMBS:
            limbs[name]["enabled"] = name == "pbook"
        decisions.append("kill_switch:body_paused")
    else:
        # 1 — quote gate: grid fully quiet when thin; arms may still hunt if any quote left
        if thin:
            limbs["grid"]["enabled"] = False
            decisions.append("quote_gate:grid_quiet")
        else:
            limbs["grid"]["enabled"] = True
            decisions.append("quote_gate:grid_ok")

        # 3/4 — arm/leg/tool enable from loop skip signals
        hunter_sum = str(((loops.get("hunter") or {}).get("summary") or ""))
        dual_sum = str(((loops.get("dual_farm") or {}).get("summary") or ""))
        if "regime_skew_too_wide" in hunter_sum:
            limbs["hunter"]["enabled"] = True
            limbs["latch"]["enabled"] = True
            decisions.append("arm:hunter_skew_watch")
            decisions.append("tool:latch_armed")
        if "no_qualifying_external_edge" in dual_sum:
            decisions.append("arm:dual_no_edge")
        # Courier on when venues are lopsided OR Binance free quote is behind floor
        if bn_free < 12.0 or (total_free >= 12.0 and min(bn_free, nk_free) < max(4.0, total_free * 0.35)):
            limbs["courier"]["enabled"] = True
            decisions.append("arm:courier_imbalance")
            if bn_free < 12.0:
                decisions.append("keep:binance_current")
        limbs["closer"]["enabled"] = True
        limbs["pbook"]["enabled"] = True  # map always on
        decisions.append("leg:pbook_map_on")
        decisions.append("tool:closer_on")

    # 2 — quote budget split
    arm_reserve = round(total_free * 0.6, 4) if not thin else round(total_free, 4)
    leg_reserve = round(max(0.0, total_free - arm_reserve), 4)
    quote_budget = {
        "arm_reserve_usd": arm_reserve,
        "leg_reserve_usd": leg_reserve,
        "total_free_usd": round(total_free, 4),
        "thin": thin,
        "bn_free": round(bn_free, 4),
        "nk_free": round(nk_free, 4),
        "notes": "60/40 arms/legs when funded; arms take all when thin",
    }
    decisions.append(f"budget:arms={arm_reserve}:legs={leg_reserve}")

    # 5 — quarantine nudge (grid leg owns state; head logs awareness)
    try:
        from backend.services.exchange_grid_bot_service import quarantined_assets

        qa = list(quarantined_assets().keys())
    except Exception:
        qa = []
    if qa:
        decisions.append(f"quarantine:n={len(qa)}")

    # 6 — kill-shot: one funded strike from pbook top when edge is real + fundable
    kill_shot = None
    prefund_hint = None
    if not ctrl.get("manual_body_pause") and top and top.get("funded") and float(top.get("net_bps") or 0) >= 20:
        kill_shot = {
            "arm": "hunter",
            "symbol": top.get("symbol"),
            "route": top.get("route"),
            "net_bps": top.get("net_bps"),
            "est_profit_usd": top.get("est_profit_usd"),
            "reason": "pbook_funded_top",
            "hot": hot[:4],
        }
        decisions.append(f"kill_shot:{kill_shot.get('symbol')}:{kill_shot.get('net_bps')}")
    elif not ctrl.get("manual_body_pause") and top and float(top.get("net_bps") or 0) >= 50 and not top.get("funded"):
        # 7 — prefund hint instead of empty exec
        prefund_hint = {
            "symbol": top.get("symbol"),
            "technique": top.get("best_technique") or "prefund_buy_quote",
            "net_bps": top.get("net_bps"),
            "reason": "unfunded_top_edge",
        }
        decisions.append(f"prefund_hint:{prefund_hint.get('symbol')}")

    courier_hint = ctrl.get("courier_hint") if isinstance(ctrl.get("courier_hint"), dict) else None
    if bn_free < 12.0 and not ctrl.get("manual_body_pause"):
        # Keep Binance current: force courier destination even if hint is stale/missing.
        courier_hint = {
            "from_venue": "nonkyc" if nk_free >= bn_free else "binance",
            "to_venue": "binance",
            "amount_usd": round(max(0.0, 12.0 - bn_free), 2),
            "reason": "keep_binance_current",
            "poor_free": round(bn_free, 4),
            "rich_free": round(nk_free, 4),
        }
        decisions.append("courier_hint:nonkyc→binance")
    elif courier_hint and not ctrl.get("manual_body_pause"):
        decisions.append(
            f"courier_hint:{(courier_hint.get('from_venue') or '?')}→{(courier_hint.get('to_venue') or '?')}"
        )

    # Preserve operator limb overrides only if they set manual flags in control — we rewrite enables.
    ctrl["limbs"] = limbs
    ctrl["quote_budget"] = quote_budget
    ctrl["kill_shot"] = kill_shot
    ctrl["prefund_hint"] = prefund_hint
    ctrl["courier_hint"] = courier_hint
    ctrl["last_decision"] = {
        "ts": _iso(),
        "decisions": decisions,
        "thin": thin,
        "total_free_usd": round(total_free, 4),
        "hot_symbols": hot[:6],
        "quarantined": qa[:8],
    }
    save_control(ctrl)

    # 9 — file + learn
    _append_head_event(
        "head_tick",
        decisions=decisions,
        thin=thin,
        total_free_usd=round(total_free, 4),
        kill_shot=kill_shot,
        prefund_hint=prefund_hint,
        courier_hint=courier_hint,
        limbs=limbs,
    )
    learn = _learn(
        float((kill_shot or {}).get("est_profit_usd") or 0) if kill_shot else 0.0,
        note=";".join(decisions[:6]),
    )

    # 8 — honest body rollup for callers
    summary = (
        f"thin={thin} free=${total_free:.2f} "
        f"arms={int(limbs['hunter']['enabled'])}{int(limbs['dual_farm']['enabled'])}{int(limbs['courier']['enabled'])} "
        f"tools={int(limbs['latch']['enabled'])}{int(limbs['closer']['enabled'])} "
        f"legs={int(limbs['pbook']['enabled'])}{int(limbs['grid']['enabled'])} "
        f"kill={kill_shot.get('symbol') if kill_shot else '-'} "
        f"dec={len(decisions)}"
    )

    state = {
        "updated_at": _iso(),
        "summary": summary,
        "decisions": decisions,
        "quotes": quotes,
        "kill_shot": kill_shot,
        "prefund_hint": prefund_hint,
        "courier_hint": courier_hint,
        "limbs": limbs,
        "quote_budget": quote_budget,
        "learning": learn,
        "hot_symbols": hot[:8],
    }
    ex._write_json(_STATE_PATH, state)

    return {
        "success": True,
        "limb": "head",
        "name": "head",
        "summary": summary,
        "decisions": decisions,
        "limbs": limbs,
        "kill_shot": kill_shot,
        "prefund_hint": prefund_hint,
        "courier_hint": courier_hint,
        "quote_budget": quote_budget,
        "quotes": quotes,
        "learning": learn,
        "manual_body_pause": bool(ctrl.get("manual_body_pause")),
    }
