"""Swap rotation — analyze funding gaps and suggest/execute capital moves for live arb.

Reuses ``can_fund_arb_leg`` / ``max_funded_notional_usd`` and internal USDC↔USDT swaps.
External venue orders require ``rotation_live_enabled`` (config or EXCHANGE_ROTATION_LIVE=1).
"""
from __future__ import annotations

import os
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_venue_api_service as vapi
from backend.services.exchange_profit_path_service import load_config, search_paths


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def rotation_live_enabled() -> bool:
    cfg = load_config()
    if cfg.get("rotation_live_enabled") is True:
        return True
    return os.environ.get("EXCHANGE_ROTATION_LIVE", "").strip().lower() in ("1", "true", "yes", "on")


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
) -> Dict[str, Any]:
    sym = str(symbol).upper()
    side_l = str(side).lower()
    label_asset = vapi.venue_quote_asset(venue_id) if side_l == "buy" else sym
    return {
        "type": "external_market_buy" if side_l == "buy" else "external_market_sell",
        "priority": priority,
        "priority_score": score,
        "label": f"{'Buy' if side_l == 'buy' else 'Sell'} {label_asset} on {venue_id} ~${amount_usd:.0f}",
        "venue_id": venue_id,
        "symbol": sym,
        "side": side_l,
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
            if short_usd < 5:
                short_usd = max(5.0, need * 0.5)
            qty = float(gaps.get("quantity") or 0)
            if side == "buy" and venue != "internal":
                act = _external_buy_action(
                    venue, sym, "buy",
                    amount_usd=short_usd,
                    qty=0,
                    reason=f"{count} recent funding skips on buy leg ({asset})",
                    score=float(count),
                    top25=["skip_reason_funding", "arb_exec_zero"],
                )
            elif side == "sell" and venue != "internal":
                act = _external_buy_action(
                    venue, sym, "sell",
                    amount_usd=short_usd,
                    qty=need - free if need > free else qty,
                    reason=f"{count} recent funding skips on sell leg ({asset})",
                    score=float(count),
                    top25=["skip_reason_funding", "nonkyc_doge_low" if asset == "DOGE" else "arb_exec_zero"],
                )
            else:
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
            if doge_usd < 25:
                act = _external_buy_action(
                    "nonkyc", "DOGE", "buy",
                    amount_usd=max(25.0 - doge_usd, 10.0),
                    qty=0,
                    reason="NonKYC DOGE inventory below $25 sell-leg minimum",
                    priority="high",
                    score=5.0,
                    top25=["nonkyc_doge_low", "skip_reason_funding"],
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
                if {ra, pa} <= {"USDC", "USDT"}:
                    act = _stable_internal_swap_action(
                        ra, pa, move,
                        reason=f"Rebalance quote: {rich['venue_id']} rich vs {poor['venue_id']} low",
                        score=4.0,
                        top25=["skip_reason_funding", "binance_quote_cap"],
                    )
                else:
                    act = _external_buy_action(
                        poor["venue_id"],
                        pa if pa not in ("USDC", "USDT") else "BTC",
                        "buy",
                        amount_usd=move,
                        qty=0,
                        reason=f"Top up {poor['venue_id']} {pa} from imbalance vs {rich['venue_id']}",
                        score=4.0,
                        top25=["skip_reason_funding"],
                    )
                if act["label"] not in seen_labels:
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
        return {
            "success": True,
            "dry_run": True,
            "skipped": True,
            "reason": "advisory_only",
            "action": action,
            "hint": "Lower paper_trade_usd in connectors config or agent override.",
        }

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
        return {"success": bool(res.get("success")), "dry_run": False, "mode": "internal", "result": res, "action": action}

    if atype in ("external_market_buy", "external_market_sell"):
        venue = str(action.get("venue_id") or "")
        sym = str(action.get("symbol") or "BTC").upper()
        side = str(action.get("side") or "buy").lower()
        qty = float(action.get("quantity") or 0)
        if qty <= 0:
            px = float(ex._price_usd(sym) or 0)
            usd = float(action.get("amount_usd") or 0)
            if side == "buy" and px > 0 and usd > 0:
                qty = round(usd / px, 8)
            elif side == "sell" and usd > 0 and px > 0:
                qty = round(usd / px, 8)
        if qty <= 0:
            return {"success": False, "error": "invalid_quantity", "action": action}
        if dry_run or not rotation_live_enabled():
            res = vapi.place_market_order(venue, sym, side, qty, dry_run=True)
            return {
                "success": bool(res.get("success")),
                "dry_run": True,
                "mode": "paper",
                "rotation_live_enabled": rotation_live_enabled(),
                "order": res,
                "action": action,
                "hint": "Set rotation_live_enabled or EXCHANGE_ROTATION_LIVE=1 to execute live.",
            }
        res = vapi.place_market_order(venue, sym, side, qty, dry_run=False)
        return {
            "success": bool(res.get("success")),
            "dry_run": False,
            "mode": "live",
            "order": res,
            "action": action,
        }

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
