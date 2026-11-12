"""Profit order book: live hitlist + ledger + leg-management techniques.

Builds a ranked book of the best calculated BN↔NK deals (top-5 by default),
keeps an append-only ledger of what the book saw, and scores **10 techniques**
for managing each leg so profit stays precalculated — no directional guessing.

Daemon leg: ``run_profit_order_book_tick`` (``PROFIT_BOOK_*`` env).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn

_BOOK_PATH = os.path.join(ex._DATA_DIR, "profit_order_book.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "profit_order_book_ledger.jsonl")
_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_order_book_state.json")
_EXTERNAL = ("binance", "nonkyc")

# Ten leg-management techniques — scored per deal, optionally applied.
LEG_TECHNIQUES: List[Dict[str, Any]] = [
    {
        "id": "prefund_buy_quote",
        "name": "Prefund buy-venue quote",
        "desc": "Sell raise inventory on the buy venue to free USDC/USDT for the cheap leg.",
    },
    {
        "id": "prefund_sell_inventory",
        "name": "Prefund sell-venue base",
        "desc": "Ensure the sell venue already holds the coin so the rich leg can fill without transfer.",
    },
    {
        "id": "size_to_funded",
        "name": "Size to funded notional",
        "desc": "Cap size to max_funded_notional so both legs clear venue mins without oversizing.",
    },
    {
        "id": "recheck_regime_deweight",
        "name": "Recheck + regime deweight",
        "desc": "Re-fetch books; shrink or skip when mid-skew eats the edge.",
    },
    {
        "id": "micro_split_fills",
        "name": "Micro-split fills",
        "desc": "Split notional into several small market clips to reduce slip and min-notional misses.",
    },
    {
        "id": "quote_bridge_rotation",
        "name": "Quote-bridge rotation",
        "desc": "Rotate USDC↔USDT / raise alts when venues use different quote assets.",
    },
    {
        "id": "stale_route_cooldown",
        "name": "Stale-route cooldown",
        "desc": "Skip routes that repeatedly fail recheck or funding for a cool-down window.",
    },
    {
        "id": "restore_post_trade",
        "name": "Restore post-trade inventory",
        "desc": "After a fill, rebalance quote/base so the next cycle stays dual-sided.",
    },
    {
        "id": "profit_floor_kill",
        "name": "Profit-floor kill switch",
        "desc": "Hard gate: never fire if compounded est_profit or net_bps falls under floor.",
    },
    {
        "id": "orphan_leg_hedge",
        "name": "Orphan-leg hedge",
        "desc": "If one venue fills and the other fails, flatten the filled leg immediately.",
    },
]


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def profit_book_enabled() -> bool:
    raw = os.environ.get("PROFIT_BOOK_ENABLED", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return bool(arb.live_enabled())


def _cfg_float(env_key: str, default: float) -> float:
    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _cfg_int(env_key: str, default: int) -> int:
    return int(_cfg_float(env_key, float(default)))


def _apply_enabled() -> bool:
    return os.environ.get("PROFIT_BOOK_APPLY", "0").strip().lower() in ("1", "true", "yes", "on")


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def read_order_book() -> Dict[str, Any]:
    data = ex._read_json(_BOOK_PATH, {})
    return data if isinstance(data, dict) else {}


def _append_ledger(row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as fh:
            import json

            fh.write(json.dumps(row, default=str) + "\n")
    except Exception:
        pass


def _tail_ledger(limit: int = 20) -> List[Dict[str, Any]]:
    import json

    if not os.path.isfile(_LEDGER_PATH):
        return []
    try:
        with open(_LEDGER_PATH, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-max(1, limit) :]
        out: List[Dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                out.append(row)
        return out
    except Exception:
        return []


def _route_key(symbol: str, buy_venue: str, sell_venue: str) -> str:
    return f"{symbol.upper()}:{buy_venue.lower()}→{sell_venue.lower()}"


def _cooldown_active(route: str, state: Dict[str, Any]) -> bool:
    cool = (state.get("cooldowns") or {}).get(route) or {}
    until = str(cool.get("until") or "")
    if not until:
        return False
    try:
        # Compare ISO strings lexicographically when both Z-suffixed.
        return until > _iso()
    except Exception:
        return False


def _set_cooldown(state: Dict[str, Any], route: str, *, seconds: float, reason: str) -> None:
    from datetime import timedelta

    until = (datetime.now(timezone.utc) + timedelta(seconds=max(5.0, seconds))).isoformat().replace("+00:00", "Z")
    cool = state.setdefault("cooldowns", {})
    cool[route] = {"until": until, "reason": reason, "set_at": _iso()}


def _scan_deals(*, notional_usd: float, scan_limit: int) -> Dict[str, Any]:
    """Reuse spread-hunter scan + compounded annotation."""
    from backend.services import exchange_spread_hunter_arm_service as hunt

    cfg = conn.load_connectors_config()
    xfer_bps = float(arb._effective_transfer_cost_bps(cfg))
    universe = hunt._build_universe(scan_limit=scan_limit)
    symbols = universe.get("symbols") or []
    annotated = hunt._batch_scan(
        symbols,
        venues=list(_EXTERNAL),
        notional_usd=notional_usd,
        batch_size=_cfg_int("PROFIT_BOOK_BATCH_SIZE", 25),
        xfer_bps=xfer_bps,
        cfg=cfg,
    )
    return {
        "symbols": symbols,
        "universe": universe,
        "deals": annotated,
        "xfer_bps": xfer_bps,
        "cfg": cfg,
    }


def _funding_snapshot(opp: Dict[str, Any], *, min_live_usd: float) -> Dict[str, Any]:
    try:
        prepared = arb.prepare_live_opportunity(
            opp,
            configured_usd=float(opp.get("notional_usd") or 15),
            buffer_pct=0.03,
            min_live_usd=min_live_usd,
        )
        return {
            "ok": bool(prepared.get("ok")),
            "reason": prepared.get("reason"),
            "max_funded_usd": prepared.get("max_funded_usd"),
            "funding": prepared.get("funding"),
            "opportunity": prepared.get("opportunity") if prepared.get("ok") else opp,
        }
    except Exception as exc:
        return {"ok": False, "reason": str(exc)[:160], "opportunity": opp}


def score_techniques_for_deal(
    opp: Dict[str, Any],
    *,
    funding: Dict[str, Any],
    state: Dict[str, Any],
    min_bps: float,
    min_profit: float,
    mid_skew_bps: float = 0.0,
) -> List[Dict[str, Any]]:
    """Rank the 10 techniques for this deal (recommend vs skip)."""
    route = _route_key(
        str(opp.get("symbol") or ""),
        str(opp.get("buy_venue") or ""),
        str(opp.get("sell_venue") or ""),
    )
    net = float(opp.get("net_bps") or 0)
    est = float(opp.get("est_profit_usd") or 0)
    funded_ok = bool(funding.get("ok"))
    max_funded = float(funding.get("max_funded_usd") or 0)
    want = float(opp.get("notional_usd") or 0)
    scored: List[Dict[str, Any]] = []

    for tech in LEG_TECHNIQUES:
        tid = tech["id"]
        recommend = False
        priority = 0
        note = ""
        if tid == "profit_floor_kill":
            recommend = net < min_bps or est < min_profit
            priority = 100 if recommend else 5
            note = "block_exec" if recommend else "floor_clear"
        elif tid == "recheck_regime_deweight":
            # Always advised before fire; lower priority so funding actions win as best_technique.
            recommend = True
            priority = 55
            note = f"mid_skew_bps={round(mid_skew_bps, 2)}"
        elif tid == "size_to_funded":
            recommend = (not funded_ok) or (0 < max_funded < want)
            priority = 88 if recommend else 20
            note = f"max_funded={max_funded}"
        elif tid == "prefund_buy_quote":
            recommend = (not funded_ok) and net >= min_bps and est >= min_profit
            priority = 92 if recommend else 10
            note = str(funding.get("reason") or "buy_quote")
        elif tid == "prefund_sell_inventory":
            recommend = (not funded_ok) and net >= min_bps
            priority = 86 if recommend else 10
            note = "sell_leg_base"
        elif tid == "quote_bridge_rotation":
            buy_v = str(opp.get("buy_venue") or "").lower()
            sell_v = str(opp.get("sell_venue") or "").lower()
            recommend = buy_v != sell_v and (buy_v in _EXTERNAL and sell_v in _EXTERNAL) and (not funded_ok)
            priority = 70 if recommend else 5
            note = "USDC↔USDT / raise rotate"
        elif tid == "micro_split_fills":
            recommend = want >= 20.0 or (funded_ok and net >= min_bps)
            priority = 50 if recommend else 15
            note = "clip=$5–10"
        elif tid == "stale_route_cooldown":
            recommend = _cooldown_active(route, state)
            priority = 97 if recommend else 8
            note = "on_cooldown" if recommend else "clear"
        elif tid == "restore_post_trade":
            recommend = funded_ok and net >= min_bps
            priority = 35 if recommend else 5
            note = "after_fill"
        elif tid == "orphan_leg_hedge":
            recommend = funded_ok and net >= min_bps
            priority = 45 if recommend else 5
            note = "arm_on_partial_fill"
        else:
            note = "unknown"
        scored.append({
            **tech,
            "recommend": recommend,
            "priority": priority,
            "note": note,
        })
    scored.sort(key=lambda r: (int(r["priority"]), 1 if r["recommend"] else 0), reverse=True)
    return scored


def _buy_sell_sides(deals: List[Dict[str, Any]], *, limit: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Best buy venues (cheapest ask) and sell venues (richest bid) across deals."""
    buys: List[Dict[str, Any]] = []
    sells: List[Dict[str, Any]] = []
    for d in deals:
        buys.append({
            "symbol": d.get("symbol"),
            "venue": d.get("buy_venue"),
            "ask": d.get("buy_ask"),
            "paired_sell_venue": d.get("sell_venue"),
            "net_bps": d.get("net_bps"),
            "est_profit_usd": d.get("est_profit_usd"),
            "action": f"BUY {d.get('symbol')} @{d.get('buy_venue')}",
        })
        sells.append({
            "symbol": d.get("symbol"),
            "venue": d.get("sell_venue"),
            "bid": d.get("sell_bid"),
            "paired_buy_venue": d.get("buy_venue"),
            "net_bps": d.get("net_bps"),
            "est_profit_usd": d.get("est_profit_usd"),
            "action": f"SELL {d.get('symbol')} @{d.get('sell_venue')}",
        })
    buys.sort(key=lambda r: float(r.get("est_profit_usd") or -999), reverse=True)
    sells.sort(key=lambda r: float(r.get("est_profit_usd") or -999), reverse=True)
    return buys[:limit], sells[:limit]


def _apply_technique(
    tech_id: str,
    opp: Dict[str, Any],
    *,
    agent_id: str,
    raise_symbols: List[str],
) -> Dict[str, Any]:
    """Execute a safe subset of techniques when PROFIT_BOOK_APPLY=1."""
    from backend.services import exchange_spread_hunter_arm_service as hunt

    if tech_id == "prefund_buy_quote":
        need = float(opp.get("notional_usd") or 15)
        return hunt._try_fund_wheel(opp, agent_id=agent_id, need_usd=need, raise_symbols=raise_symbols)
    if tech_id == "prefund_sell_inventory":
        try:
            from backend.services.venue_funding_rotation_service import fund_venue_legs_for_symbol

            return fund_venue_legs_for_symbol(
                agent_id, str(opp.get("symbol") or ""), float(opp.get("notional_usd") or 15),
                dry_run=False, max_actions=2,
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)[:200]}
    if tech_id == "restore_post_trade":
        try:
            from backend.services.venue_funding_rotation_service import restore_post_trade_inventory

            return restore_post_trade_inventory(
                symbol=str(opp.get("symbol") or ""),
                buy_venue=str(opp.get("buy_venue") or ""),
                sell_venue=str(opp.get("sell_venue") or ""),
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)[:200]}
    if tech_id == "size_to_funded":
        snap = _funding_snapshot(opp, min_live_usd=_cfg_float("PROFIT_BOOK_MIN_LIVE_USD", 10.0))
        return {"success": bool(snap.get("ok")), "funding": snap, "action": "size_to_funded"}
    # Advisory-only techniques
    return {"success": True, "skipped": True, "reason": "advisory_only", "technique": tech_id}


def build_order_book(
    *,
    top_n: Optional[int] = None,
    notional_usd: Optional[float] = None,
    scan_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Scan, rank top deals, attach techniques, persist book + ledger rows."""
    n = int(top_n or _cfg_int("PROFIT_BOOK_TOP_N", 5))
    notional = float(notional_usd or _cfg_float("PROFIT_BOOK_NOTIONAL_USD", 15.0))
    limit = int(scan_limit or _cfg_int("PROFIT_BOOK_SCAN_LIMIT", 80))
    min_bps = _cfg_float("PROFIT_BOOK_MIN_BPS", 12.0)
    min_profit = _cfg_float("PROFIT_BOOK_MIN_PROFIT_USD", 0.02)
    min_live = _cfg_float("PROFIT_BOOK_MIN_LIVE_USD", 10.0)
    agent_id = (os.environ.get("PROFIT_BOOK_AGENT_ID") or "arb_live_dual_farm").strip()
    state = _load_state()

    scanned = _scan_deals(notional_usd=notional, scan_limit=limit)
    deals = list(scanned.get("deals") or [])
    deals.sort(
        key=lambda d: (float(d.get("est_profit_usd") or 0), float(d.get("net_bps") or 0)),
        reverse=True,
    )

    hitlist: List[Dict[str, Any]] = []
    for rank, opp in enumerate(deals[: max(n * 3, n)], start=1):
        route = _route_key(
            str(opp.get("symbol") or ""),
            str(opp.get("buy_venue") or ""),
            str(opp.get("sell_venue") or ""),
        )
        funding = _funding_snapshot(opp, min_live_usd=min_live)
        # Light mid-skew from stored ask/bid if present
        skew = 0.0
        try:
            from backend.services.exchange_spread_hunter_arm_service import mid_skew_bps

            skew = mid_skew_bps(
                float(opp.get("buy_ask") or 0),
                float(opp.get("buy_bid") or opp.get("buy_ask") or 0),
                float(opp.get("sell_ask") or opp.get("sell_bid") or 0),
                float(opp.get("sell_bid") or 0),
            )
        except Exception:
            skew = 0.0
        techniques = score_techniques_for_deal(
            opp, funding=funding, state=state, min_bps=min_bps, min_profit=min_profit, mid_skew_bps=skew,
        )
        best_tech = next((t for t in techniques if t.get("recommend")), techniques[0] if techniques else None)
        qualifies = (
            float(opp.get("net_bps") or 0) >= min_bps
            and float(opp.get("est_profit_usd") or 0) >= min_profit
            and bool(opp.get("profitable"))
            and not _cooldown_active(route, state)
        )
        row = {
            "rank": rank,
            "route": route,
            "symbol": opp.get("symbol"),
            "buy_venue": opp.get("buy_venue"),
            "sell_venue": opp.get("sell_venue"),
            "buy_ask": opp.get("buy_ask"),
            "sell_bid": opp.get("sell_bid"),
            "gross_bps": opp.get("gross_bps"),
            "fee_bps": opp.get("fee_bps"),
            "net_bps": opp.get("net_bps"),
            "est_profit_usd": opp.get("est_profit_usd"),
            "notional_usd": opp.get("notional_usd"),
            "qualifies": qualifies,
            "funded": bool(funding.get("ok")),
            "max_funded_usd": funding.get("max_funded_usd"),
            "mid_skew_bps": round(skew, 2),
            "action": (
                f"BUY {opp.get('symbol')} @{opp.get('buy_venue')} / "
                f"SELL @{opp.get('sell_venue')}"
            ),
            "best_technique": (best_tech or {}).get("id"),
            "techniques": techniques[:5],
            "all_technique_ids": [t["id"] for t in techniques if t.get("recommend")],
        }
        hitlist.append(row)

    top5 = [r for r in hitlist if r.get("qualifies")][:n]
    if len(top5) < n:
        # Fill remaining slots with best non-qualifying for visibility.
        for r in hitlist:
            if r in top5:
                continue
            top5.append({**r, "below_threshold": not r.get("qualifies")})
            if len(top5) >= n:
                break

    buy_side, sell_side = _buy_sell_sides(deals, limit=n)

    book = {
        "updated_at": _iso(),
        "arm": "profit_order_book",
        "top_n": n,
        "min_bps": min_bps,
        "min_profit_usd": min_profit,
        "notional_usd": notional,
        "universe_size": len(scanned.get("symbols") or []),
        "deal_count": len(deals),
        "qualifying_count": sum(1 for r in hitlist if r.get("qualifies")),
        "top5": top5,
        "hitlist": hitlist[: max(n * 2, 10)],
        "buy_side": buy_side,
        "sell_side": sell_side,
        "techniques_catalog": LEG_TECHNIQUES,
        "apply_enabled": _apply_enabled(),
    }
    ex._write_json(_BOOK_PATH, book)

    # Ledger: one summary + each top row
    _append_ledger({
        "ts": book["updated_at"],
        "kind": "book_snapshot",
        "deal_count": book["deal_count"],
        "qualifying_count": book["qualifying_count"],
        "top_symbols": [r.get("symbol") for r in top5],
        "top_net_bps": [r.get("net_bps") for r in top5],
    })
    for r in top5:
        _append_ledger({
            "ts": book["updated_at"],
            "kind": "hit",
            "rank": r.get("rank"),
            "route": r.get("route"),
            "symbol": r.get("symbol"),
            "net_bps": r.get("net_bps"),
            "est_profit_usd": r.get("est_profit_usd"),
            "qualifies": r.get("qualifies"),
            "funded": r.get("funded"),
            "best_technique": r.get("best_technique"),
            "action": r.get("action"),
        })

    state["updated_at"] = book["updated_at"]
    state["last_top"] = top5
    state["agent_id"] = agent_id
    _save_state(state)
    book["ledger_tail"] = _tail_ledger(15)
    return book


def run_profit_order_book_tick(*, force: bool = False, apply: Optional[bool] = None) -> Dict[str, Any]:
    """Daemon tick: refresh book, optionally apply top technique on #1 deal."""
    if not profit_book_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled"}

    book = build_order_book()
    out: Dict[str, Any] = {
        "success": True,
        "arm": "profit_order_book",
        "scanned_at": book.get("updated_at"),
        "deal_count": book.get("deal_count"),
        "qualifying_count": book.get("qualifying_count"),
        "top5": book.get("top5"),
        "buy_side": book.get("buy_side"),
        "sell_side": book.get("sell_side"),
        "applied": None,
        "skip_reason": None,
    }
    if not book.get("deal_count"):
        out["skip_reason"] = "empty_book"
        return out

    do_apply = _apply_enabled() if apply is None else bool(apply)
    top = (book.get("top5") or [None])[0]
    if not top:
        out["skip_reason"] = "no_top_deal"
        return out

    out["best"] = {
        "symbol": top.get("symbol"),
        "route": top.get("route"),
        "net_bps": top.get("net_bps"),
        "est_profit_usd": top.get("est_profit_usd"),
        "action": top.get("action"),
        "best_technique": top.get("best_technique"),
        "qualifies": top.get("qualifies"),
        "funded": top.get("funded"),
    }

    # Always enforce profit-floor / cooldown bookkeeping even when apply is off.
    state = _load_state()
    route = str(top.get("route") or "")
    if top.get("best_technique") == "stale_route_cooldown" and top.get("qualifies") is False:
        out["skip_reason"] = "cooldown"
    if not top.get("qualifies"):
        out["skip_reason"] = out.get("skip_reason") or "top_below_threshold"

    if do_apply and top.get("qualifies") and not top.get("funded"):
        tech_id = str(top.get("best_technique") or "prefund_buy_quote")
        if tech_id in ("profit_floor_kill", "stale_route_cooldown"):
            out["skip_reason"] = tech_id
            return out
        agent_id = (os.environ.get("PROFIT_BOOK_AGENT_ID") or "arb_live_dual_farm").strip()
        symbols = [str(r.get("symbol") or "") for r in (book.get("hitlist") or []) if r.get("symbol")]
        applied = _apply_technique(
            tech_id,
            {
                "symbol": top.get("symbol"),
                "buy_venue": top.get("buy_venue"),
                "sell_venue": top.get("sell_venue"),
                "buy_ask": top.get("buy_ask"),
                "sell_bid": top.get("sell_bid"),
                "notional_usd": top.get("notional_usd"),
                "net_bps": top.get("net_bps"),
                "est_profit_usd": top.get("est_profit_usd"),
            },
            agent_id=agent_id,
            raise_symbols=symbols,
        )
        out["applied"] = {"technique": tech_id, **(applied if isinstance(applied, dict) else {"result": applied})}
        if not applied.get("success"):
            _set_cooldown(state, route, seconds=_cfg_float("PROFIT_BOOK_COOLDOWN_SEC", 120), reason=tech_id)
            _save_state(state)
            out["skip_reason"] = "apply_failed"
        else:
            _append_ledger({
                "ts": _iso(),
                "kind": "technique_apply",
                "route": route,
                "technique": tech_id,
                "success": True,
            })
    elif do_apply and top.get("qualifies") and top.get("funded"):
        # Funded + qualifies → hand off to hunter/dual-farm execution path by recording ready flag.
        out["ready_to_exec"] = True
        out["skip_reason"] = None
        _append_ledger({
            "ts": _iso(),
            "kind": "ready_to_exec",
            "route": route,
            "net_bps": top.get("net_bps"),
            "est_profit_usd": top.get("est_profit_usd"),
        })
    return out


def profit_order_book_status() -> Dict[str, Any]:
    return {
        "success": True,
        "enabled": profit_book_enabled(),
        "apply_enabled": _apply_enabled(),
        "top_n": _cfg_int("PROFIT_BOOK_TOP_N", 5),
        "min_bps": _cfg_float("PROFIT_BOOK_MIN_BPS", 12.0),
        "book": read_order_book(),
        "state": _load_state(),
        "ledger_tail": _tail_ledger(20),
        "techniques": LEG_TECHNIQUES,
    }
