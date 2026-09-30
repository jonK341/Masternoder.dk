"""Per-user exchange daemon — venue selection, farming strategy, rented bot control."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONFIG_DIR = os.path.join(ex._DATA_DIR, "user_daemons")
_DEFAULTS_PATH = os.path.join(ex._BASE, "data", "exchange_user_daemon_defaults.json")

STRATEGIES = (
    "spatial_arbitrage",
    "cross_exchange_farm",
    "internal_vs_external",
    "ai_multi_venue",
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _user_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id or "default_user"))
    return os.path.join(_CONFIG_DIR, f"{safe}.json")


def _defaults() -> Dict[str, Any]:
    cfg = ex._read_json(_DEFAULTS_PATH, {})
    if not isinstance(cfg, dict):
        cfg = {}
    return {
        "enabled": True,
        "strategy": str(cfg.get("strategy") or "cross_exchange_farm"),
        "venues": list(cfg.get("venues") or ["binance", "okx", "bybit", "kucoin", "nonkyc"]),
        "symbols": list(cfg.get("symbols") or ["BTC", "ETH", "SOL"]),
        "agent_ids": list(cfg.get("agent_ids") or []),
        "auto_run_with_marketplace": bool(cfg.get("auto_run_with_marketplace", True)),
        "include_rentals": bool(cfg.get("include_rentals", True)),
        "include_owned": bool(cfg.get("include_owned", True)),
        "notional_usd": float(cfg.get("notional_usd") or 250),
    }


def get_config(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    path = _user_path(user_id)
    base = _defaults()
    if os.path.isfile(path):
        stored = ex._read_json(path, {})
        if isinstance(stored, dict):
            base.update({k: stored[k] for k in stored if k in base or k in (
                "updated_at", "last_run_at", "last_run_profit_usd", "last_scan",
            )})
            if stored.get("venues"):
                base["venues"] = list(stored["venues"])
            if stored.get("symbols"):
                base["symbols"] = list(stored["symbols"])
            if stored.get("agent_ids") is not None:
                base["agent_ids"] = list(stored.get("agent_ids") or [])
    from backend.services.external_exchange_connector_service import list_venues
    venues = list_venues()
    return {
        "success": True,
        "user_id": user_id,
        "config": base,
        "strategies": [{"id": s, "label": s.replace("_", " ").title()} for s in STRATEGIES],
        "available_venues": venues.get("venues") or [],
        "supported_symbols": (venues.get("supported_symbols") or ex._read_json(
            os.path.join(ex._BASE, "data", "exchange_connectors_config.json"), {}
        ).get("supported_symbols") or []),
    }


def save_config(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    cur = get_config(user_id)["config"]
    if "strategy" in payload:
        st = str(payload.get("strategy") or "").strip()
        if st in STRATEGIES:
            cur["strategy"] = st
    if "venues" in payload and isinstance(payload.get("venues"), list):
        cur["venues"] = [str(v).strip() for v in payload["venues"] if str(v).strip()]
    if "symbols" in payload and isinstance(payload.get("symbols"), list):
        cur["symbols"] = [str(s).upper() for s in payload["symbols"] if str(s).strip()]
    if "agent_ids" in payload and isinstance(payload.get("agent_ids"), list):
        cur["agent_ids"] = [str(a).strip() for a in payload["agent_ids"] if str(a).strip()]
    for key in ("enabled", "auto_run_with_marketplace", "include_rentals", "include_owned"):
        if key in payload:
            cur[key] = bool(payload.get(key))
    if payload.get("notional_usd") is not None:
        try:
            cur["notional_usd"] = max(10.0, float(payload.get("notional_usd")))
        except (TypeError, ValueError):
            pass
    cur["updated_at"] = _iso()
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    ex._write_json(_user_path(user_id), cur)
    ex._audit("user_daemon_config", user_id=user_id, venues=len(cur.get("venues") or []),
              symbols=len(cur.get("symbols") or []), strategy=cur.get("strategy"))
    return {"success": True, "config": cur}


def _agent_farm_params(agent: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    venues = list(agent.get("farm_venues") or cfg.get("venues") or [])
    symbols = list(agent.get("farm_symbols") or cfg.get("symbols") or [])
    strategy = str(agent.get("farm_strategy") or cfg.get("strategy") or "cross_exchange_farm")
    notional = float(agent.get("capital_usd") or cfg.get("notional_usd") or 250)
    return {"venues": venues, "symbols": symbols, "strategy": strategy, "notional_usd": notional}


def preview_farm(user_id: str, *, venues: Optional[List[str]] = None,
                 symbols: Optional[List[str]] = None, notional_usd: Optional[float] = None) -> Dict[str, Any]:
    cfg = get_config(user_id)["config"]
    v = venues or cfg.get("venues")
    s = symbols or cfg.get("symbols")
    n = float(notional_usd if notional_usd is not None else cfg.get("notional_usd") or 250)
    from backend.services.exchange_arbitrage_service import scan_opportunities
    scan = scan_opportunities(symbols=s, venues=v, notional_usd=n)
    top = (scan.get("opportunities") or [])[:8]
    return {
        "success": True,
        "scanned_at": scan.get("scanned_at"),
        "opportunity_count": scan.get("opportunity_count"),
        "profitable_count": scan.get("profitable_count"),
        "venues": v,
        "symbols": s,
        "notional_usd": n,
        "top_opportunities": top,
    }


def _select_agents(user_id: str, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    from backend.services import agent_marketplace_service as mkt
    data = mkt._read_user_agents(user_id)
    agents = list((data.get("agents") or {}).values())
    selected_ids = set(cfg.get("agent_ids") or [])
    rows = []
    for a in agents:
        if not a.get("enabled", True):
            continue
        is_rental = bool(a.get("rented"))
        if is_rental and not cfg.get("include_rentals", True):
            continue
        if not is_rental and not cfg.get("include_owned", True):
            continue
        if selected_ids and a.get("agent_id") not in selected_ids:
            continue
        try:
            from backend.services.exchange_rental_service import rental_gate
            if rental_gate(a):
                continue
        except Exception:
            pass
        rows.append(a)
    return rows


def run_user_daemon(user_id: str, *, volatility: Optional[float] = None) -> Dict[str, Any]:
    """Run one daemon cycle for the user's configured bots using live venue scans."""
    user_id = (user_id or "").strip() or "default_user"
    if not get_config(user_id)["config"].get("enabled", True):
        return {"success": False, "error": "daemon_disabled"}

    cfg = get_config(user_id)["config"]
    agents = _select_agents(user_id, cfg)
    if not agents:
        return {"success": False, "error": "no_agents", "hint": "Rent a bot or buy from marketplace first."}

    from backend.services import agent_marketplace_service as mkt
    from backend.services.exchange_arbitrage_service import scan_opportunities

    actions: List[Dict[str, Any]] = []
    total_profit = 0.0
    scan_cache: Dict[str, Any] = {}

    for agent in agents:
        fp = _agent_farm_params(agent, cfg)
        cache_key = "|".join(sorted(fp["venues"])) + ":" + "|".join(sorted(fp["symbols"]))
        if cache_key not in scan_cache:
            scan_cache[cache_key] = scan_opportunities(
                symbols=fp["symbols"], venues=fp["venues"], notional_usd=fp["notional_usd"],
            )
        scan = scan_cache[cache_key]
        opps = [o for o in (scan.get("opportunities") or []) if o.get("profitable")]
        venue_bonus = 0.0
        best = opps[0] if opps else None
        if best:
            venue_bonus = float(best.get("est_profit_usd") or 0)
            if fp["strategy"] == "internal_vs_external":
                venue_bonus *= 0.85
            elif fp["strategy"] == "ai_multi_venue":
                venue_bonus *= 1.15

        tick = mkt.run_user_agent_tick(user_id, agent["agent_id"], volatility=volatility)
        if tick.get("success") and (tick.get("action") or {}).get("live_execution"):
            total_profit += float((tick.get("action") or {}).get("profit_usd") or 0)
            actions.append({**tick, "agent_name": agent.get("name"), "farm": fp})
            continue
        if tick.get("success") and venue_bonus > 0:
            data = mkt._read_user_agents(user_id)
            ag = data.get("agents", {}).get(agent["agent_id"])
            if ag:
                ag["realized_profit_usd"] = round(float(ag.get("realized_profit_usd") or 0) + venue_bonus, 6)
                act = dict(ag.get("last_action") or {})
                act["venue_farm_bonus_usd"] = round(venue_bonus, 4)
                act["farm_venues"] = fp["venues"]
                act["best_spread"] = best
                ag["last_action"] = act
                mkt._write_user_agents(user_id, data)
                tick["action"] = act
                tick["realized_profit_usd"] = ag["realized_profit_usd"]
        if tick.get("success"):
            total_profit += float((tick.get("action") or {}).get("profit_usd") or 0)
            total_profit += float((tick.get("action") or {}).get("venue_farm_bonus_usd") or 0)
        actions.append({**tick, "agent_name": agent.get("name"), "farm": fp})

    stored = ex._read_json(_user_path(user_id), _defaults())
    stored["last_run_at"] = _iso()
    stored["last_run_profit_usd"] = round(total_profit, 4)
    stored["last_scan"] = {
        "opportunity_count": sum(int((s or {}).get("opportunity_count") or 0) for s in scan_cache.values()),
        "profitable_count": sum(int((s or {}).get("profitable_count") or 0) for s in scan_cache.values()),
    }
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    ex._write_json(_user_path(user_id), {**cfg, **stored})

    return {
        "success": True,
        "ran": len(actions),
        "total_profit_usd": round(total_profit, 4),
        "actions": actions,
        "config": cfg,
    }
