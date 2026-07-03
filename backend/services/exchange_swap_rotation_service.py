"""Swap rotation — analyze funding gaps and suggest/execute capital moves for live arb.

Reuses ``can_fund_arb_leg`` / ``max_funded_notional_usd`` and internal USDC↔USDT swaps.
External venue orders require ``rotation_live_enabled`` (config or EXCHANGE_ROTATION_LIVE=1).
Auto-execute when ``rotation_auto_execute`` or ``EXCHANGE_ROTATION_AUTO=1``.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_venue_api_service as vapi
from backend.services.exchange_profit_path_service import load_config, search_paths


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_STATE_PATH = os.path.join(ex._DATA_DIR, "rotation_auto_state.json")
_CONNECTORS_PATH = os.path.join(ex._BASE, "data", "exchange_connectors_config.json")
_EXTENDED_PROFIT_PATH = os.path.join(ex._BASE, "data", "exchange_extended_profit_config.json")
_DEDUPE_MINUTES = 30
_TYPE_ORDER = {
    "internal_stable_swap": 0,
    "reduce_notional": 1,
    "external_market_buy": 2,
    "external_market_sell": 2,
}


def rotation_live_enabled() -> bool:
    cfg = load_config()
    if cfg.get("rotation_live_enabled") is True:
        return True
    return os.environ.get("EXCHANGE_ROTATION_LIVE", "").strip().lower() in ("1", "true", "yes", "on")


def rotation_auto_execute_enabled() -> bool:
    cfg = load_config()
    if cfg.get("rotation_auto_execute") is True:
        return True
    return os.environ.get("EXCHANGE_ROTATION_AUTO", "").strip().lower() in ("1", "true", "yes", "on")


def _min_sell_leg_usd() -> float:
    return float(load_config().get("min_sell_leg_usd") or 25)


def _active_sell_leg_symbols(venue_id: str) -> frozenset[str]:
    """Symbols currently used as sell-leg base on this venue (live scan + recent PPP skips)."""
    venue = str(venue_id or "").lower()
    symbols: set[str] = set()
    try:
        from backend.services import exchange_arbitrage_service as arb

        scan = arb.scan_opportunities(
            symbols=["DOGE", "XRP", "BTC", "ETH", "SOL", "LINK", "LTC", "AVAX"],
            venues=["binance", "nonkyc"],
            notional_usd=25,
        )
        for opp in scan.get("opportunities") or []:
            if str(opp.get("sell_venue") or "").lower() == venue:
                sym = str(opp.get("symbol") or "").upper()
                if sym:
                    symbols.add(sym)
    except Exception:
        pass
    try:
        rows = search_paths(hours=6, limit=200).get("paths") or []
        for row in rows:
            if row.get("skip_reason") not in ("insufficient_venue_balance", "insufficient_balance"):
                continue
            v = row.get("venues") or {}
            if str(v.get("sell") or "").lower() != venue:
                continue
            sym = str(row.get("symbol") or "").upper()
            if sym:
                symbols.add(sym)
    except Exception:
        pass
    return frozenset(symbols)


def _protected_sell_assets(venue_id: str) -> frozenset[str]:
    """Base coins that must not be sold for quote shortfall (sell-leg inventory reserve)."""
    min_usd = _min_sell_leg_usd()
    active = _active_sell_leg_symbols(venue_id)
    protected: set[str] = set(active)
    for usd_val, asset, _qty, _px in _sellable_base_on_venue(venue_id, min_usd=0):
        sym = str(asset or "").upper()
        if usd_val < min_usd or sym in active:
            protected.add(sym)
    return frozenset(protected)


def _load_rotation_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_rotation_state(state: Dict[str, Any]) -> None:
    state["updated_at"] = _iso()
    ex._write_json(_STATE_PATH, state)


def _action_fingerprint(action: Dict[str, Any]) -> str:
    atype = str(action.get("type") or "")
    if atype == "internal_stable_swap":
        parts = [
            atype,
            str(action.get("wallet_user_id") or ""),
            str(action.get("symbol") or ""),
            str(action.get("quote") or ""),
            str(action.get("side") or ""),
        ]
    elif atype == "reduce_notional":
        parts = [atype, str(action.get("venue_id") or ""), str(action.get("suggested_notional_usd") or "")]
    else:
        parts = [
            atype,
            str(action.get("venue_id") or ""),
            str(action.get("symbol") or ""),
            str(action.get("side") or ""),
            str(action.get("market") or ""),
            str(action.get("quote") or ""),
        ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _venue_asset_key(action: Dict[str, Any]) -> str:
    atype = str(action.get("type") or "")
    venue = str(action.get("venue_id") or action.get("wallet_user_id") or "")
    sym = str(action.get("symbol") or action.get("quote") or "")
    side = str(action.get("side") or atype)
    market = str(action.get("market") or "")
    return f"{venue}|{sym}|{side}|{market}"


def _dedupe_skip(action: Dict[str, Any], state: Dict[str, Any]) -> Optional[str]:
    """Return skip reason when action should not re-run yet."""
    now = datetime.now(timezone.utc)
    fp = _action_fingerprint(action)
    fail_hash = str(state.get("last_failure_hash") or "")
    fail_at = _parse_ts(str(state.get("last_failure_at") or ""))
    if fail_hash == fp and fail_at and (now - fail_at) < timedelta(minutes=_DEDUPE_MINUTES):
        return "recent_failure_dedupe"

    amount = float(action.get("amount_usd") or action.get("amount") or action.get("suggested_notional_usd") or 0)
    asset_key = _venue_asset_key(action)
    for entry in reversed(state.get("recent") or []):
        if not isinstance(entry, dict):
            continue
        entry_at = _parse_ts(str(entry.get("ts") or ""))
        if not entry_at or (now - entry_at) >= timedelta(minutes=_DEDUPE_MINUTES):
            continue
        if str(entry.get("asset_key") or "") != asset_key:
            continue
        prev_amt = float(entry.get("amount_usd") or 0)
        if prev_amt > 0 and amount > 0:
            diff_pct = abs(amount - prev_amt) / max(prev_amt, amount)
            if diff_pct <= 0.20:
                return "venue_asset_cooldown"
    return None


def _parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _record_rotation_attempt(action: Dict[str, Any], state: Dict[str, Any], *, success: bool, skip_reason: str = "") -> None:
    fp = _action_fingerprint(action)
    amount = float(action.get("amount_usd") or action.get("amount") or action.get("suggested_notional_usd") or 0)
    entry = {
        "hash": fp,
        "ts": _iso(),
        "asset_key": _venue_asset_key(action),
        "amount_usd": round(amount, 2),
        "type": str(action.get("type") or ""),
        "success": success,
        "skip_reason": skip_reason,
    }
    recent = [e for e in (state.get("recent") or []) if isinstance(e, dict)][-40:]
    recent.append(entry)
    state["recent"] = recent
    state["last_executed_hash"] = fp
    state["last_executed_at"] = _iso()
    if success:
        state.pop("last_failure_hash", None)
        state.pop("last_failure_at", None)
    else:
        state["last_failure_hash"] = fp
        state["last_failure_at"] = _iso()
    _save_rotation_state(state)


def _cap_action_amount(action: Dict[str, Any], max_usd: float) -> Dict[str, Any]:
    capped = dict(action)
    for key in ("amount_usd", "amount"):
        if key in capped and capped[key]:
            capped[key] = round(min(float(capped[key]), float(max_usd)), 2)
    return capped


def _apply_reduce_notional(action: Dict[str, Any]) -> Dict[str, Any]:
    """Lower configured notional to fit venue quote balance."""
    cap = round(float(action.get("suggested_notional_usd") or 0), 2)
    venue = str(action.get("venue_id") or "")
    if cap <= 0:
        return {"success": False, "error": "invalid_cap"}

    updated: List[str] = []
    cfg = ex._read_json(_CONNECTORS_PATH, {})
    if isinstance(cfg, dict):
        prev = float(cfg.get("paper_trade_usd") or 0)
        if prev > cap:
            cfg["paper_trade_usd"] = cap
            updated.append("connectors.paper_trade_usd")
        for agent in cfg.get("arbitrage_agents") or []:
            if not isinstance(agent, dict):
                continue
            venues = list(agent.get("venues") or [])
            if venue and venue not in venues and venue != "internal":
                continue
            agent_notion = float(agent.get("paper_trade_usd") or prev or cap)
            if agent_notion > cap:
                agent["paper_trade_usd"] = cap
                updated.append(f"agent.{agent.get('id')}")
        ex._write_json(_CONNECTORS_PATH, cfg)

    ext = ex._read_json(_EXTENDED_PROFIT_PATH, {})
    if isinstance(ext, dict):
        for name, scfg in (ext.get("strategies") or {}).items():
            if not isinstance(scfg, dict):
                continue
            notion = float(scfg.get("notional_usd") or 0)
            venues = list(scfg.get("venues") or [])
            if notion > cap and (not venue or venue in venues or not venues):
                scfg["notional_usd"] = cap
                updated.append(f"extended.{name}")
        ex._write_json(_EXTENDED_PROFIT_PATH, ext)

    return {
        "success": bool(updated) or cap > 0,
        "already_applied": not bool(updated),
        "mode": "config",
        "cap_usd": cap,
        "updated": updated,
        "venue_id": venue,
    }


def _current_net_bps() -> Optional[float]:
    try:
        from backend.services.exchange_extended_profit_service import read_arb_threshold_state

        state = read_arb_threshold_state()
        best = state.get("best_net_bps")
        if best is not None:
            return float(best)
    except Exception:
        pass
    return None


def _record_rotation_baseline(action: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
    try:
        from backend.services.exchange_profit_baseline_service import record_baseline_trade

        order = (exec_res.get("order") or exec_res.get("result") or {})
        return record_baseline_trade(
            predicted={
                "action_label": action.get("label"),
                "amount_usd": action.get("amount_usd") or action.get("amount") or action.get("suggested_notional_usd"),
                "expected_unlock_bps": action.get("priority_score"),
                "top25_items": action.get("top25_items") or [],
            },
            executed={
                "success": exec_res.get("success"),
                "mode": exec_res.get("mode"),
                "fill_usd": exec_res.get("cap_usd") or action.get("amount_usd") or action.get("suggested_notional_usd"),
                "order_id": str(order.get("order_id") or order.get("id") or ""),
                "trade_id": str(order.get("trade_id") or order.get("quote_id") or ""),
            },
            source="rotation",
            route={
                "agent_id": str(action.get("agent_id") or ""),
                "symbol": str(action.get("symbol") or ""),
                "buy_venue": str(action.get("venue_id") or action.get("wallet_user_id") or ""),
                "sell_venue": "",
            },
            net_bps_at_exec=_current_net_bps(),
        )
    except Exception:
        return None


def _pick_auto_action(actions: List[Dict[str, Any]], allowed_types: List[str]) -> Optional[Dict[str, Any]]:
    live = rotation_live_enabled()
    candidates = [a for a in actions if str(a.get("type") or "") in allowed_types]
    if not live:
        candidates = [a for a in candidates if str(a.get("type") or "") != "external_market_buy"
                        and str(a.get("type") or "") != "external_market_sell"]
    if not candidates:
        return None
    candidates.sort(key=lambda a: (_TYPE_ORDER.get(str(a.get("type") or ""), 9), -_action_score(a)))
    return candidates[0]


def _rotation_log_fields(action: Dict[str, Any]) -> Dict[str, str]:
    """Pair/venue/market fields for daemon logging."""
    venue = str(action.get("venue_id") or action.get("wallet_user_id") or "")
    sym = str(action.get("symbol") or "")
    market = str(action.get("market") or "")
    if not market and sym and venue:
        try:
            resolved = vapi.resolve_market(venue, sym, action.get("quote"))
            if resolved.get("ok"):
                market = str(resolved.get("market") or "")
        except Exception:
            pass
    return {"venue_id": venue, "symbol": sym, "market": market}


def maybe_auto_rotation(exchange_res: Dict[str, Any]) -> Dict[str, Any]:
    """After exchange tick: suggest and optionally auto-execute top rotation action."""
    plat = exchange_res.get("platform") or {}
    results = plat.get("results") or {}
    arb = results.get("arbitrage") or {}
    executed = int(arb.get("executed_count") or 0)

    rot = suggest_swap_actions(hours=6, limit=3)
    actions = rot.get("actions") or []
    if not actions:
        return {"skipped": True, "reason": "no_actions"}

    top = actions[0]
    high_priority = str(top.get("priority") or "") in ("critical", "high")
    if executed > 0 and not high_priority:
        return {"skipped": True, "reason": "arb_executed"}

    if not rotation_auto_execute_enabled():
        log_rotation_to_ppp(actions, arb_executed=executed)
        return {"skipped": True, "reason": "auto_disabled", "suggested": top.get("label")}

    cfg = load_config()
    allowed = list(cfg.get("rotation_auto_types") or [
        "internal_stable_swap", "external_market_buy", "external_market_sell", "reduce_notional",
    ])
    max_usd = float(cfg.get("rotation_auto_max_usd_per_tick") or 100)
    action = _pick_auto_action(actions, allowed)
    if not action:
        log_rotation_to_ppp(actions, arb_executed=executed)
        return {"skipped": True, "reason": "no_eligible_action"}

    capped = _cap_action_amount(action, max_usd)
    if str(capped.get("type") or "") in ("external_market_buy", "external_market_sell"):
        venue = str(capped.get("venue_id") or "")
        sym = str(capped.get("symbol") or "")
        side = str(capped.get("side") or "buy")
        usd = float(capped.get("amount_usd") or 0)
        qty = float(capped.get("quantity") or 0)
        spec = vapi.market_order_for_leg(
            venue, side, sym, usd,
            quote=capped.get("quote"),
            quantity=qty if qty > 0 else None,
        )
        if not spec.get("ok"):
            reason = str(spec.get("error") or "pair_not_supported")
            log_fields = _rotation_log_fields(capped)
            return {
                "skipped": True,
                "reason": reason,
                "action": capped.get("label"),
                **log_fields,
            }
        capped = {**capped, **{k: spec[k] for k in ("market", "quote", "quantity") if k in spec}}

    state = _load_rotation_state()
    skip = _dedupe_skip(capped, state)
    if skip:
        log_fields = _rotation_log_fields(capped)
        return {"skipped": True, "reason": skip, "action": capped.get("label"), **log_fields}

    log_fields = _rotation_log_fields(capped)

    dry_run = False
    exec_res = execute_rotation(capped, dry_run=dry_run)
    success = bool(exec_res.get("success"))
    if exec_res.get("already_applied"):
        success = True
    _record_rotation_attempt(capped, state, success=success, skip_reason=str(exec_res.get("error") or exec_res.get("reason") or ""))

    baseline_id = exec_res.get("baseline_id") if success else None

    log_rotation_to_ppp(actions, arb_executed=executed)
    if baseline_id:
        try:
            from backend.services.exchange_profit_path_service import record_event

            record_event(
                phase="rotation",
                agent_id="swap_rotation",
                strategy="funding_rotation",
                decision="fill" if success else "attempt",
                notional_usd=float(capped.get("amount_usd") or capped.get("suggested_notional_usd") or 0),
                execution={
                    "action_count": len(actions),
                    "top_action": capped.get("label"),
                    "top_type": capped.get("type"),
                    "rotation_live_enabled": rotation_live_enabled(),
                    "auto_executed": True,
                    "success": success,
                    "baseline_id": baseline_id,
                },
            )
        except Exception:
            pass

    return {
        "auto_executed": True,
        "success": success,
        "action": capped.get("label"),
        "mode": exec_res.get("mode"),
        "baseline_id": baseline_id,
        "already_applied": bool(exec_res.get("already_applied")),
        "skip_reason": None if success else str(exec_res.get("error") or exec_res.get("reason") or "failed"),
        **log_fields,
    }


def _agent_config(agent_id: str) -> Optional[Dict[str, Any]]:
    from backend.services import external_exchange_connector_service as conn

    for agent in conn.load_connectors_config().get("arbitrage_agents") or []:
        if isinstance(agent, dict) and str(agent.get("id") or "") == agent_id:
            return agent
    return None


def _resolve_route(
    agent_id: str,
    symbol: str,
) -> Tuple[str, str, float, float]:
    """Return buy_venue, sell_venue, buy_ask, notional from ledger or fresh scan."""
    sym = str(symbol or "").upper()
    rows = search_paths(agent_id=agent_id, symbol=sym or None, hours=6, limit=20).get("paths") or []
    for row in reversed(rows):
        if row.get("skip_reason") != "insufficient_venue_balance":
            continue
        v = row.get("venues") or {}
        buy_v = str(v.get("buy") or "")
        sell_v = str(v.get("sell") or "")
        if buy_v and sell_v:
            notion = float(row.get("notional_usd") or 0)
            return buy_v, sell_v, 0.0, notion

    acct = None
    try:
        from backend.services.exchange_arbitrage_service import read_account

        acct = read_account(agent_id)
    except Exception:
        pass
    last = (acct or {}).get("last_action") or {}
    best = last.get("best") if isinstance(last.get("best"), dict) else {}
    if best.get("symbol") and (not sym or str(best["symbol"]).upper() == sym):
        return (
            str(best.get("buy_venue") or ""),
            str(best.get("sell_venue") or ""),
            float(best.get("buy_ask") or 0),
            float(best.get("notional_usd") or last.get("max_funded_usd") or 0),
        )

    agent = _agent_config(agent_id)
    venues = list((agent or {}).get("venues") or ["binance", "nonkyc"])
    symbols = [sym] if sym else [str(s).upper() for s in ((agent or {}).get("symbols") or ["BTC"])]
    from backend.services import exchange_arbitrage_service as arb

    scan = arb.scan_opportunities(symbols=symbols, venues=venues)
    for opp in scan.get("opportunities") or []:
        if sym and str(opp.get("symbol") or "").upper() != sym:
            continue
        return (
            str(opp.get("buy_venue") or ""),
            str(opp.get("sell_venue") or ""),
            float(opp.get("buy_ask") or 0),
            float(opp.get("notional_usd") or 0),
        )
    return "", "", 0.0, 0.0


def analyze_funding_gaps(
    agent_id: str,
    symbol: str,
    notional_usd: float,
    *,
    buffer_pct: float = 0.03,
) -> Dict[str, Any]:
    """From PPP skip reasons + live balances, return which arb leg is short."""
    sym = str(symbol or "").upper()
    buy_v, sell_v, buy_ask, ledger_notion = _resolve_route(agent_id, sym)
    notional = float(notional_usd or ledger_notion or 0)
    if notional <= 0:
        agent = _agent_config(agent_id)
        from backend.services import external_exchange_connector_service as conn

        notional = float(
            (agent or {}).get("paper_trade_usd")
            or conn.load_connectors_config().get("paper_trade_usd")
            or 75.0
        )

    if buy_ask <= 0 and sym:
        tick = None
        try:
            from backend.services import external_exchange_connector_service as conn

            tick = conn.fetch_ticker(buy_v or "binance", sym)
        except Exception:
            tick = None
        if tick:
            buy_ask = float(tick.get("ask") or tick.get("last") or 0)
        if buy_ask <= 0:
            buy_ask = float(ex._price_usd(sym) or 0)

    qty = round(notional / buy_ask, 8) if buy_ask > 0 else 0.0
    buy_chk = (
        vapi.can_fund_arb_leg(buy_v, sym, "buy", qty=qty, notional_usd=notional, buffer_pct=buffer_pct)
        if buy_v
        else {"ok": False, "error": "no_buy_venue"}
    )
    sell_chk = (
        vapi.can_fund_arb_leg(sell_v, sym, "sell", qty=qty, notional_usd=notional, buffer_pct=buffer_pct)
        if sell_v
        else {"ok": False, "error": "no_sell_venue"}
    )
    max_funded = 0.0
    if buy_v and sell_v and buy_ask > 0:
        max_funded = vapi.max_funded_notional_usd(
            sym, buy_v, sell_v, buy_ask, configured_usd=notional, buffer_pct=buffer_pct,
        )

    short_legs: List[Dict[str, Any]] = []
    if not buy_chk.get("ok"):
        short_legs.append({"leg": "buy", "venue_id": buy_v, **{k: buy_chk[k] for k in buy_chk if k not in ("ok", "venue_id")}})
    if not sell_chk.get("ok"):
        short_legs.append({"leg": "sell", "venue_id": sell_v, **{k: sell_chk[k] for k in sell_chk if k not in ("ok", "venue_id")}})

    return {
        "success": True,
        "agent_id": agent_id,
        "symbol": sym,
        "notional_usd": round(notional, 2),
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "buy_ask": round(buy_ask, 8) if buy_ask else 0,
        "quantity": qty,
        "max_funded_usd": round(max_funded, 2),
        "funded_ok": bool(buy_chk.get("ok")) and bool(sell_chk.get("ok")),
        "buy_leg": buy_chk,
        "sell_leg": sell_chk,
        "short_legs": short_legs,
        "analyzed_at": _iso(),
    }


_STABLES = frozenset({"USDT", "USDC", "BUSD", "DAI", "TUSD", "USDD"})


def _order_error(res: Dict[str, Any]) -> str:
    try:
        from backend.services.exchange_venue_api_service import extract_order_error
        return extract_order_error(res)
    except Exception:
        return str(res.get("error") or "")


def _sellable_base_on_venue(venue_id: str, *, min_usd: float = 5.0) -> List[Tuple[float, str, float, float]]:
    """Return [(usd_value, asset, qty, px), …] sorted by USD value desc."""
    bals = vapi.parse_spot_balances(venue_id, dry_run=False)
    out: List[Tuple[float, str, float, float]] = []
    for asset, bal in (bals or {}).items():
        sym = str(asset or "").upper()
        qty = float(bal or 0)
        if qty <= 0 or sym in _STABLES:
            continue
        px = float(ex._price_usd(sym) or 0)
        if px <= 0:
            continue
        usd = qty * px
        if usd >= min_usd:
            out.append((usd, sym, qty, px))
    out.sort(key=lambda row: row[0], reverse=True)
    return out


def _quote_shortfall_action(
    venue_id: str,
    quote_asset: str,
    short_usd: float,
    *,
    reason: str,
    priority: str = "high",
    score: float = 0,
    top25: Optional[List[str]] = None,
    configured_usd: float = 0,
) -> Optional[Dict[str, Any]]:
    """Acquire quote on a venue — prefer lower notional; never sell protected sell-leg inventory."""
    quote = str(quote_asset or vapi.venue_quote_asset(venue_id)).upper()
    gap = round(max(5.0, float(short_usd)), 2)
    free_quote = float(vapi.parse_spot_balances(venue_id, dry_run=False).get(quote) or 0)
    protected = _protected_sell_assets(venue_id)

    if free_quote >= 10 and configured_usd > free_quote:
        return _reduce_notional_action(
            venue_id, quote, free_quote, configured_usd, score=score * 0.85,
        )

    for usd_val, asset, qty, px in _sellable_base_on_venue(venue_id, min_usd=2.0):
        if str(asset or "").upper() in protected:
            continue
        min_reserve = _min_sell_leg_usd()
        max_sell_usd = round(usd_val - min_reserve, 2)
        if max_sell_usd < 5:
            continue
        sell_usd = round(min(gap * 1.08, usd_val * 0.92, max_sell_usd), 2)
        if sell_usd < 5:
            continue
        sell_qty = round(min(qty * 0.92, sell_usd / px), 8)
        if sell_qty <= 0:
            continue
        spec = vapi.market_order_for_leg(
            venue_id, "sell", asset, sell_usd, quote=quote, quantity=sell_qty,
        )
        if not spec.get("ok"):
            continue
        act = _external_buy_action(
            venue_id, asset, "sell",
            amount_usd=sell_usd,
            qty=spec["quantity"],
            reason=f"Sell {asset}→{quote}: {reason}",
            priority=priority,
            score=score,
            top25=top25,
            market=spec.get("market"),
            quote=quote,
        )
        act["label"] = f"Sell {asset} on {venue_id} ({spec.get('market')}) for {quote} ~${sell_usd:.0f}"
        act["funding_target"] = quote
        return act

    if free_quote >= 10 and configured_usd > free_quote:
        return _reduce_notional_action(
            venue_id, quote, free_quote, configured_usd, score=score * 0.85,
        )
    return None


def _action_score(action: Dict[str, Any]) -> float:
    base = float(action.get("priority_score") or 0)
    pri = {"critical": 100, "high": 50, "medium": 20, "low": 5}.get(str(action.get("priority") or ""), 10)
    return base + pri


def _stable_internal_swap_action(
    from_asset: str,
    to_asset: str,
    amount_usd: float,
    *,
    reason: str,
    priority: str = "high",
    score: float = 0,
    top25: Optional[List[str]] = None,
) -> Dict[str, Any]:
    amt = round(max(1.0, float(amount_usd)), 2)
    return {
        "type": "internal_stable_swap",
        "priority": priority,
        "priority_score": score,
        "label": f"Internal {from_asset}→{to_asset} ~${amt:.0f}",
        "wallet_user_id": "exchange_sales_pool",
        "symbol": to_asset if from_asset in ("USDC", "USDT") else from_asset,
        "side": "buy" if from_asset in ("USDC", "USDT") else "sell",
        "quote": from_asset if from_asset in ("USDC", "USDT") else to_asset,
        "amount_usd": amt,
        "amount": amt,
        "reason": reason,
        "top25_items": top25 or [],
        "dry_run_safe": True,
    }


def _external_buy_action(
    venue_id: str,
    symbol: str,
    side: str,
    *,
    amount_usd: float,
    qty: float,
    reason: str,
    priority: str = "high",
    score: float = 0,
    top25: Optional[List[str]] = None,
    market: Optional[str] = None,
    quote: Optional[str] = None,
) -> Dict[str, Any]:
    sym = str(symbol).upper()
    side_l = str(side).lower()
    trade_asset = sym
    resolved = vapi.resolve_market(venue_id, sym, quote)
    mkt = market or (resolved.get("market") if resolved.get("ok") else "")
    quote_asset = quote or (resolved.get("quote") if resolved.get("ok") else vapi.venue_quote_asset(venue_id))
    mkt_suffix = f" ({mkt})" if mkt else ""
    return {
        "type": "external_market_buy" if side_l == "buy" else "external_market_sell",
        "priority": priority,
        "priority_score": score,
        "label": f"{'Buy' if side_l == 'buy' else 'Sell'} {trade_asset} on {venue_id}{mkt_suffix} ~${amount_usd:.0f}",
        "venue_id": venue_id,
        "symbol": sym,
        "side": side_l,
        "quote": str(quote_asset or "").upper(),
        "market": mkt,
        "amount_usd": round(amount_usd, 2),
        "quantity": round(qty, 8) if qty > 0 else 0,
        "reason": reason,
        "top25_items": top25 or [],
        "requires_rotation_live": True,
        "dry_run_safe": True,
    }


def _reduce_notional_action(
    venue_id: str,
    quote_asset: str,
    free_usd: float,
    configured_usd: float,
    *,
    score: float,
) -> Dict[str, Any]:
    cap = round(max(10.0, free_usd * 0.95), 2)
    return {
        "type": "reduce_notional",
        "priority": "medium",
        "priority_score": score,
        "label": f"Lower notional to ${cap:.0f} (fits {venue_id} {quote_asset} ~${free_usd:.0f})",
        "venue_id": venue_id,
        "suggested_notional_usd": cap,
        "configured_notional_usd": round(configured_usd, 2),
        "reason": "quote_balance_caps_live_notional",
        "top25_items": ["binance_quote_cap", "skip_reason_funding"],
        "dry_run_safe": True,
        "advisory_only": True,
    }


def suggest_swap_actions(
    *,
    hours: Optional[float] = None,
    limit: int = 12,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ranked swap/rotation actions from PPP skips + live venue balances."""
    cfg = load_config()
    lookback = float(hours if hours is not None else cfg.get("rotation_lookback_hours") or 24)
    rows = search_paths(hours=lookback, limit=3000, agent_id=agent_id).get("paths") or []
    funding_rows = [
        r for r in rows
        if r.get("skip_reason") in ("insufficient_venue_balance", "insufficient_balance")
    ]

    gap_counts: Counter = Counter()
    route_meta: Dict[str, Dict[str, Any]] = {}
    for r in funding_rows:
        v = r.get("venues") or {}
        sym = str(r.get("symbol") or "")
        buy_v = str(v.get("buy") or "")
        sell_v = str(v.get("sell") or "")
        aid = str(r.get("agent_id") or "")
        key = f"{aid}|{sym}|{buy_v}|{sell_v}"
        gap_counts[key] += 1
        route_meta[key] = {
            "agent_id": aid,
            "symbol": sym,
            "buy_venue": buy_v,
            "sell_venue": sell_v,
            "notional_usd": float(r.get("notional_usd") or 0),
        }

    actions: List[Dict[str, Any]] = []
    seen_labels: set = set()

    for key, count in gap_counts.most_common(8):
        meta = route_meta[key]
        aid = meta["agent_id"]
        sym = meta["symbol"]
        notion = meta["notional_usd"]
        if not aid or not sym:
            continue
        gaps = analyze_funding_gaps(aid, sym, notion)
        for leg in gaps.get("short_legs") or []:
            venue = str(leg.get("venue_id") or "")
            side = str(leg.get("leg") or "")
            asset = str(leg.get("asset") or "")
            need = float(leg.get("need") or 0)
            free = float(leg.get("free") or 0)
            short_usd = max(0.0, need - free) if side == "buy" else max(0.0, (need - free) * float(gaps.get("buy_ask") or ex._price_usd(sym) or 1))
            if short_usd < 5 and side == "buy":
                short_usd = max(5.0, need - free)
            elif short_usd < 5:
                short_usd = 5.0
            qty = float(gaps.get("quantity") or 0)
            act: Optional[Dict[str, Any]] = None
            if side == "buy" and venue != "internal":
                quote = asset or vapi.venue_quote_asset(venue)
                act = _quote_shortfall_action(
                    venue, quote, short_usd,
                    reason=f"{count} recent funding skips on buy leg ({quote})",
                    score=float(count),
                    top25=["skip_reason_funding", "arb_exec_zero"],
                    configured_usd=float(gaps.get("notional_usd") or notion),
                )
            elif side == "sell" and venue != "internal":
                spec = vapi.market_order_for_leg(venue, "buy", sym, short_usd)
                if not spec.get("ok"):
                    continue
                act = _external_buy_action(
                    venue, sym, "buy",
                    amount_usd=short_usd,
                    qty=spec["quantity"],
                    reason=f"{count} recent funding skips on sell leg ({asset})",
                    score=float(count),
                    top25=["skip_reason_funding", "nonkyc_doge_low" if asset == "DOGE" else "arb_exec_zero"],
                    market=spec.get("market"),
                    quote=spec.get("quote"),
                )
            else:
                continue
            if not act:
                continue
            lbl = act["label"]
            if lbl not in seen_labels:
                seen_labels.add(lbl)
                actions.append(act)

        max_f = float(gaps.get("max_funded_usd") or 0)
        if max_f > 10 and notion > max_f + 5:
            buy_v = meta["buy_venue"]
            quote = vapi.venue_quote_asset(buy_v) if buy_v else "USDC"
            act = _reduce_notional_action(buy_v, quote, max_f, notion, score=float(count) * 0.5)
            if act["label"] not in seen_labels:
                seen_labels.add(act["label"])
                actions.append(act)

    # Venue balance heuristics (Binance USDC cap, NonKYC DOGE, quote imbalance)
    venue_ids = list(cfg.get("balance_summary_venues") or ["binance", "nonkyc"])
    from backend.services import external_exchange_connector_service as conn

    default_notion = float(conn.load_connectors_config().get("paper_trade_usd") or 75.0)
    for vid in venue_ids:
        if not vapi.venue_has_credentials(vid):
            continue
        bals = vapi.parse_spot_balances(vid, dry_run=False)
        quote = vapi.venue_quote_asset(vid)
        free_q = float(bals.get(quote) or 0)
        if 0 < free_q < default_notion and free_q < 100:
            act = _reduce_notional_action(vid, quote, free_q, default_notion, score=3.0)
            if act["label"] not in seen_labels:
                seen_labels.add(act["label"])
                actions.append(act)
        if vid == "nonkyc":
            doge = float(bals.get("DOGE") or 0)
            doge_usd = doge * float(ex._price_usd("DOGE") or 0)
            if doge_usd < 25 and vapi.venue_supports_symbol("nonkyc", "DOGE"):
                need_usd = max(25.0 - doge_usd, 10.0)
                # Stronger priority when inventory is far below sell-leg minimum.
                doge_score = 8.0 if doge_usd < 15 else 6.5 if doge_usd < 20 else 5.0
                spec = vapi.market_order_for_leg("nonkyc", "buy", "DOGE", need_usd)
                if spec.get("ok"):
                    act = _external_buy_action(
                        "nonkyc", "DOGE", "buy",
                        amount_usd=need_usd,
                        qty=spec["quantity"],
                        reason=f"NonKYC DOGE ${doge_usd:.2f} below $25 sell-leg minimum (prefund: prefund_arb_legs.py --live --symbol DOGE)",
                        priority="critical" if doge_usd < 15 else "high",
                        score=doge_score,
                        top25=["nonkyc_doge_low", "skip_reason_funding"],
                        market=spec.get("market"),
                        quote=spec.get("quote"),
                    )
                    if act["label"] not in seen_labels:
                        seen_labels.add(act["label"])
                        actions.append(act)

    quotes: List[Dict[str, Any]] = []
    for vid in venue_ids:
        if not vapi.venue_has_credentials(vid):
            continue
        quote = vapi.venue_quote_asset(vid)
        free = float(vapi.parse_spot_balances(vid, dry_run=False).get(quote) or 0)
        quotes.append({"venue_id": vid, "quote_asset": quote, "free_quote": free})
    if len(quotes) >= 2:
        rich = max(quotes, key=lambda q: q["free_quote"])
        poor = min(quotes, key=lambda q: q["free_quote"])
        if rich["free_quote"] > 30 and poor["free_quote"] < rich["free_quote"] * 0.5:
            move = round((rich["free_quote"] - poor["free_quote"]) * 0.4, 2)
            if move >= 15:
                ra, pa = rich["quote_asset"], poor["quote_asset"]
                act = None
                if ra != pa and {ra, pa} <= {"USDC", "USDT"}:
                    act = _stable_internal_swap_action(
                        ra, pa, move,
                        reason=f"Rebalance quote: {rich['venue_id']} rich vs {poor['venue_id']} low",
                        score=4.0,
                        top25=["skip_reason_funding", "binance_quote_cap"],
                    )
                elif rich["venue_id"] != poor["venue_id"]:
                    act = _quote_shortfall_action(
                        poor["venue_id"],
                        pa,
                        move,
                        reason=f"Top up {poor['venue_id']} {pa} from imbalance vs {rich['venue_id']}",
                        score=4.0,
                        top25=["skip_reason_funding"],
                        configured_usd=default_notion,
                    )
                if act and act["label"] not in seen_labels:
                    seen_labels.add(act["label"])
                    actions.append(act)

    actions.sort(key=_action_score, reverse=True)
    trimmed = actions[: max(1, int(limit))]
    return {
        "success": True,
        "lookback_hours": lookback,
        "funding_skip_count": len(funding_rows),
        "rotation_live_enabled": rotation_live_enabled(),
        "action_count": len(trimmed),
        "actions": trimmed,
        "suggested_at": _iso(),
    }


def execute_rotation(action: Dict[str, Any], *, dry_run: bool = True) -> Dict[str, Any]:
    """Execute one rotation action (dry-run by default)."""
    if not isinstance(action, dict) or not action.get("type"):
        return {"success": False, "error": "invalid_action"}

    atype = str(action["type"])
    if atype == "reduce_notional":
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "skipped": True,
                "reason": "advisory_only",
                "action": action,
                "hint": "Lower paper_trade_usd in connectors config or agent override.",
            }
        applied = _apply_reduce_notional(action)
        ok = bool(applied.get("success"))
        exec_res = {
            "success": ok,
            "dry_run": False,
            "mode": "config",
            "action": action,
            "already_applied": bool(applied.get("already_applied")),
            **applied,
        }
        if ok:
            exec_res["baseline_id"] = _record_rotation_baseline(action, exec_res)
        return exec_res

    if atype == "internal_stable_swap":
        wallet = str(action.get("wallet_user_id") or "exchange_sales_pool")
        sym = str(action.get("symbol") or "USDC").upper()
        side = str(action.get("side") or "buy").lower()
        quote = str(action.get("quote") or "USDT").upper()
        amt = float(action.get("amount") or action.get("amount_usd") or 0)
        if amt <= 0:
            return {"success": False, "error": "invalid_amount", "action": action}
        if dry_run:
            q = ex.quote_swap(wallet, sym, side, amt, quote)
            return {
                "success": bool(q.get("success")),
                "dry_run": True,
                "mode": "internal",
                "quote": q,
                "action": action,
            }
        qid = uuid.uuid4().hex[:16]
        q = ex.quote_swap(wallet, sym, side, amt, quote)
        if not q.get("success"):
            return {"success": False, "dry_run": False, "error": q.get("error"), "quote": q, "action": action}
        res = ex.execute_swap(wallet, qid, sym, side, amt, quote)
        exec_res = {"success": bool(res.get("success")), "dry_run": False, "mode": "internal", "result": res, "action": action}
        if exec_res.get("success"):
            exec_res["baseline_id"] = _record_rotation_baseline(action, exec_res)
        return exec_res

    if atype in ("external_market_buy", "external_market_sell"):
        venue = str(action.get("venue_id") or "")
        sym = str(action.get("symbol") or "BTC").upper()
        side = str(action.get("side") or "buy").lower()
        qty = float(action.get("quantity") or 0)
        usd = float(action.get("amount_usd") or 0)
        quote = action.get("quote")
        market = action.get("market")
        spec = vapi.market_order_for_leg(
            venue, side, sym, usd,
            quote=quote,
            quantity=qty if qty > 0 else None,
        )
        if not spec.get("ok"):
            return {
                "success": False,
                "error": spec.get("error"),
                "reason": spec.get("error"),
                "action": action,
                "venue_id": venue,
                "symbol": sym,
                "market": market,
            }
        qty = float(spec["quantity"])
        sym = str(spec["base"])
        market = str(spec.get("market") or market or "")
        quote = spec.get("quote")
        usd = float(spec.get("notional_usd") or usd)
        if side == "sell" and usd > 0:
            min_reserve = _min_sell_leg_usd()
            bals = vapi.parse_spot_balances(venue, dry_run=False)
            coin_free = float(bals.get(sym) or 0)
            px = float(spec.get("price_usd") or ex._price_usd(sym) or 0)
            if px > 0 and coin_free > 0:
                inv_usd = coin_free * px
                if inv_usd - usd < min_reserve:
                    return {
                        "success": False,
                        "skipped": True,
                        "error": "sell_would_breach_min_leg_reserve",
                        "reason": f"post-sell {sym} inventory would be ${inv_usd - usd:.2f} < ${min_reserve:.0f}",
                        "action": action,
                        "venue_id": venue,
                        "symbol": sym,
                    }
        if dry_run or not rotation_live_enabled():
            res = vapi.place_market_order(
                venue, sym, side, qty, dry_run=True, quote=quote, market=market,
            )
            return {
                "success": bool(res.get("success")),
                "dry_run": True,
                "mode": "paper",
                "rotation_live_enabled": rotation_live_enabled(),
                "order": res,
                "action": action,
                "venue_id": venue,
                "symbol": sym,
                "market": market,
                "hint": "Set rotation_live_enabled or EXCHANGE_ROTATION_LIVE=1 to execute live.",
            }
        res = vapi.place_market_order(
            venue, sym, side, qty, dry_run=False, rotation=True, quote=quote, market=market,
        )
        err = _order_error(res)
        exec_res = {
            "success": bool(res.get("success")),
            "dry_run": False,
            "mode": "live",
            "order": res,
            "action": action,
            "venue_id": venue,
            "symbol": sym,
            "market": market,
            "error": err or None,
        }
        if exec_res.get("success"):
            exec_res["baseline_id"] = _record_rotation_baseline(action, exec_res)
        return exec_res

    return {"success": False, "error": "unknown_action_type", "action": action}


def log_rotation_to_ppp(actions: List[Dict[str, Any]], *, arb_executed: int = 0) -> Optional[str]:
    """Append a PPP rotation phase row when arb had zero fills."""
    if arb_executed > 0 or not actions:
        return None
    try:
        from backend.services.exchange_profit_path_service import record_event

        top = actions[0]
        return record_event(
            phase="rotation",
            agent_id="swap_rotation",
            strategy="funding_rotation",
            decision="suggest",
            skip_reason="",
            notional_usd=float(top.get("amount_usd") or 0),
            execution={
                "action_count": len(actions),
                "top_action": top.get("label"),
                "top_type": top.get("type"),
                "rotation_live_enabled": rotation_live_enabled(),
            },
        )
    except Exception:
        return None
