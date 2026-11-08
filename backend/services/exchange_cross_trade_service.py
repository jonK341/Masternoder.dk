"""Cross-venue auto-trader — SEARCH continuously and EXECUTE the spatial arb the instant a
profitable price difference appears across Binance / NonKYC / XeggeX.

Unlike the read-only scanner, this acts: on every pass it finds the best cross-venue price
difference (buy cheap on one venue, sell dear on another), and if the edge clears the
configured threshold (net of both venues' fees) it fires both legs. ``order_style=limit``
caps each leg at the price that produced the edge (Binance IOC, other venues cancelled if
still resting). ``order_style=market`` sends market orders. Both go through
``exchange_live_execution_service.execute_spatial_arbitrage``.

Safety:
  * Paper by default. Places REAL orders only when BOTH ``EXCHANGE_ARBITRAGE_LIVE=1`` and
    ``EXCHANGE_CROSS_TRADE_LIVE=1`` are set (plus credentials + funding on both legs).
  * Per-trade notional cap, per-route cooldown, and a daily realized-loss cap that halts.
  * Every decision and fill is written to an append-only audit ledger for later review
    ("examination of details") — symbol, route, gross/net bps, mode, order ids, P&L.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_cross_trade_config.json")
_AUDIT_PATH = os.path.join(ex._DATA_DIR, "cross_trade_audit.jsonl")
_STATE_PATH = os.path.join(ex._DATA_DIR, "cross_trade_state.json")

_AGENT_ID = "cross_trade_auto"

# Coins whose own network credits in a few seconds and that trade against USDT on NonKYC
# and against USDC/USDT on Binance. Nothing on a chain is instant after it leaves the
# exchange; these are the ones where a one-confirmation credit is a few seconds.
# SOL is included because the chain is fast, but exchange queues are often longer.
FAST_USDT_COINS: Tuple[str, ...] = ("XRP", "XLM", "ALGO", "TRX", "SOL")
_FAST_CREDIT_SEC = {"XRP": 5, "XLM": 5, "ALGO": 5, "TRX": 5, "SOL": 30}
_NONKYC_BOOK_URL = "https://api.nonkyc.io/api/v2/market/orderbook?symbol={pair}"
_BINANCE_BOOK_URLS = (
    "https://api.binance.com/api/v3/ticker/bookTicker?symbol={pair}",
    "https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol={pair}",
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "venues": ["binance", "nonkyc", "xeggex"],
        "min_net_bps": 8.0,          # execute only when the edge (after fees) clears this
        "notional_usd": 25.0,        # per-trade size
        "cooldown_seconds": 3.0,     # min gap between executions on the same route
        "max_trades_per_run": 3,     # cap executions per search pass
        "daily_loss_cap_usd": 10.0,  # halt when realized losses for the day exceed this
        "fast_withdraw_only": False,
        "symbols": list(FAST_USDT_COINS),
        "order_style": "market",     # market | limit (price-capped)
    }


def _clampf(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, None)
    if not isinstance(cfg, dict):
        cfg = _default_config()
        ex._write_json(_CFG_PATH, cfg)
    base = _default_config()
    base.update({k: v for k, v in cfg.items() if v is not None})
    base["min_net_bps"] = _clampf(base.get("min_net_bps"), 0.0, 1e5, 8.0)
    base["notional_usd"] = _clampf(base.get("notional_usd"), 1.0, 1e6, 25.0)
    base["cooldown_seconds"] = _clampf(base.get("cooldown_seconds"), 0.0, 3600.0, 3.0)
    base["max_trades_per_run"] = int(_clampf(base.get("max_trades_per_run"), 1, 50, 3))
    base["daily_loss_cap_usd"] = _clampf(base.get("daily_loss_cap_usd"), 0.0, 1e6, 10.0)
    if not isinstance(base.get("venues"), list) or not base["venues"]:
        base["venues"] = ["binance", "nonkyc", "xeggex"]
    base["fast_withdraw_only"] = bool(base.get("fast_withdraw_only"))
    symbols = base.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        base["symbols"] = list(FAST_USDT_COINS)
    else:
        base["symbols"] = [str(s).upper() for s in symbols if str(s).strip()]
    style = str(base.get("order_style") or "market").lower()
    base["order_style"] = style if style in ("market", "limit") else "market"
    return base


def save_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k, v in (patch or {}).items():
        if k in cfg and v is not None:
            cfg[k] = v
    ex._write_json(_CFG_PATH, cfg)
    return cfg


def set_enabled(enabled: bool) -> Dict[str, Any]:
    cfg = save_config({"enabled": bool(enabled)})
    return {"success": True, "enabled": cfg["enabled"]}


def fast_usdt_coins() -> List[Dict[str, Any]]:
    """USDT-linked coins with a few-second credit. Sorted by typical credit time."""
    return [
        {
            "symbol": sym,
            "quote": "USDT",
            "credit_sec": _FAST_CREDIT_SEC[sym],
            "pair_nonkyc": f"{sym}_USDT",
            "pair_binance_usdc": f"{sym}USDC",
            "pair_binance_usdt": f"{sym}USDT",
        }
        for sym in FAST_USDT_COINS
    ]


def _cross_fee_bps() -> float:
    """Binance taker + NonKYC taker + the prefunded buffer. No chain fee in this number."""
    cfg = conn.load_connectors_config()
    vmap = conn._venue_map(cfg)
    binance = float((vmap.get("binance") or {}).get("fee_taker_bps") or 10)
    nonkyc = float((vmap.get("nonkyc") or {}).get("fee_taker_bps") or 20)
    transfer = float(cfg.get("prefunded_transfer_cost_bps") or cfg.get("transfer_cost_bps") or 6)
    return binance + nonkyc + transfer


def walk_quote_usd(
    levels: Sequence[Tuple[float, float]],
    *,
    side: str,
    counter_price: float,
    hurdle_bps: float,
) -> float:
    """Quote notional that still clears ``hurdle_bps`` against ``counter_price``.

    ``side='sell'`` walks bids (we hit the bid). ``side='buy'`` walks asks.
    Levels must be price/qty. They are sorted best-first here.
    """
    if counter_price <= 0 or hurdle_bps < 0:
        return 0.0
    hurdle = 1.0 + float(hurdle_bps) / 10000.0
    rows = [(float(p), float(q)) for p, q in levels if float(p) > 0 and float(q) > 0]
    usd = 0.0
    if side == "sell":
        floor = counter_price * hurdle
        for price, qty in sorted(rows, key=lambda row: row[0], reverse=True):
            if price < floor:
                break
            usd += price * qty
        return usd
    if side == "buy":
        ceil = counter_price / hurdle
        for price, qty in sorted(rows, key=lambda row: row[0]):
            if price > ceil:
                break
            usd += price * qty
        return usd
    raise ValueError(f"unknown side {side}")


def _get_json(url: str, timeout: float = 8.0) -> Optional[Any]:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "masternoder-cross-trade/1.0"})
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def fetch_nonkyc_book(symbol: str) -> Dict[str, List[Tuple[float, float]]]:
    """Public NonKYC USDT book. Empty on failure (fail closed)."""
    pair = f"{str(symbol).upper()}_USDT"
    body = _get_json(_NONKYC_BOOK_URL.format(pair=pair))
    if not isinstance(body, dict):
        return {"bids": [], "asks": []}

    def _levels(key: str) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for row in body.get(key) or []:
            if isinstance(row, dict):
                price, qty = row.get("price"), row.get("quantity")
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                price, qty = row[0], row[1]
            else:
                continue
            try:
                out.append((float(price), float(qty)))
            except (TypeError, ValueError):
                continue
        return out

    return {"bids": _levels("bids"), "asks": _levels("asks")}


def _binance_top(symbol: str) -> Optional[Dict[str, float]]:
    """Top of book. Tries Binance, then the public market-data mirror (regions that 451 the main host)."""
    base = str(symbol).upper()
    for quote in ("USDC", "USDT"):
        pair = f"{base}{quote}"
        for template in _BINANCE_BOOK_URLS:
            body = _get_json(template.format(pair=pair))
            if not isinstance(body, dict):
                continue
            try:
                bid = float(body.get("bidPrice") or 0)
                ask = float(body.get("askPrice") or 0)
            except (TypeError, ValueError):
                continue
            if bid > 0 and ask > 0:
                return {"bid": bid, "ask": ask, "quote": quote, "pair": pair}
    return None


def nonkyc_executable_usd(diff: Dict[str, Any], *, hurdle_bps: float,
                          book: Optional[Dict[str, List[Tuple[float, float]]]] = None) -> float:
    """How much USDT on the NonKYC side still clears the hurdle. No NonKYC leg -> the clip size."""
    buy = str(diff.get("buy_venue") or "").lower()
    sell = str(diff.get("sell_venue") or "").lower()
    if "nonkyc" not in (buy, sell):
        return float(diff.get("notional_usd") or 0) or 1e9
    if book is None:
        book = fetch_nonkyc_book(str(diff.get("symbol") or ""))
    buy_ask = float(diff.get("buy_ask") or 0)
    sell_bid = float(diff.get("sell_bid") or 0)
    if sell == "nonkyc":
        return walk_quote_usd(book.get("bids") or [], side="sell", counter_price=buy_ask, hurdle_bps=hurdle_bps)
    return walk_quote_usd(book.get("asks") or [], side="buy", counter_price=sell_bid, hurdle_bps=hurdle_bps)


def preview_fast_usdt(*, notional_usd: float = 25.0, min_net_bps: float = 18.0) -> Dict[str, Any]:
    """Read-only scan of the fast USDT coins. Places no order and no withdrawal."""
    fee_bps = _cross_fee_bps()
    hurdle = fee_bps + float(min_net_bps)
    rows: List[Dict[str, Any]] = []
    for spec in fast_usdt_coins():
        sym = spec["symbol"]
        top = _binance_top(sym)
        book = fetch_nonkyc_book(sym)
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        row: Dict[str, Any] = {
            "symbol": sym,
            "credit_sec": spec["credit_sec"],
            "nonkyc_pair": spec["pair_nonkyc"],
            "binance": top,
            "nonkyc_bid": bids[0][0] if bids else None,
            "nonkyc_ask": asks[0][0] if asks else None,
            "executable_usd": 0.0,
            "net_bps": None,
            "route": None,
            "decision": "no_book",
        }
        if not top or not bids or not asks:
            rows.append(row)
            continue
        # Two directions. Keep the one with more executable size, then higher net.
        candidates = []
        sell_usd = walk_quote_usd(bids, side="sell", counter_price=top["ask"], hurdle_bps=hurdle)
        if top["ask"] > 0 and bids[0][0] > 0:
            gross = (bids[0][0] - top["ask"]) / top["ask"] * 10000.0
            candidates.append({
                "route": f"binance→nonkyc",
                "net_bps": round(gross - fee_bps, 2),
                "executable_usd": round(sell_usd, 2),
                "buy_ask": top["ask"],
                "sell_bid": bids[0][0],
            })
        buy_usd = walk_quote_usd(asks, side="buy", counter_price=top["bid"], hurdle_bps=hurdle)
        if top["bid"] > 0 and asks[0][0] > 0:
            gross = (top["bid"] - asks[0][0]) / asks[0][0] * 10000.0
            candidates.append({
                "route": "nonkyc→binance",
                "net_bps": round(gross - fee_bps, 2),
                "executable_usd": round(buy_usd, 2),
                "buy_ask": asks[0][0],
                "sell_bid": top["bid"],
            })
        if not candidates:
            rows.append(row)
            continue
        best = max(candidates, key=lambda c: (c["executable_usd"], c["net_bps"]))
        row.update(best)
        if best["executable_usd"] >= notional_usd and best["net_bps"] >= min_net_bps:
            row["decision"] = "paper_candidate"
        elif best["net_bps"] >= min_net_bps:
            row["decision"] = "book_too_thin"
        else:
            row["decision"] = "below_fees"
        rows.append(row)
    tradable = [r for r in rows if r["decision"] == "paper_candidate"]
    return {
        "success": True,
        "fee_bps": fee_bps,
        "min_net_bps": min_net_bps,
        "notional_usd": notional_usd,
        "withdrawal_broadcast": False,
        "live": False,
        "coins": rows,
        "tradable_count": len(tradable),
    }


def cron_hook_ok(presented: str) -> bool:
    """True when the caller presented the cron hook key or the exchange admin key."""
    got = str(presented or "").strip()
    if not got:
        return False
    secret = str(os.environ.get("EXCHANGE_CRON_HOOK_KEY") or "").strip()
    admin = str(
        os.environ.get("EXCHANGE_ADMIN_KEY") or os.environ.get("COGS_ADMIN_REPORT_KEY") or ""
    ).strip()
    if secret and got == secret:
        return True
    return bool(admin) and got == admin


def _open_order_rows(body: Any) -> List[Dict[str, Any]]:
    if isinstance(body, list):
        return [row for row in body if isinstance(row, dict)]
    if isinstance(body, dict):
        for key in ("orders", "data", "result"):
            rows = body.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def cancel_our_open_limits() -> List[Dict[str, Any]]:
    """Cancel resting limits this bot placed (client id starts with ``arb-``)."""
    from backend.services import exchange_venue_api_service as vapi

    cfg = load_config()
    released: List[Dict[str, Any]] = []
    for venue in cfg.get("venues") or []:
        for sym in cfg.get("symbols") or []:
            try:
                res = vapi.get_open_orders(str(venue), str(sym), dry_run=False)
            except Exception:
                continue
            if not res.get("success") or res.get("simulated"):
                continue
            for od in _open_order_rows(res.get("body")):
                coid = str(
                    od.get("clientOrderId")
                    or od.get("origClientOrderId")
                    or od.get("userProvidedId")
                    or od.get("client_order_id")
                    or ""
                )
                if not coid.startswith("arb-"):
                    continue
                oid = od.get("orderId") or od.get("id") or od.get("_id")
                if oid in (None, ""):
                    continue
                try:
                    vapi.cancel_order(str(venue), str(sym), str(oid), dry_run=False)
                except Exception:
                    continue
                released.append({"venue": str(venue), "symbol": str(sym), "order_id": str(oid)})
                _audit({"event": "cancel_resting_limit", "venue": venue, "symbol": sym, "order_id": str(oid)})
    return released


def cross_trade_live_enabled() -> bool:
    """Real cross-venue orders require BOTH the arbitrage gate and the dedicated cross-trade
    gate. Missing either -> paper (search + simulate, no real orders)."""
    def _on(k: str) -> bool:
        return str(os.environ.get(k, "")).strip().lower() in ("1", "true", "yes")
    return _on("EXCHANGE_ARBITRAGE_LIVE") and _on("EXCHANGE_CROSS_TRADE_LIVE")


def _read_state() -> Dict[str, Any]:
    st = ex._read_json(_STATE_PATH, {})
    return st if isinstance(st, dict) else {}


def _write_state(st: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, st)


def _audit(row: Dict[str, Any]) -> None:
    try:
        ex._append_jsonl(_AUDIT_PATH, {"ts": _iso(), **row})
    except Exception:
        pass


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def find_opportunities(*, min_net_bps: Optional[float] = None,
                       notional: Optional[float] = None,
                       venues: Optional[List[str]] = None) -> Dict[str, Any]:
    """Search current cross-venue price differences (delegates to the grid scanner)."""
    from backend.services import exchange_grid_bot_service as grid
    cfg = load_config()
    symbols = None
    if cfg.get("fast_withdraw_only"):
        allow = set(FAST_USDT_COINS)
        symbols = [s for s in cfg.get("symbols") or FAST_USDT_COINS if s in allow]
    return grid.scan_cross_venue_differences(
        venues=venues or cfg["venues"],
        symbols=symbols,
        min_net_bps=(min_net_bps if min_net_bps is not None else cfg["min_net_bps"]),
        notional_usd=notional or cfg["notional_usd"],
    )


def funding_status(diff: Dict[str, Any]) -> Dict[str, Any]:
    """Can this cross-venue difference actually be executed RIGHT NOW?

    There is no atomic trade that spans two exchanges — each leg settles on its own venue.
    So a cross-venue arb is only executable when BOTH sides are pre-funded: the buy venue holds
    enough quote (USDC/USDT) and the sell venue already holds enough of the coin. This reports
    that readiness per leg (the honest 'is there a real trade here' check)."""
    from backend.services import exchange_venue_api_service as vapi
    cfg = load_config()
    opp = {
        "symbol": diff.get("symbol"), "buy_venue": diff.get("buy_venue"),
        "sell_venue": diff.get("sell_venue"), "buy_ask": diff.get("buy_ask"),
        "notional_usd": float(cfg["notional_usd"]),
    }
    try:
        return vapi.opportunity_funded(opp)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def preview(*, min_net_bps: Optional[float] = None) -> Dict[str, Any]:
    """Search differences and annotate each with real executability (both legs pre-funded).

    ``executable_now_hedged`` = a genuine trade you can fire this instant against balances that
    already sit on both venues (you bank the spread; your net coin exposure stays ~flat).
    ``needs_funding_or_transfer`` = the edge exists but a side isn't funded — you'd have to move
    money onto a venue first (the slow part that no 'wormhole' removes)."""
    cfg = load_config()
    scan = find_opportunities(min_net_bps=(min_net_bps if min_net_bps is not None else 0.0))
    if not scan.get("success"):
        return {"success": False, "error": scan.get("error"), "candidates": []}
    out: List[Dict[str, Any]] = []
    for d in (scan.get("differences") or []):
        f = funding_status(d)
        both = bool(f.get("ok"))
        buy = f.get("buy") or {}
        sell = f.get("sell") or {}
        out.append({
            "symbol": d.get("symbol"), "route": d.get("route"),
            "buy_venue": d.get("buy_venue"), "sell_venue": d.get("sell_venue"),
            "net_bps": d.get("net_bps"), "est_profit_usd": d.get("est_profit_usd"),
            "buy_funded": bool(buy.get("ok")), "buy_need": buy.get("need"), "buy_free": buy.get("free"),
            "sell_funded": bool(sell.get("ok")), "sell_need": sell.get("need"), "sell_free": sell.get("free"),
            "executable_now": both,
            "verdict": "executable_now_hedged" if both else "needs_funding_or_transfer",
            "error": f.get("error"),
        })
    executable = sum(1 for c in out if c["executable_now"])
    return {"success": True, "count": len(out), "executable_now": executable,
            "min_net_bps": (min_net_bps if min_net_bps is not None else cfg["min_net_bps"]),
            "candidates": out,
            "note": "Cross-venue arb is pre-funded/hedged: both sides must hold inventory. "
                    "There is no single atomic trade across two exchanges."}


def rebalance_hint() -> Dict[str, Any]:
    """Summarize accumulated inventory skew from hedged trades and suggest transfers.

    Each hedged fill leaves the buy venue longer the coin and the sell venue shorter it; over
    many fills you must move coin buy→sell (and quote back) to keep trading — the periodic
    rebalance that replaces the impossible atomic cross-exchange trade."""
    state = _read_state()
    skew = state.get("skew") or {}
    moves: List[Dict[str, Any]] = []
    for venue, assets in skew.items():
        for asset, amt in (assets or {}).items():
            if abs(float(amt or 0)) > 1e-9:
                moves.append({"venue": venue, "asset": asset, "net_base": round(float(amt), 8),
                              "direction": "accumulating (move out)" if amt > 0 else "depleting (top up)"})
    moves.sort(key=lambda m: abs(m["net_base"]), reverse=True)
    return {"success": True, "skew": moves,
            "note": "Positive = venue is accumulating that coin (transfer some out); "
                    "negative = venue is running low (top it up)."}


def execute_opportunity(
    diff: Dict[str, Any],
    *,
    dry_run: Optional[bool] = None,
    force_live: bool = False,
) -> Dict[str, Any]:
    """Fire both legs for one spotted difference and audit the result."""
    from backend.services.exchange_live_execution_service import execute_spatial_arbitrage
    cfg = load_config()
    opp = {
        "symbol": diff.get("symbol"),
        "buy_venue": diff.get("buy_venue"),
        "sell_venue": diff.get("sell_venue"),
        "buy_ask": diff.get("buy_ask"),
        "sell_bid": diff.get("sell_bid"),
        "net_bps": diff.get("net_bps"),
        "notional_usd": float(cfg["notional_usd"]),
        "order_style": cfg.get("order_style") or "market",
    }
    if opp["order_style"] == "limit":
        opp["buy_limit"] = float(diff.get("buy_ask") or 0)
        opp["sell_limit"] = float(diff.get("sell_bid") or 0)
    if force_live:
        exec_dry: Optional[bool] = False
    else:
        env_live = cross_trade_live_enabled() if dry_run is None else (not dry_run)
        exec_dry = None if env_live else True
    res = execute_spatial_arbitrage(
        opp, agent_id=_AGENT_ID, dry_run=exec_dry, force_live=bool(force_live),
    )
    _audit({
        "event": "execute", "symbol": opp["symbol"],
        "route": f'{opp["buy_venue"]}\u2192{opp["sell_venue"]}',
        "net_bps": opp["net_bps"], "notional_usd": opp["notional_usd"],
        "order_style": opp.get("order_style"),
        "mode": res.get("mode"), "success": res.get("success"), "error": res.get("error"),
        "unhedged": res.get("unhedged"),
        "est_profit_usd": res.get("est_profit_usd"),
        "buy_order_id": (res.get("buy_order") or {}).get("order_id"),
        "sell_order_id": (res.get("sell_order") or {}).get("order_id"),
    })
    return res


def run_once(*, dry_run: Optional[bool] = None, force: bool = False,
             force_live: bool = False) -> Dict[str, Any]:
    """One search-and-execute pass: find the best differences and fire the ones that clear
    the threshold (respecting per-route cooldown and the daily loss cap)."""
    cfg = load_config()
    if not cfg.get("enabled") and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}

    state = _read_state()
    day = _today()
    if state.get("loss_day") != day:
        state["loss_day"] = day
        state["realized_loss_usd"] = 0.0
    loss_cap = float(cfg["daily_loss_cap_usd"])
    if loss_cap > 0 and float(state.get("realized_loss_usd") or 0) >= loss_cap:
        _write_state(state)
        return {"success": True, "halted": True, "reason": "daily_loss_cap",
                "realized_loss_usd": state.get("realized_loss_usd")}

    if force_live:
        live = True
    else:
        live = cross_trade_live_enabled() if dry_run is None else (not dry_run)
    released: List[Dict[str, Any]] = []
    if live:
        released = cancel_our_open_limits()
    scan = find_opportunities()
    if not scan.get("success"):
        _audit({"event": "search_error", "error": scan.get("error")})
        return {"success": False, "error": scan.get("error") or "search_failed",
                "searched": 0, "executed": []}
    diffs = scan.get("differences") or []

    now = time.time()
    last_exec = dict(state.get("last_exec") or {})
    executed: List[Dict[str, Any]] = []
    skipped_thin: List[Dict[str, Any]] = []
    min_bps = float(cfg["min_net_bps"])
    fast_only = bool(cfg.get("fast_withdraw_only"))
    allow = set(FAST_USDT_COINS)
    cap = int(cfg["max_trades_per_run"])
    pool = diffs if fast_only else diffs[:cap]
    for d in pool:
        if len(executed) >= cap:
            break
        if float(d.get("net_bps") or 0) < min_bps:
            continue
        sym = str(d.get("symbol") or "").upper()
        if fast_only and sym not in allow:
            continue
        key = f'{d.get("symbol")}:{d.get("buy_venue")}->{d.get("sell_venue")}'
        if now - float(last_exec.get(key) or 0) < float(cfg["cooldown_seconds"]):
            continue
        if fast_only:
            fee_bps = float(d.get("fee_bps") or _cross_fee_bps())
            depth = nonkyc_executable_usd(d, hurdle_bps=fee_bps + min_bps)
            if depth < float(cfg["notional_usd"]):
                skipped_thin.append({
                    "route": key, "symbol": sym, "net_bps": d.get("net_bps"),
                    "executable_usd": round(depth, 2), "reason": "book_too_thin",
                })
                _audit({"event": "skip_thin_book", "symbol": sym, "route": key,
                        "net_bps": d.get("net_bps"), "executable_usd": round(depth, 2)})
                continue
        res = execute_opportunity(d, dry_run=dry_run, force_live=force_live)
        last_exec[key] = now
        profit = float(res.get("est_profit_usd") or 0) if res.get("success") else 0.0
        if profit < 0:
            state["realized_loss_usd"] = round(float(state.get("realized_loss_usd") or 0) - profit, 6)
        # Track inventory skew: a hedged fill leaves the buy venue longer the coin and the sell
        # venue shorter it. Accumulated skew tells us when to rebalance across venues.
        if res.get("success"):
            qty = float(res.get("quantity") or 0)
            sym = str(d.get("symbol") or "").upper()
            skew = state.setdefault("skew", {})
            bv = skew.setdefault(str(d.get("buy_venue")), {})
            sv = skew.setdefault(str(d.get("sell_venue")), {})
            bv[sym] = round(float(bv.get(sym) or 0) + qty, 10)
            sv[sym] = round(float(sv.get(sym) or 0) - qty, 10)
        executed.append({
            "route": key, "symbol": d.get("symbol"), "net_bps": d.get("net_bps"),
            "mode": res.get("mode"), "success": res.get("success"),
            "error": res.get("error"), "est_profit_usd": res.get("est_profit_usd"),
        })
    state["last_exec"] = last_exec
    state["last_run_at"] = _iso()
    _write_state(state)
    return {"success": True, "searched": scan.get("count"), "candidates": len(diffs),
            "executed": executed, "skipped_thin": skipped_thin, "live": live,
            "order_style": cfg.get("order_style"),
            "released_limits": released,
            "min_net_bps": min_bps, "withdrawal_broadcast": False}


def history(limit: int = 50) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    try:
        if os.path.isfile(_AUDIT_PATH):
            with open(_AUDIT_PATH, encoding="utf-8") as fh:
                lines = fh.readlines()[-int(limit):]
            import json as _json
            for ln in lines:
                ln = ln.strip()
                if ln:
                    try:
                        rows.append(_json.loads(ln))
                    except Exception:
                        pass
    except Exception:
        pass
    rows.reverse()
    return {"success": True, "count": len(rows), "events": rows}


def status() -> Dict[str, Any]:
    cfg = load_config()
    state = _read_state()
    hist = history(limit=200)["events"]
    fills = [e for e in hist if e.get("event") == "execute" and e.get("success")]
    realized = round(sum(float(e.get("est_profit_usd") or 0) for e in fills), 6)
    return {
        "success": True,
        "enabled": cfg.get("enabled"),
        "live": cross_trade_live_enabled(),
        "config": {k: cfg.get(k) for k in ("venues", "symbols", "fast_withdraw_only",
                                           "min_net_bps", "notional_usd",
                                           "cooldown_seconds", "max_trades_per_run",
                                           "daily_loss_cap_usd", "order_style")},
        "fast_usdt_coins": [c["symbol"] for c in fast_usdt_coins()],
        "last_run_at": state.get("last_run_at"),
        "realized_loss_usd_today": state.get("realized_loss_usd"),
        "executed_fills": len(fills),
        "realized_pnl_usd": realized,
        "rebalance": rebalance_hint().get("skew"),
        "recent": hist[:12],
    }
