"""Spread-hunter arm: multi-assignment BN↔NK hunter (hunt + backfill).

No directional guessing on the hunt path. Every candidate is priced from live bid/ask,
fee-compounded, rechecked immediately before fill, and sized only to fundable balances.

Assignments per tick (hunter does more than one job):
* ``backfill`` — when quote is thin / head posts a prefund hint / last skip was funding:
  sell raise inventory (and optional rotation) to rebuild free USDC/USDT toward a floor.
* ``hunt`` — wide catalog scan → regime recheck → opportunistic prefund wheel → execute.

Flow per tick:
1. Decide assignments (backfill and/or hunt).
2. Run backfill first when needed (head prefund_hint is the priority brief).
3. Build a large BN↔NK universe (catalog ∩ hot list, up to ``SPREAD_HUNTER_SCAN_LIMIT``).
4. Batch-scan spreads; recompute compounded ``est_profit_usd`` / ``net_bps``.
5. Regime deweight: skip routes whose mid-skew collapses the edge or flipped on recheck.
6. Prefund / rotate quote inventory when edge is real but a leg is short.
7. Execute spatial arb (buy cheap venue + sell rich venue) only when prepare+recheck pass.

Enable with ``SPREAD_HUNTER_ENABLED=1`` (default on when live arb is on).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn

_STATE_PATH = os.path.join(ex._DATA_DIR, "spread_hunter_arm_state.json")
_BOARD_PATH = os.path.join(ex._DATA_DIR, "spread_hunter_board.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "spread_hunter_ledger.jsonl")
_EXTERNAL = ("binance", "nonkyc")
_SEED_SYMBOLS = [
    "ADA", "LINK", "BNB", "XRP", "SOL", "AVAX", "DOT", "ATOM", "NEAR", "TRX", "UNI", "LTC",
    "BTC", "ETH", "DOGE", "SHIB", "MATIC", "POL", "APT", "SUI", "ARB", "OP", "FIL", "AAVE",
    "MKR", "CRV", "PEPE", "WIF", "TON", "INJ", "RENDER", "FET", "TIA", "SEI", "HBAR", "ALGO",
]
_HUNTER_AGENT_ID = "arb_spread_hunter"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def spread_hunter_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("hunter"):
            return False
    except Exception:
        pass
    raw = os.environ.get("SPREAD_HUNTER_ENABLED", "").strip().lower()
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


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _venue_fee_bps(venue_id: str, cfg: Optional[Dict[str, Any]] = None) -> float:
    cfg = cfg or conn.load_connectors_config()
    for row in cfg.get("venues") or []:
        if str(row.get("id") or "").lower() == str(venue_id or "").lower():
            try:
                return float(row.get("fee_taker_bps") or 10)
            except (TypeError, ValueError):
                return 10.0
    return 10.0


def estimate_compounded_leg(
    *,
    buy_ask: float,
    sell_bid: float,
    notional_usd: float,
    fee_buy_bps: float,
    fee_sell_bps: float,
    xfer_bps: float = 0.0,
) -> Dict[str, Any]:
    """Fee-compounded spatial PnL — buy then sell same qty (prefunded inventory model)."""
    ask = float(buy_ask or 0)
    bid = float(sell_bid or 0)
    notional = max(0.0, float(notional_usd or 0))
    if ask <= 0 or bid <= 0 or notional <= 0:
        return {
            "gross_bps": 0.0,
            "fee_bps": 0.0,
            "net_bps": 0.0,
            "est_profit_usd": 0.0,
            "profitable": False,
        }
    gross_bps = (bid - ask) / ask * 10000.0
    fee_bps = float(fee_buy_bps) + float(fee_sell_bps) + float(xfer_bps)
    net_bps = gross_bps - fee_bps
    qty = notional / ask
    buy_cost = notional * (1.0 + float(fee_buy_bps) / 10000.0)
    sell_proceeds = qty * bid * (1.0 - float(fee_sell_bps) / 10000.0) * (1.0 - float(xfer_bps) / 10000.0)
    est = sell_proceeds - buy_cost
    return {
        "gross_bps": round(gross_bps, 2),
        "fee_bps": round(fee_bps, 2),
        "net_bps": round(net_bps, 2),
        "est_profit_usd": round(est, 6),
        "profitable": net_bps > 0 and est > 0,
        "buy_cost_usd": round(buy_cost, 6),
        "sell_proceeds_usd": round(sell_proceeds, 6),
        "quantity": round(qty, 8),
    }


def mid_skew_bps(buy_ask: float, buy_bid: float, sell_ask: float, sell_bid: float) -> float:
    """Absolute mid-price skew between venues in bps of the cheaper mid."""
    buy_mid = (float(buy_ask or 0) + float(buy_bid or 0)) / 2.0
    sell_mid = (float(sell_ask or 0) + float(sell_bid or 0)) / 2.0
    if buy_mid <= 0 or sell_mid <= 0:
        return 0.0
    base = min(buy_mid, sell_mid)
    return abs(sell_mid - buy_mid) / base * 10000.0


def regime_deweight_factor(
    *,
    net_bps: float,
    mid_skew: float,
    max_skew_bps: float,
    collapse_bps: float,
) -> Tuple[float, Optional[str]]:
    """Return (size_factor 0..1, skip_reason). Deweight noisy mid skew; skip collapsed edges."""
    nb = float(net_bps or 0)
    skew = float(mid_skew or 0)
    max_skew = max(1.0, float(max_skew_bps or 1))
    collapse = max(0.0, float(collapse_bps or 0))
    if nb < collapse:
        return 0.0, "regime_edge_collapsed"
    # When mid skew >> remaining edge, books are noisy — shrink size.
    if skew > max_skew:
        # Linear deweight from 1.0 at max_skew down to 0 at 2× max_skew.
        excess = min(1.0, (skew - max_skew) / max_skew)
        factor = max(0.0, 1.0 - excess)
        if factor <= 0.05:
            return 0.0, "regime_skew_too_wide"
        return round(factor, 4), "regime_deweight"
    # Soft deweight when skew eats most of the edge.
    if skew > 0 and nb > 0 and skew / max(nb, 1e-9) > 1.5:
        return 0.55, "regime_deweight"
    return 1.0, None


def _is_external_opp(opp: Dict[str, Any]) -> bool:
    buy = str(opp.get("buy_venue") or "").lower()
    sell = str(opp.get("sell_venue") or "").lower()
    return buy in _EXTERNAL and sell in _EXTERNAL and buy != sell


def _build_universe(*, scan_limit: int) -> Dict[str, Any]:
    """Wide catalog hunt pool — prefer catalog ∩ hot, fall back to seeds."""
    limit = max(8, int(scan_limit))
    catalog: List[str] = []
    hot: List[str] = []
    try:
        from backend.services.exchange_profit_pair_search_service import (
            catalog_intersection,
            enabled as pair_search_enabled,
            get_hot_symbols,
            run_profit_pair_search,
        )

        catalog = [str(s).upper() for s in catalog_intersection(list(_EXTERNAL)) if s]
        if pair_search_enabled():
            try:
                # Refresh index so hunter sees newest gaps (bounded inside search).
                search = run_profit_pair_search(venues=list(_EXTERNAL), top_n=min(24, limit))
                hot = [str(s).upper() for s in (search.get("hot_symbols") or []) if s]
            except Exception:
                hot = [str(s).upper() for s in get_hot_symbols(limit=min(24, limit)) if s]
        else:
            hot = [str(s).upper() for s in get_hot_symbols(limit=min(24, limit)) if s]
    except Exception:
        catalog = []
        hot = []

    env_syms = [
        s.strip().upper()
        for s in (os.environ.get("SPREAD_HUNTER_SYMBOLS") or "").split(",")
        if s.strip()
    ]
    ordered: List[str] = []
    for sym in env_syms + hot + _SEED_SYMBOLS + catalog:
        if sym and sym not in ordered:
            ordered.append(sym)
        if len(ordered) >= limit:
            break
    return {
        "symbols": ordered,
        "catalog_count": len(catalog),
        "hot_count": len(hot),
        "scan_limit": limit,
    }


def _annotate_opportunity(
    opp: Dict[str, Any],
    *,
    notional_usd: float,
    cfg: Dict[str, Any],
    xfer_bps: float,
) -> Dict[str, Any]:
    buy_v = str(opp.get("buy_venue") or "")
    sell_v = str(opp.get("sell_venue") or "")
    fee_buy = _venue_fee_bps(buy_v, cfg)
    fee_sell = _venue_fee_bps(sell_v, cfg)
    math = estimate_compounded_leg(
        buy_ask=float(opp.get("buy_ask") or 0),
        sell_bid=float(opp.get("sell_bid") or 0),
        notional_usd=notional_usd,
        fee_buy_bps=fee_buy,
        fee_sell_bps=fee_sell,
        xfer_bps=xfer_bps,
    )
    out = dict(opp)
    out.update({
        "fee_buy_bps": fee_buy,
        "fee_sell_bps": fee_sell,
        "xfer_bps": float(xfer_bps),
        "gross_bps": math["gross_bps"],
        "fee_bps": math["fee_bps"],
        "net_bps": math["net_bps"],
        "est_profit_usd": math["est_profit_usd"],
        "notional_usd": round(float(notional_usd), 2),
        "compounded": True,
        "profitable": math["profitable"],
    })
    return out


def _batch_scan(
    symbols: Sequence[str],
    *,
    venues: List[str],
    notional_usd: float,
    batch_size: int,
    xfer_bps: float,
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Scan up to ~100 symbols in batches; return annotated external opps."""
    from backend.services import exchange_venue_api_service as vapi

    vapi.refresh_venue_balances(venues, force=True)
    size = max(5, int(batch_size))
    annotated: List[Dict[str, Any]] = []
    for i in range(0, len(symbols), size):
        chunk = list(symbols[i : i + size])
        scan = arb.scan_opportunities(symbols=chunk, venues=venues, notional_usd=notional_usd)
        for opp in scan.get("opportunities") or []:
            if not _is_external_opp(opp):
                continue
            ask = float(opp.get("buy_ask") or 0)
            bid = float(opp.get("sell_bid") or 0)
            # Reject dust/broken books that invent phantom million-bps edges.
            if ask <= 0 or bid <= 0 or ask < 1e-6 or (bid / ask) > 1.25:
                continue
            annotated.append(
                _annotate_opportunity(opp, notional_usd=notional_usd, cfg=cfg, xfer_bps=xfer_bps)
            )
    annotated.sort(
        key=lambda o: (float(o.get("est_profit_usd") or 0), float(o.get("net_bps") or 0)),
        reverse=True,
    )
    return annotated


def _recheck_live(
    opp: Dict[str, Any],
    *,
    notional_usd: float,
    cfg: Dict[str, Any],
    xfer_bps: float,
    max_skew_bps: float,
    collapse_bps: float,
) -> Dict[str, Any]:
    """Re-fetch both venue books and recompute PnL + regime factor."""
    symbol = str(opp.get("symbol") or "").upper()
    buy_v = str(opp.get("buy_venue") or "")
    sell_v = str(opp.get("sell_venue") or "")
    buy_tick = conn.fetch_ticker(buy_v, symbol) or {}
    sell_tick = conn.fetch_ticker(sell_v, symbol) or {}
    buy_ask = float(buy_tick.get("ask") or 0)
    buy_bid = float(buy_tick.get("bid") or 0)
    sell_ask = float(sell_tick.get("ask") or 0)
    sell_bid = float(sell_tick.get("bid") or 0)
    if buy_ask <= 0 or sell_bid <= 0:
        return {"ok": False, "reason": "stale_or_missing_book"}

    refreshed = {
        **opp,
        "buy_ask": buy_ask,
        "sell_bid": sell_bid,
        "buy_bid": buy_bid,
        "sell_ask": sell_ask,
    }
    refreshed = _annotate_opportunity(
        refreshed, notional_usd=notional_usd, cfg=cfg, xfer_bps=xfer_bps,
    )
    skew = mid_skew_bps(buy_ask, buy_bid, sell_ask, sell_bid)
    factor, regime_reason = regime_deweight_factor(
        net_bps=float(refreshed.get("net_bps") or 0),
        mid_skew=skew,
        max_skew_bps=max_skew_bps,
        collapse_bps=collapse_bps,
    )
    refreshed["mid_skew_bps"] = round(skew, 2)
    refreshed["regime_factor"] = factor
    refreshed["regime_reason"] = regime_reason
    if factor <= 0:
        return {"ok": False, "reason": regime_reason or "regime_skip", "opportunity": refreshed}
    if not refreshed.get("profitable"):
        return {"ok": False, "reason": "recheck_unprofitable", "opportunity": refreshed}
    sized = float(notional_usd) * float(factor)
    refreshed = _annotate_opportunity(
        refreshed, notional_usd=sized, cfg=cfg, xfer_bps=xfer_bps,
    )
    refreshed["mid_skew_bps"] = round(skew, 2)
    refreshed["regime_factor"] = factor
    refreshed["regime_reason"] = regime_reason
    return {"ok": True, "opportunity": refreshed}


def _prefund_enabled() -> bool:
    return os.environ.get("SPREAD_HUNTER_PREFUND", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def _backfill_enabled() -> bool:
    return os.environ.get("SPREAD_HUNTER_BACKFILL", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def _backfill_floor_usd() -> float:
    # Above head thin gate (~$12) and default min live notional (~$10).
    return _cfg_float("SPREAD_HUNTER_BACKFILL_FLOOR_USD", 18.0)


def _backfill_cooldown_sec() -> float:
    return _cfg_float("SPREAD_HUNTER_BACKFILL_COOLDOWN_SEC", 90.0)


def _append_hunter_event(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "hunter"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _learn_hunter(note: str, *, profit_usd: float = 0.0) -> Dict[str, Any]:
    try:
        from backend.services.exchange_agent_learning_service import learn_from_profit

        agent_id = (os.environ.get("SPREAD_HUNTER_AGENT_ID") or _HUNTER_AGENT_ID).strip()
        acct = arb.read_account(agent_id)
        if not acct.get("skills"):
            acct["skills"] = [
                "spread_hunt", "backfill", "prefund", "regime_filter", "kill_shot",
            ]
            acct.setdefault("skill_proficiency", {})
        out = learn_from_profit(acct, max(0.0, float(profit_usd or 0)))
        acct["ticks"] = int(acct.get("ticks") or 0) + 1
        acct["last_action"] = {"note": note, "ts": _iso(), "profit_usd": profit_usd}
        arb.write_account(acct)
        return {"ok": True, **out}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}


def _venue_free_quote(venue: str) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi

    quote = str(vapi.venue_quote_asset(venue) or "").upper()
    bals = vapi.parse_spot_balances(venue, dry_run=False, force_refresh=True) or {}
    free = float(bals.get(quote) or 0) if quote else 0.0
    return {"venue": venue, "quote": quote, "free": round(free, 4), "balances": bals}


_FIAT_SKIP = frozenset({
    "USDT", "USDC", "USD", "BUSD", "FDUSD", "DAI", "TUSD", "USDD",
    "EUR", "DKK", "GBP", "JPY", "AUD", "CAD", "CHF", "SEK", "NOK",
})


def _raise_inventory_candidates(
    bals: Dict[str, Any],
    *,
    quote: str,
    preferred: Optional[Sequence[str]] = None,
) -> List[str]:
    """Preferred symbols first, then spot inventory (skip LD* earn wrappers / fiat)."""
    quote_u = str(quote or "").upper()
    skip = set(_FIAT_SKIP)
    skip.add(quote_u)
    ordered: List[str] = []
    seen = set()
    for sym in list(preferred or []) + list(_SEED_SYMBOLS):
        s = str(sym or "").upper()
        if not s or s in skip or s in seen or s.startswith("LD"):
            continue
        if float(bals.get(s) or 0) > 0:
            ordered.append(s)
            seen.add(s)
    extras: List[Tuple[str, float]] = []
    for k, val in (bals or {}).items():
        s = str(k or "").upper()
        if not s or s in skip or s in seen or s.startswith("LD"):
            continue
        try:
            qty = float(val or 0)
        except (TypeError, ValueError):
            continue
        if qty > 0:
            extras.append((s, qty))
    extras.sort(key=lambda row: -row[1])
    ordered.extend(sym for sym, _ in extras)
    return ordered


def _raise_quote_on_buy_venue(
    buy_venue: str,
    *,
    need_usd: float,
    raise_symbols: Optional[List[str]] = None,
    min_sell_usd: float = 5.0,
    max_fraction: float = 0.45,
    scan_all_balances: bool = False,
) -> Dict[str, Any]:
    """Sell raise inventory on buy venue to free quote for the arb buy leg / backfill."""
    from backend.services import exchange_venue_api_service as vapi

    quote = vapi.venue_quote_asset(buy_venue)
    bals = vapi.parse_spot_balances(buy_venue, dry_run=False, force_refresh=True) or {}
    free_q = float(bals.get(quote) or 0)
    if free_q >= need_usd:
        return {"success": True, "skipped": True, "reason": "already_funded", "free_quote": free_q}

    gap = max(0.0, need_usd - free_q)
    max_raise = _cfg_float("SPREAD_HUNTER_PREFUND_MAX_USD", 40.0)
    target = min(gap * 1.05, max_raise)
    if target < float(min_sell_usd):
        return {
            "success": False,
            "reason": "gap_too_small",
            "gap_usd": round(gap, 2),
            "free_quote": round(free_q, 4),
            "need_usd": round(need_usd, 2),
        }

    earn_unlock = None
    if str(buy_venue).lower() == "binance":
        try:
            from backend.services.exchange_binance_earn_service import list_ld_balances, unlock_earn_to_spot

            if list_ld_balances(bals):
                earn_unlock = unlock_earn_to_spot(target_usd=max(target, float(min_sell_usd)))
                if earn_unlock.get("success"):
                    time.sleep(1.0)
                    vapi.invalidate_venue_balance_cache(buy_venue)
                    bals = vapi.parse_spot_balances(buy_venue, dry_run=False, force_refresh=True) or {}
                    free_q = float(bals.get(quote) or 0)
                    if free_q >= need_usd:
                        return {
                            "success": True,
                            "skipped": True,
                            "reason": "funded_after_earn_unlock",
                            "free_quote": free_q,
                            "earn_unlock": earn_unlock,
                        }
        except Exception as exc:
            earn_unlock = {"success": False, "error": str(exc)[:160]}

    if scan_all_balances:
        candidates = _raise_inventory_candidates(bals, quote=str(quote or ""), preferred=raise_symbols)
    else:
        candidates = [
            s for s in (raise_symbols or list(_SEED_SYMBOLS))
            if not str(s).upper().startswith("LD")
        ]

    attempts: List[Dict[str, Any]] = []
    for sym in candidates:
        qty_coin = float(bals.get(sym) or 0)
        if qty_coin <= 0:
            continue
        tick = conn.fetch_ticker(buy_venue, sym) or {}
        bid = float(tick.get("bid") or 0)
        if bid <= 0:
            attempts.append({"symbol": sym, "skipped": True, "reason": "no_bid"})
            continue
        inv_usd = qty_coin * bid
        sell_usd = min(target, inv_usd * float(max_fraction))
        if sell_usd < float(min_sell_usd):
            attempts.append({"symbol": sym, "skipped": True, "reason": "below_min_sell", "usd": round(inv_usd, 2)})
            continue
        sell_qty = round((sell_usd / bid) * 0.995, 6)
        if sell_qty <= 0:
            continue
        order = vapi.place_market_order(
            buy_venue, sym, "sell", sell_qty, dry_run=False, quote=quote,
        )
        ok = bool(order.get("success"))
        vapi.invalidate_venue_balance_cache(buy_venue)
        attempts.append({
            "symbol": sym,
            "success": ok,
            "sell_usd": round(sell_usd, 2),
            "error": order.get("error") if not ok else None,
        })
        if ok:
            return {
                "success": True,
                "action": "prefund_sell",
                "venue": buy_venue,
                "symbol": sym,
                "sell_qty": sell_qty,
                "sell_usd": round(sell_usd, 2),
                "order_success": True,
                "free_quote_before": round(free_q, 4),
                "earn_unlock": earn_unlock,
                "attempts": attempts[-5:],
            }
    return {
        "success": False,
        "reason": "no_raise_inventory",
        "need_usd": round(need_usd, 2),
        "free_quote": round(free_q, 4),
        "candidates": len(candidates),
        "earn_unlock": earn_unlock,
        "attempts": attempts[-8:],
    }


def _try_fund_wheel(
    opp: Dict[str, Any],
    *,
    agent_id: str,
    need_usd: float,
    raise_symbols: List[str],
) -> Dict[str, Any]:
    """Move capital toward the short leg: local prefund sell, then optional rotation fund."""
    buy_v = str(opp.get("buy_venue") or "")
    steps: List[Dict[str, Any]] = []
    pref = _raise_quote_on_buy_venue(buy_v, need_usd=need_usd, raise_symbols=raise_symbols)
    steps.append({"step": "raise_quote", **pref})

    # Optional: venue_funding_rotation when live rotation is on.
    try:
        from backend.services.venue_funding_rotation_service import fund_venue_legs_for_symbol

        fund = fund_venue_legs_for_symbol(
            agent_id,
            str(opp.get("symbol") or ""),
            float(opp.get("notional_usd") or need_usd),
            dry_run=False,
            max_actions=2,
        )
        steps.append({"step": "fund_legs", **fund})
    except Exception as exc:
        steps.append({"step": "fund_legs", "success": False, "error": str(exc)[:200]})

    ok = any(bool(s.get("success")) and not s.get("skipped") for s in steps) or any(
        bool(s.get("skipped")) for s in steps
    )
    return {"success": ok, "steps": steps}


def _backfill_needed(
    *,
    floor_usd: float,
    hint: Optional[Dict[str, Any]],
    last_skip: Optional[str],
    snaps: Optional[Sequence[Dict[str, Any]]] = None,
) -> Tuple[bool, str]:
    if hint:
        return True, "head_prefund_hint"
    if str(last_skip or "") in ("insufficient_venue_balance", "gap_too_small"):
        return True, "last_skip_funding"
    rows = list(snaps) if snaps is not None else [_venue_free_quote(v) for v in _EXTERNAL]
    total = sum(float(s.get("free") or 0) for s in rows)
    thin_total = total < max(12.0, floor_usd * 0.7)
    thin_venue = any(float(s.get("free") or 0) < floor_usd for s in rows)
    if thin_total:
        return True, "thin_total_quote"
    if thin_venue:
        return True, "venue_below_floor"
    return False, "funded"


def run_hunter_backfill_assignment(
    *,
    hint: Optional[Dict[str, Any]] = None,
    raise_symbols: Optional[List[str]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Hunter assignment: rebuild free quote on thin venues (head prefund_hint first)."""
    floor = _backfill_floor_usd()
    agent_id = (os.environ.get("SPREAD_HUNTER_AGENT_ID") or "arb_live_dual_farm").strip()
    preferred = list(raise_symbols or [])
    if hint and hint.get("symbol"):
        preferred = [str(hint["symbol"]).upper()] + [s for s in preferred if s != str(hint["symbol"]).upper()]

    snaps = [_venue_free_quote(v) for v in _EXTERNAL]
    # Thin venues first; keep order stable otherwise.
    venues = sorted(snaps, key=lambda s: float(s.get("free") or 0))
    actions: List[Dict[str, Any]] = []
    raised_usd = 0.0

    for snap in venues:
        venue = str(snap.get("venue") or "")
        free = float(snap.get("free") or 0)
        if free >= floor and not force:
            actions.append({
                "venue": venue,
                "skipped": True,
                "reason": "above_floor",
                "free_quote": free,
                "floor_usd": floor,
            })
            continue
        need = floor if free < floor else max(floor, free + 5.0)
        pref = _raise_quote_on_buy_venue(
            venue,
            need_usd=need,
            raise_symbols=preferred or None,
            min_sell_usd=_cfg_float("SPREAD_HUNTER_BACKFILL_MIN_SELL_USD", 3.0),
            max_fraction=_cfg_float("SPREAD_HUNTER_BACKFILL_MAX_FRACTION", 0.55),
            scan_all_balances=True,
        )
        actions.append({"venue": venue, **pref})
        if pref.get("success") and not pref.get("skipped"):
            raised_usd += float(pref.get("sell_usd") or 0)

    # Optional rotation toward the hinted symbol when local raise missed.
    if hint and hint.get("symbol") and raised_usd <= 0:
        try:
            from backend.services.venue_funding_rotation_service import fund_venue_legs_for_symbol

            fund = fund_venue_legs_for_symbol(
                agent_id,
                str(hint.get("symbol") or ""),
                float(floor),
                dry_run=False,
                max_actions=2,
            )
            actions.append({"step": "fund_legs", "symbol": hint.get("symbol"), **fund})
            if fund.get("success"):
                raised_usd += float(fund.get("funded_usd") or fund.get("amount_usd") or 0)
        except Exception as exc:
            actions.append({"step": "fund_legs", "success": False, "error": str(exc)[:200]})

    after = [_venue_free_quote(v) for v in _EXTERNAL]
    total_after = sum(float(s.get("free") or 0) for s in after)
    sold = any(bool(a.get("success")) and not a.get("skipped") and a.get("action") == "prefund_sell" for a in actions)
    ok = sold or total_after >= floor or any(bool(a.get("success")) and a.get("step") == "fund_legs" for a in actions)

    out = {
        "success": bool(ok),
        "assignment": "backfill",
        "floor_usd": floor,
        "hint": hint,
        "raised_usd": round(raised_usd, 2),
        "before": [{"venue": s["venue"], "free": s["free"], "quote": s.get("quote")} for s in snaps],
        "after": [{"venue": s["venue"], "free": s["free"], "quote": s.get("quote")} for s in after],
        "total_free_usd": round(total_after, 4),
        "actions": actions,
        "reason": "raised" if sold else ("funded" if total_after >= floor else "no_raise"),
    }
    _append_hunter_event("backfill", **{k: v for k, v in out.items() if k != "hint"}, hint_symbol=(hint or {}).get("symbol"))
    _learn_hunter(
        f"backfill:{out.get('reason')}:raised={out.get('raised_usd')}",
        profit_usd=0.01 if sold else 0.0,
    )
    if sold or (hint and ok):
        try:
            from backend.services.exchange_profit_head_service import clear_prefund_hint

            clear_prefund_hint()
        except Exception:
            pass
    return out


def decide_hunter_assignments(
    *,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pick hunter jobs for this tick. Backfill is first class, not only opportunistic."""
    state = state if isinstance(state, dict) else _load_state()
    hint = None
    try:
        from backend.services.exchange_profit_head_service import get_prefund_hint

        hint = get_prefund_hint()
    except Exception:
        hint = None

    last_skip = None
    last_tick = state.get("last_tick") if isinstance(state.get("last_tick"), dict) else {}
    if isinstance(last_tick, dict):
        last_skip = last_tick.get("skip_reason")

    floor = _backfill_floor_usd()
    need, why = (False, "backfill_disabled")
    if _backfill_enabled():
        need, why = _backfill_needed(floor_usd=floor, hint=hint, last_skip=str(last_skip) if last_skip else None)

    cooldown = _backfill_cooldown_sec()
    last_bf = state.get("last_backfill_at")
    cooled = True
    if last_bf and cooldown > 0 and need:
        try:
            prev = datetime.fromisoformat(str(last_bf).replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - prev).total_seconds()
            cooled = age >= cooldown
            if not cooled:
                why = "backfill_cooldown"
        except Exception:
            cooled = True

    assignments: List[str] = []
    if need and cooled:
        assignments.append("backfill")
    assignments.append("hunt")
    return {
        "assignments": assignments,
        "backfill_needed": bool(need),
        "backfill_ready": bool(need and cooled),
        "reason": why,
        "hint": hint,
        "floor_usd": floor,
    }


def _write_board(candidates: List[Dict[str, Any]], *, scanned: int, qualifying: int) -> None:
    board = {
        "updated_at": _iso(),
        "scanned": scanned,
        "qualifying": qualifying,
        "gaps": [
            {
                "symbol": c.get("symbol"),
                "buy_venue": c.get("buy_venue"),
                "sell_venue": c.get("sell_venue"),
                "net_bps": c.get("net_bps"),
                "est_profit_usd": c.get("est_profit_usd"),
                "notional_usd": c.get("notional_usd"),
                "gross_bps": c.get("gross_bps"),
                "fee_bps": c.get("fee_bps"),
            }
            for c in candidates[:25]
        ],
    }
    ex._write_json(_BOARD_PATH, board)


def run_spread_hunter_tick(*, force: bool = False) -> Dict[str, Any]:
    """One hunter tick: assignments → optional backfill → hunt → prefund → execute."""
    if not spread_hunter_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled"}

    min_bps = _cfg_float("SPREAD_HUNTER_MIN_BPS", 12.0)
    min_profit = _cfg_float("SPREAD_HUNTER_MIN_PROFIT_USD", 0.02)
    notional = _cfg_float("SPREAD_HUNTER_NOTIONAL_USD", 15.0)
    min_live = _cfg_float("SPREAD_HUNTER_MIN_LIVE_USD", 10.0)
    max_exec = _cfg_int("SPREAD_HUNTER_MAX_EXEC", 1)
    scan_limit = _cfg_int("SPREAD_HUNTER_SCAN_LIMIT", 100)
    batch_size = _cfg_int("SPREAD_HUNTER_BATCH_SIZE", 25)
    max_skew = _cfg_float("SPREAD_HUNTER_MAX_MID_SKEW_BPS", 80.0)
    # Recheck must still clear this floor (slightly softer than min_bps to allow tiny drift).
    collapse_bps = _cfg_float("SPREAD_HUNTER_COLLAPSE_BPS", max(0.0, min_bps - 3.0))
    agent_id = (os.environ.get("SPREAD_HUNTER_AGENT_ID") or "arb_live_dual_farm").strip()
    venues = list(_EXTERNAL)
    cfg = conn.load_connectors_config()
    xfer_bps = float(arb._effective_transfer_cost_bps(cfg))

    plan = decide_hunter_assignments(state=_load_state())
    assignments = list(plan.get("assignments") or ["hunt"])
    backfill_res = None
    if "backfill" in assignments:
        backfill_res = run_hunter_backfill_assignment(
            hint=plan.get("hint") if isinstance(plan.get("hint"), dict) else None,
            raise_symbols=None,
        )
        if backfill_res.get("raised_usd"):
            time.sleep(1.0)
            try:
                from backend.services import exchange_venue_api_service as vapi

                vapi.refresh_venue_balances(venues, force=True)
            except Exception:
                pass

    universe = _build_universe(scan_limit=scan_limit)
    symbols = list(universe["symbols"])
    # Head kill-shot: prioritize the named symbol for this hunt cycle.
    try:
        from backend.services.exchange_profit_head_service import get_kill_shot

        ks = get_kill_shot()
        if ks and str(ks.get("arm") or "hunter") == "hunter" and ks.get("symbol"):
            sym = str(ks["symbol"]).upper()
            symbols = [sym] + [s for s in symbols if s != sym]
    except Exception:
        ks = None
    # Prefer head prefund-hint symbol on the hunt pass too.
    hint_sym = None
    if isinstance(plan.get("hint"), dict) and plan["hint"].get("symbol"):
        hint_sym = str(plan["hint"]["symbol"]).upper()
        symbols = [hint_sym] + [s for s in symbols if s != hint_sym]
    out: Dict[str, Any] = {
        "success": True,
        "arm": "spread_hunter",
        "assignments": assignments,
        "assignment_reason": plan.get("reason"),
        "scanned_at": _iso(),
        "min_bps": min_bps,
        "min_profit_usd": min_profit,
        "notional_usd": notional,
        "scan_limit": scan_limit,
        "universe_size": len(symbols),
        "catalog_count": universe["catalog_count"],
        "hot_count": universe["hot_count"],
        "symbols_sample": symbols[:12],
        "kill_shot": ks,
        "prefund_hint": plan.get("hint"),
        "opportunity_count": 0,
        "qualifying": 0,
        "top": None,
        "board_top": [],
        "executed": False,
        "prefund": None,
        "backfill": backfill_res,
        "skip_reason": None,
    }
    if "hunt" not in assignments:
        out["skip_reason"] = "assignment_backfill_only"
        _persist_tick(out)
        return out
    if not symbols:
        out["skip_reason"] = "empty_universe"
        _persist_tick(out)
        return out

    annotated = _batch_scan(
        symbols,
        venues=venues,
        notional_usd=notional,
        batch_size=batch_size,
        xfer_bps=xfer_bps,
        cfg=cfg,
    )
    out["opportunity_count"] = len(annotated)
    qualifying = [
        o for o in annotated
        if _is_external_opp(o)
        and float(o.get("net_bps") or 0) >= min_bps
        and float(o.get("est_profit_usd") or 0) >= min_profit
        and o.get("profitable")
    ]
    # Keep Binance live: when BN quote is funded, prefer buy-on-binance routes.
    bn_free = 0.0
    try:
        bn_free = float(_venue_free_quote("binance").get("free") or 0)
    except Exception:
        bn_free = 0.0
    prefer_bn_buy = bn_free >= _cfg_float("SPREAD_HUNTER_BN_BUY_FLOOR_USD", 12.0)

    def _rank_opp(o: Dict[str, Any]) -> float:
        bps = float(o.get("net_bps") or 0)
        if prefer_bn_buy and str(o.get("buy_venue") or "").lower() == "binance":
            return bps + 8.0
        return bps

    qualifying.sort(key=_rank_opp, reverse=True)
    annotated.sort(key=_rank_opp, reverse=True)
    out["qualifying"] = len(qualifying)
    out["prefer_binance_buy"] = prefer_bn_buy
    _write_board(qualifying or annotated, scanned=len(symbols), qualifying=len(qualifying))
    out["board_top"] = [
        {
            "symbol": o.get("symbol"),
            "buy_venue": o.get("buy_venue"),
            "sell_venue": o.get("sell_venue"),
            "net_bps": o.get("net_bps"),
            "est_profit_usd": o.get("est_profit_usd"),
        }
        for o in (qualifying or annotated)[:5]
    ]

    if qualifying:
        top = qualifying[0]
        out["top"] = {
            "symbol": top.get("symbol"),
            "buy_venue": top.get("buy_venue"),
            "sell_venue": top.get("sell_venue"),
            "net_bps": top.get("net_bps"),
            "est_profit_usd": top.get("est_profit_usd"),
        }
    elif annotated:
        top = annotated[0]
        out["top"] = {
            "symbol": top.get("symbol"),
            "buy_venue": top.get("buy_venue"),
            "sell_venue": top.get("sell_venue"),
            "net_bps": top.get("net_bps"),
            "est_profit_usd": top.get("est_profit_usd"),
            "below_threshold": True,
        }
        out["skip_reason"] = "no_qualifying_edge"
        _persist_tick(out)
        return out
    else:
        out["skip_reason"] = "no_external_spreads"
        _persist_tick(out)
        return out

    from backend.services.exchange_live_execution_service import book_agent_profit, execute_spatial_arbitrage
    from backend.services.exchange_profit_path_service import record_execution, record_scan
    from backend.services import exchange_venue_api_service as vapi

    for opp in qualifying[: max(1, max_exec)]:
        recheck = _recheck_live(
            opp,
            notional_usd=float(opp.get("notional_usd") or notional),
            cfg=cfg,
            xfer_bps=xfer_bps,
            max_skew_bps=max_skew,
            collapse_bps=collapse_bps,
        )
        if not recheck.get("ok"):
            out["skip_reason"] = str(recheck.get("reason") or "recheck_failed")
            out["recheck"] = {
                "reason": recheck.get("reason"),
                "opportunity": {
                    "symbol": (recheck.get("opportunity") or {}).get("symbol") or opp.get("symbol"),
                    "buy_venue": (recheck.get("opportunity") or {}).get("buy_venue") or opp.get("buy_venue"),
                    "sell_venue": (recheck.get("opportunity") or {}).get("sell_venue") or opp.get("sell_venue"),
                    "net_bps": (recheck.get("opportunity") or {}).get("net_bps"),
                    "est_profit_usd": (recheck.get("opportunity") or {}).get("est_profit_usd"),
                    "notional_usd": (recheck.get("opportunity") or {}).get("notional_usd") or opp.get("notional_usd"),
                    "mid_skew_bps": (recheck.get("opportunity") or {}).get("mid_skew_bps"),
                    "regime_factor": (recheck.get("opportunity") or {}).get("regime_factor"),
                },
            }
            if out["skip_reason"] == "regime_skew_too_wide":
                try:
                    from backend.services.exchange_latch_sniper_service import arm_latch

                    ro = out["recheck"]["opportunity"]
                    arm_latch(
                        symbol=str(ro.get("symbol") or ""),
                        buy_venue=str(ro.get("buy_venue") or ""),
                        sell_venue=str(ro.get("sell_venue") or ""),
                        net_bps=float(ro.get("net_bps") or opp.get("net_bps") or 0),
                        mid_skew_bps=float(ro.get("mid_skew_bps") or 0),
                        est_profit_usd=float(ro.get("est_profit_usd") or opp.get("est_profit_usd") or 0),
                        notional_usd=float(ro.get("notional_usd") or notional),
                        source="hunter_skew",
                    )
                    out["latch_armed"] = True
                except Exception:
                    pass
            continue

        trade_opp = recheck["opportunity"]
        if float(trade_opp.get("net_bps") or 0) < min_bps:
            out["skip_reason"] = "recheck_below_min_bps"
            continue
        if float(trade_opp.get("est_profit_usd") or 0) < min_profit:
            out["skip_reason"] = "recheck_below_min_profit"
            continue

        prepared = arb.prepare_live_opportunity(
            trade_opp, configured_usd=float(trade_opp.get("notional_usd") or notional),
            buffer_pct=0.03, min_live_usd=min_live,
        )
        if not prepared.get("ok") and _prefund_enabled():
            need = max(min_live, float(prepared.get("requested_usd") or notional))
            wheel = _try_fund_wheel(
                trade_opp, agent_id=agent_id, need_usd=need, raise_symbols=symbols,
            )
            out["prefund"] = wheel
            if wheel.get("success"):
                time.sleep(1.0)
                vapi.refresh_venue_balances(venues, force=True)
                prepared = arb.prepare_live_opportunity(
                    trade_opp, configured_usd=float(trade_opp.get("notional_usd") or notional),
                    buffer_pct=0.03, min_live_usd=min_live,
                )

        if not prepared.get("ok"):
            out["skip_reason"] = str(prepared.get("reason") or "insufficient_venue_balance")
            out["max_funded_usd"] = prepared.get("max_funded_usd")
            continue

        ready = prepared["opportunity"]
        # Final math stamp after sizing.
        ready = _annotate_opportunity(
            ready,
            notional_usd=float(ready.get("notional_usd") or notional),
            cfg=cfg,
            xfer_bps=xfer_bps,
        )
        if float(ready.get("est_profit_usd") or 0) < min_profit or float(ready.get("net_bps") or 0) < min_bps:
            out["skip_reason"] = "sized_below_profit_gate"
            continue

        path_id = record_scan(
            agent_id=agent_id,
            strategy="spread_hunter_arm",
            best=ready,
            threshold_bps=min_bps,
            mode="live" if arb.live_enabled() else "paper",
            decision="attempt",
            notional_usd=float(ready.get("notional_usd") or notional),
            venues=venues,
        )
        exec_res = execute_spatial_arbitrage(ready, agent_id=agent_id)
        try:
            from backend.services.exchange_closer_claw_service import note_execution_legs

            note_execution_legs(ready, exec_res, source="hunter")
        except Exception:
            pass
        record_execution(
            path_id=path_id,
            agent_id=agent_id,
            opp=ready,
            exec_res=exec_res,
            strategy="spread_hunter_arm",
            threshold_bps=min_bps,
            venues=venues,
        )
        try:
            from backend.services.exchange_profit_baseline_service import record_arb_baseline

            record_arb_baseline(ready, exec_res, source="spread_hunter_arm", agent_id=agent_id)
        except Exception:
            pass
        book_agent_profit(agent_id, ready, exec_res)
        fleet_id = (os.environ.get("SPREAD_HUNTER_FLEET_AGENT_ID") or "fleet_extended_profit_fast").strip()
        if fleet_id and fleet_id != agent_id and exec_res.get("success"):
            try:
                book_agent_profit(fleet_id, ready, exec_res)
            except Exception:
                pass

        out["executed"] = bool(exec_res.get("success"))
        out["mode"] = exec_res.get("mode")
        out["profit_path_id"] = path_id
        out["trade"] = {
            "symbol": ready.get("symbol"),
            "net_bps": ready.get("net_bps"),
            "est_profit_usd": ready.get("est_profit_usd"),
            "notional_usd": ready.get("notional_usd"),
            "buy_venue": ready.get("buy_venue"),
            "sell_venue": ready.get("sell_venue"),
            "regime_factor": trade_opp.get("regime_factor"),
            "mid_skew_bps": trade_opp.get("mid_skew_bps"),
        }
        if exec_res.get("success"):
            out["skip_reason"] = None
            _persist_tick(out)
            return out
        out["skip_reason"] = str(exec_res.get("error") or "execution_failed")

    _persist_tick(out)
    return out


def _persist_tick(out: Dict[str, Any]) -> None:
    state = _load_state()
    state.update({
        "updated_at": _iso(),
        "last_tick": {
            "scanned_at": out.get("scanned_at"),
            "assignments": out.get("assignments"),
            "assignment_reason": out.get("assignment_reason"),
            "universe_size": out.get("universe_size"),
            "opportunity_count": out.get("opportunity_count"),
            "qualifying": out.get("qualifying"),
            "top": out.get("top"),
            "board_top": out.get("board_top"),
            "executed": out.get("executed"),
            "skip_reason": out.get("skip_reason"),
            "recheck": out.get("recheck"),
            "latch_armed": out.get("latch_armed"),
            "prefund": out.get("prefund"),
            "backfill": {
                "success": (out.get("backfill") or {}).get("success"),
                "reason": (out.get("backfill") or {}).get("reason"),
                "raised_usd": (out.get("backfill") or {}).get("raised_usd"),
                "total_free_usd": (out.get("backfill") or {}).get("total_free_usd"),
            } if out.get("backfill") else None,
            "trade": out.get("trade"),
        },
    })
    if out.get("backfill"):
        state["last_backfill_at"] = out.get("scanned_at")
        state["last_backfill"] = out.get("backfill")
        if (out.get("backfill") or {}).get("raised_usd"):
            state["backfill_count"] = int(state.get("backfill_count") or 0) + 1
    if out.get("executed"):
        state["last_exec_at"] = out.get("scanned_at")
        state["last_exec"] = out.get("trade")
        state["exec_count"] = int(state.get("exec_count") or 0) + 1
        try:
            from backend.services.exchange_profit_head_service import clear_kill_shot

            clear_kill_shot()
        except Exception:
            pass
    _save_state(state)


def spread_hunter_status() -> Dict[str, Any]:
    state = _load_state()
    board = ex._read_json(_BOARD_PATH, {})
    return {
        "success": True,
        "enabled": spread_hunter_enabled(),
        "live": arb.live_enabled(),
        "min_bps": _cfg_float("SPREAD_HUNTER_MIN_BPS", 12.0),
        "min_profit_usd": _cfg_float("SPREAD_HUNTER_MIN_PROFIT_USD", 0.02),
        "notional_usd": _cfg_float("SPREAD_HUNTER_NOTIONAL_USD", 15.0),
        "scan_limit": _cfg_int("SPREAD_HUNTER_SCAN_LIMIT", 100),
        "prefund": _prefund_enabled(),
        "backfill": _backfill_enabled(),
        "backfill_floor_usd": _backfill_floor_usd(),
        "assignments": ["backfill", "hunt"],
        "state": state,
        "board": board if isinstance(board, dict) else {},
    }
