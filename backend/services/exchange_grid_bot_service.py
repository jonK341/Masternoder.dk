"""Grid / market-maker bot — posts limit orders around mid and books small wins on oscillation.

Unlike arbitrage (which pays taker fees that exceed the edge on liquid venues), a grid bot
EARNS the spread by placing maker limit orders: buy below mid, sell above. It realizes a small
profit each time price oscillates through a level pair. This is NOT risk-free — it accumulates
inventory and loses in strong trends — so it is bounded by a per-asset inventory cap and a hard
loss cap that halts the bot and cancels all orders.

Paper by default (in-process fill simulation, no real orders). Live requires
``EXCHANGE_GRID_LIVE=1`` + ``EXCHANGE_ARBITRAGE_LIVE=1`` and venue credentials, and places real
limit orders via ``exchange_venue_api_service``.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_grid_bot_config.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "grid_bot_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "grid_bot_ledger.jsonl")
_PROFIT_INDEX_PATH = os.path.join(ex._DATA_DIR, "profit_pair_search_index.json")
_PAIR_CATALOG_PATH = os.path.join(ex._DATA_DIR, "profit_pair_catalog_cache.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "venue": "binance",
        "assets": ["DOGE"],
        "grid_levels": 3,
        "grid_step_pct": 0.004,        # 0.4% between levels
        "order_size_usd": 6.0,          # per grid order (>= venue min-notional)
        "max_inventory_usd": 15.0,      # per-asset inventory cap
        "hard_loss_cap_usd": 5.0,       # halt bot when total PnL <= -cap
        "min_spread_bps": 8.0,          # asset selection: min quoted spread
        "min_vol_pct": 0.5,             # asset selection: min recent volatility %
        "min_notional_usd": 5.0,        # skip orders below the venue minimum notional
        # Sell-from-existing: when the bot has no accumulated inventory yet, seed SELL levels
        # against the coin you already hold on the venue (e.g. DOGE). This lets the grid trade
        # when you hold the base asset but little quote (USDC). Trigger/kill switch — set false
        # to stop selling your existing coin.
        "allow_sell_existing_inventory": True,
        "taker_fee_bps": 10.0,
        "maker_fee_bps": 10.0,
        "tick_cooldown_seconds": 20,
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
    # Validate/clamp numeric settings so a bad edit can't produce nonsensical orders.
    base["grid_levels"] = int(_clampf(base.get("grid_levels"), 1, 20, 3))
    base["grid_step_pct"] = _clampf(base.get("grid_step_pct"), 0.0005, 0.2, 0.004)
    base["order_size_usd"] = _clampf(base.get("order_size_usd"), 1.0, 100000.0, 6.0)
    base["max_inventory_usd"] = _clampf(base.get("max_inventory_usd"), 0.0, 1e9, 15.0)
    base["hard_loss_cap_usd"] = _clampf(base.get("hard_loss_cap_usd"), 0.0, 1e9, 5.0)
    base["min_notional_usd"] = _clampf(base.get("min_notional_usd"), 0.0, 1e6, 5.0)
    base["maker_fee_bps"] = _clampf(base.get("maker_fee_bps"), 0.0, 100.0, 10.0)
    base["allow_sell_existing_inventory"] = bool(base.get("allow_sell_existing_inventory"))
    return base


def save_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k, v in (patch or {}).items():
        if k in cfg and v is not None:
            cfg[k] = v
    ex._write_json(_CFG_PATH, cfg)
    return cfg


def _read_state() -> Dict[str, Any]:
    st = ex._read_json(_STATE_PATH, {})
    return st if isinstance(st, dict) else {}


def _write_state(st: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, st)


def _key(venue: str, asset: str) -> str:
    return f"{venue}:{asset}".upper()


def _new_asset_state() -> Dict[str, Any]:
    return {
        "halted": False, "halt_reason": None,
        "inventory_base": 0.0, "avg_cost_usd": 0.0,
        "realized_pnl_usd": 0.0, "fills": 0,
        "open_orders": [], "last_mid": 0.0, "updated_at": _iso(),
    }


# ----------------------------- pure core -----------------------------

def compute_grid_orders(mid: float, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Grid of buy limits below mid and sell limits above mid."""
    mid = float(mid or 0)
    if mid <= 0:
        return []
    levels = int(cfg.get("grid_levels") or 3)
    step = float(cfg.get("grid_step_pct") or 0.004)
    size_usd = float(cfg.get("order_size_usd") or 5.0)
    orders: List[Dict[str, Any]] = []
    for i in range(1, levels + 1):
        buy_px = round(mid * (1 - i * step), 8)
        sell_px = round(mid * (1 + i * step), 8)
        if buy_px > 0:
            orders.append({"side": "buy", "price": buy_px, "size_base": round(size_usd / buy_px, 8), "level": i})
        if sell_px > 0:
            orders.append({"side": "sell", "price": sell_px, "size_base": round(size_usd / sell_px, 8), "level": i})
    return orders


def apply_fill(state: Dict[str, Any], fill: Dict[str, Any], *, fee_bps: float = 10.0) -> float:
    """Apply a fill to inventory (avg-cost) and realized PnL. Returns realized delta (USD)."""
    side = str(fill.get("side") or "").lower()
    price = float(fill.get("price") or 0)
    size = float(fill.get("size_base") or 0)
    if price <= 0 or size <= 0:
        return 0.0
    fee = price * size * (fee_bps / 10000.0)
    inv = float(state.get("inventory_base") or 0)
    avg = float(state.get("avg_cost_usd") or 0)
    realized_delta = 0.0
    if side == "buy":
        new_inv = inv + size
        # blend fee into cost basis
        state["avg_cost_usd"] = ((inv * avg) + (size * price) + fee) / new_inv if new_inv > 0 else 0.0
        state["inventory_base"] = round(new_inv, 12)
    elif side == "sell":
        if fill.get("is_existing_inv_sell"):
            # Selling the user's PRE-EXISTING coin (not bot-accumulated inventory). Book only the
            # grid edge relative to the reference mid when the order was posted — the coin's
            # principal value is the user's capital, not bot profit. This sale does NOT draw down
            # the avg-cost inventory book (that coin was never in it); the paired buy that follows
            # rebuys the coin one step lower, closing the round.
            ref = float(fill.get("existing_ref_px") or price)
            realized_delta = size * (price - ref) - fee
        else:
            sell_size = min(size, inv)
            realized_delta = sell_size * (price - avg) - fee
            state["inventory_base"] = round(inv - sell_size, 12)
            if state["inventory_base"] <= 1e-12:
                state["avg_cost_usd"] = 0.0
    state["realized_pnl_usd"] = round(float(state.get("realized_pnl_usd") or 0) + realized_delta, 8)
    state["fills"] = int(state.get("fills") or 0) + 1
    return round(realized_delta, 8)


def unrealized_pnl(state: Dict[str, Any], mid: float) -> float:
    inv = float(state.get("inventory_base") or 0)
    avg = float(state.get("avg_cost_usd") or 0)
    return round(inv * (float(mid or 0) - avg), 8)


def total_pnl(state: Dict[str, Any], mid: float) -> float:
    return round(float(state.get("realized_pnl_usd") or 0) + unrealized_pnl(state, mid), 8)


def risk_check(state: Dict[str, Any], cfg: Dict[str, Any], mid: float) -> Dict[str, Any]:
    """Return {halt, reason} enforcing inventory + hard loss caps."""
    inv_usd = float(state.get("inventory_base") or 0) * float(mid or 0)
    max_inv = float(cfg.get("max_inventory_usd") or 0)
    loss_cap = float(cfg.get("hard_loss_cap_usd") or 0)
    tpnl = total_pnl(state, mid)
    if loss_cap > 0 and tpnl <= -loss_cap:
        return {"halt": True, "reason": "hard_loss_cap", "total_pnl_usd": tpnl}
    if max_inv > 0 and inv_usd > max_inv * 1.001:
        return {"halt": True, "reason": "inventory_cap", "inventory_usd": round(inv_usd, 4)}
    return {"halt": False, "reason": None, "total_pnl_usd": tpnl, "inventory_usd": round(inv_usd, 4)}


def select_assets(candidates: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Keep assets whose quoted spread and volatility clear the configured minimums."""
    min_spread = float(cfg.get("min_spread_bps") or 0)
    min_vol = float(cfg.get("min_vol_pct") or 0)
    out: List[Dict[str, Any]] = []
    for c in candidates or []:
        bid = float(c.get("bid") or 0)
        ask = float(c.get("ask") or 0)
        if bid <= 0 or ask <= 0:
            continue
        mid = (bid + ask) / 2.0
        spread_bps = (ask - bid) / mid * 10000.0 if mid > 0 else 0.0
        vol_pct = float(c.get("vol_pct") or 0)
        if spread_bps >= min_spread and vol_pct >= min_vol:
            out.append({**c, "spread_bps": round(spread_bps, 2), "mid": round(mid, 8)})
    out.sort(key=lambda r: (r.get("spread_bps", 0), r.get("vol_pct", 0)), reverse=True)
    return out


# ----------------------------- brokers -----------------------------

def _paper_fills(open_orders: List[Dict[str, Any]], mid: float) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
    """Fill buys at/above their price when mid<=price; sells when mid>=price. Returns (filled, remaining)."""
    filled, remaining = [], []
    for o in open_orders:
        side = str(o.get("side") or "").lower()
        px = float(o.get("price") or 0)
        if side == "buy" and mid <= px:
            filled.append(o)
        elif side == "sell" and mid >= px:
            filled.append(o)
        else:
            remaining.append(o)
    return filled, remaining


def grid_live_enabled() -> bool:
    """Live grid trading requires BOTH owner flags. Standalone (laptop) bot — deliberately
    does NOT depend on the site's MN2 chain spork, which isn't reachable off the server."""
    def _on(k: str) -> bool:
        return str(os.environ.get(k, "")).strip().lower() in ("1", "true", "yes")
    return _on("EXCHANGE_GRID_LIVE") and _on("EXCHANGE_ARBITRAGE_LIVE")


# ----------------------------- orchestrator -----------------------------

def run_grid_tick(venue: str, asset: str, *, mid: Optional[float] = None,
                  dry_run: Optional[bool] = None,
                  simulate_fill_mid: Optional[float] = None,
                  spot_free_base: Optional[float] = None) -> Dict[str, Any]:
    """One grid tick: reconcile fills, enforce risk, refresh grid. Paper unless live gate on.

    ``mid`` overrides the market price (tests). ``simulate_fill_mid`` (paper) drives which open
    orders fill this tick before the grid is refreshed. ``spot_free_base`` overrides the free
    balance of ``asset`` on the venue (tests); when omitted and live, it's read from the venue —
    used by sell-from-existing mode to seed sells against coin you already hold.
    """
    cfg = load_config()
    venue = str(venue or cfg.get("venue") or "binance").lower()
    asset = str(asset).upper()
    live = grid_live_enabled() if dry_run is None else (not dry_run)

    all_state = _read_state()
    key = _key(venue, asset)
    st = all_state.get(key) or _new_asset_state()

    # Resolve current mid price
    if mid is None:
        try:
            from backend.services import external_exchange_connector_service as conn
            tick = conn.fetch_ticker(venue, asset, timeout=5.0)
            if tick:
                bid = float(tick.get("bid") or 0); askp = float(tick.get("ask") or 0)
                mid = (bid + askp) / 2.0 if (bid > 0 and askp > 0) else float(tick.get("last") or 0)
        except Exception:
            mid = 0.0
    mid = float(mid or 0)
    if mid <= 0:
        return {"success": False, "error": "no_price", "venue": venue, "asset": asset}

    # 1) Reconcile fills
    fills_applied: List[Dict[str, Any]] = []
    reconcile_note: Optional[str] = None
    if live:
        # Live reconciliation. An order that has left the venue's open list is NOT assumed filled —
        # it might have been rejected, canceled, or the book read may have failed. We confirm each
        # disappeared order's real status before booking it, so we never invent a phantom fill or
        # phantom inventory. If we can't read the book at all this tick, we leave state untouched.
        from backend.services import exchange_venue_api_service as vapi
        oo = vapi.get_open_orders(venue, asset, dry_run=False)
        if not oo.get("success"):
            # Can't see the order book -> skip reconciliation (do not infer fills this tick).
            reconcile_note = "open_orders_read_failed"
        else:
            rows = oo.get("orders")
            if not isinstance(rows, list):
                rows = oo.get("body") if isinstance(oo.get("body"), list) else []
            live_ids = {str(o.get("orderId") or o.get("id") or o.get("_id"))
                        for o in rows if isinstance(o, dict)}
            remaining: List[Dict[str, Any]] = []
            for o in st.get("open_orders", []):
                oid = str(o.get("order_id"))
                if oid in live_ids:
                    remaining.append(o)
                    continue
                # Disappeared from the book — confirm what actually happened.
                try:
                    stt = vapi.get_order_status(venue, asset, o.get("order_id"), dry_run=False)
                except Exception:
                    stt = {}
                if stt.get("filled"):
                    fills_applied.append(o)
                elif stt.get("resting"):
                    remaining.append(o)  # book listing was stale/partial; keep it
                # else: canceled / rejected / unconfirmable -> drop WITHOUT booking a fill
            st["open_orders"] = remaining
    else:
        fill_mid = float(simulate_fill_mid if simulate_fill_mid is not None else mid)
        filled, remaining = _paper_fills(st.get("open_orders", []), fill_mid)
        fills_applied = filled
        st["open_orders"] = remaining

    fee_bps = float(cfg.get("maker_fee_bps") or 10.0)
    tick_realized = 0.0
    for f in fills_applied:
        rd = apply_fill(st, f, fee_bps=fee_bps)
        tick_realized += rd
        ex._append_jsonl(_LEDGER_PATH, {
            "ts": _iso(), "venue": venue, "asset": asset, "side": f.get("side"),
            "price": f.get("price"), "size_base": f.get("size_base"),
            "realized_delta_usd": rd, "mode": "live" if live else "paper",
        })

    # Track peak realized PnL + max drawdown for the accounting/monitor views.
    _realized_now = float(st.get("realized_pnl_usd") or 0)
    _peak = max(float(st.get("peak_realized_usd") or 0), _realized_now)
    st["peak_realized_usd"] = round(_peak, 8)
    st["max_drawdown_usd"] = round(max(float(st.get("max_drawdown_usd") or 0), _peak - _realized_now), 8)

    # 2) Risk check -> halt + cancel all if breached
    rc = risk_check(st, cfg, mid)
    if rc["halt"]:
        if live and st.get("open_orders"):
            from backend.services import exchange_venue_api_service as vapi
            for o in st["open_orders"]:
                try:
                    vapi.cancel_order(venue, asset, o.get("order_id"), dry_run=False)
                except Exception:
                    pass
        st["open_orders"] = []
        st["halted"] = True
        st["halt_reason"] = rc["reason"]
        st["last_mid"] = mid
        st["updated_at"] = _iso()
        all_state[key] = st
        _write_state(all_state)
        return {"success": True, "venue": venue, "asset": asset, "halted": True,
                "reason": rc["reason"], "tick_realized_usd": round(tick_realized, 6),
                "realized_pnl_usd": st["realized_pnl_usd"], "mode": "live" if live else "paper", **rc}

    # 3) Fixed-level grid with paired replacement (proper grid mechanic):
    #    a filled buy posts a sell one step up (locks the step); a filled sell posts a buy one
    #    step down. Unfilled levels stay put (we do NOT recenter every tick). If the grid is
    #    empty (fresh start), seed levels around the current mid.
    step = float(cfg.get("grid_step_pct") or 0.004)
    size_usd = float(cfg.get("order_size_usd") or 5.0)
    max_inv = float(cfg.get("max_inventory_usd") or 0)
    min_notional = float(cfg.get("min_notional_usd") or 0)
    allow_sell_existing = bool(cfg.get("allow_sell_existing_inventory"))
    # Free base-asset balance you already hold on the venue — seeds sells when the bot has no
    # accumulated inventory yet ("sell-from-existing" mode). Live: read from the venue.
    existing_free = 0.0
    if allow_sell_existing:
        if spot_free_base is not None:
            existing_free = max(0.0, float(spot_free_base or 0))
        elif live:
            try:
                from backend.services import exchange_venue_api_service as vapi
                existing_free = max(0.0, float(vapi.parse_spot_balances(venue, dry_run=False).get(asset) or 0))
            except Exception:
                existing_free = 0.0
    st_open: List[Dict[str, Any]] = list(st.get("open_orders") or [])
    place_errors: List[Dict[str, Any]] = []
    _seq = [0]

    def _place(side: str, price: float, size_base: float, *,
               from_existing: bool = False, ref_px: Optional[float] = None) -> None:
        price = round(float(price), 8)
        size_base = round(float(size_base), 8)
        if price <= 0 or size_base <= 0:
            return
        # Skip dust orders the venue would reject (below min notional).
        if min_notional > 0 and price * size_base < min_notional:
            return
        if side == "buy" and max_inv > 0:
            inv_usd_now = float(st.get("inventory_base") or 0) * mid + sum(
                o["size_base"] * o["price"] for o in st_open if o["side"] == "buy")
            if inv_usd_now + size_base * price > max_inv:
                return
        if live:
            from backend.services import exchange_venue_api_service as vapi
            r = vapi.place_limit_order(venue, asset, side, size_base, price, dry_run=False)
            if not r.get("success"):
                place_errors.append({"side": side, "price": round(float(price), 8),
                                     "error": vapi.extract_order_error(r) or r.get("error") or "place_failed"})
                return
            oid = r.get("order_id")
        else:
            _seq[0] += 1
            oid = f"paper-{venue}-{asset}-{side}-{int(time.time()*1000)}-{_seq[0]}"
        order = {"order_id": oid, "side": side, "price": price,
                 "size_base": size_base, "ts": _iso()}
        if from_existing:
            # Mark so apply_fill books only the grid edge vs the reference mid, not principal.
            order["is_existing_inv_sell"] = True
            order["existing_ref_px"] = round(float(ref_px if ref_px is not None else mid), 8)
        st_open.append(order)

    # Paired replacement for orders that filled this tick.
    for f in fills_applied:
        fpx = float(f.get("price") or 0)
        if fpx <= 0:
            continue
        if str(f.get("side")).lower() == "buy":
            _place("sell", fpx * (1 + step), float(f.get("size_base") or 0))
        else:
            bp = fpx * (1 - step)
            if bp > 0:
                _place("buy", bp, size_usd / bp)

    # Seed a fresh grid if we have no resting orders. Sells need something to sell: either
    # bot-accumulated inventory, or (sell-from-existing) the coin you already hold on the venue.
    if not st_open:
        inv_base = float(st.get("inventory_base") or 0)
        remaining_existing = existing_free
        for od in compute_grid_orders(mid, cfg):
            side = od["side"]
            size_base = float(od.get("size_base") or 0)
            if side == "sell":
                if inv_base > 1e-12:
                    _place("sell", od["price"], size_base)
                elif allow_sell_existing and size_base > 0 and remaining_existing >= size_base:
                    _place("sell", od["price"], size_base, from_existing=True, ref_px=mid)
                    remaining_existing -= size_base
                # else: no inventory and no existing coin to sell -> skip this sell level
            else:
                _place("buy", od["price"], size_base)

    new_open = st_open
    st["open_orders"] = new_open
    st["halted"] = False
    st["halt_reason"] = None
    st["last_mid"] = mid
    st["updated_at"] = _iso()
    all_state[key] = st
    _write_state(all_state)

    inv_usd = float(st.get("inventory_base") or 0) * mid
    return {
        "success": True, "venue": venue, "asset": asset, "halted": False,
        "mid": mid, "fills_this_tick": len(fills_applied),
        "tick_realized_usd": round(tick_realized, 6),
        "realized_pnl_usd": st["realized_pnl_usd"],
        "unrealized_pnl_usd": unrealized_pnl(st, mid),
        "inventory_base": st["inventory_base"], "inventory_usd": round(inv_usd, 4),
        "open_orders": len(new_open), "place_errors": place_errors[:6],
        "reconcile_note": reconcile_note,
        "mode": "live" if live else "paper",
    }


def set_enabled(enabled: bool) -> Dict[str, Any]:
    cfg = save_config({"enabled": bool(enabled)})
    return {"success": True, "enabled": cfg["enabled"]}


def reset_open_orders(venue: Optional[str] = None) -> Dict[str, Any]:
    """Cancel the bot's tracked open orders (live) and clear them from state, so the next tick
    seeds a fresh full grid. Use after funding more capital to (re)place all levels. Inventory
    and realized PnL are preserved."""
    cfg = load_config()
    live = grid_live_enabled()
    all_state = _read_state()
    cleared = 0
    # If a specific venue is passed, only reset that venue's targets; else reset all.
    only_venue = str(venue).lower() if venue else None
    for v, asset in grid_targets(cfg):
        if only_venue and v != only_venue:
            continue
        key = _key(v, str(asset))
        st = all_state.get(key)
        if not st:
            continue
        for o in st.get("open_orders") or []:
            if live:
                try:
                    from backend.services import exchange_venue_api_service as vapi
                    vapi.cancel_order(v, str(asset), o.get("order_id"), dry_run=False)
                except Exception:
                    pass
            cleared += 1
        st["open_orders"] = []
        st["halted"] = False
        st["halt_reason"] = None
        all_state[key] = st
    _write_state(all_state)
    return {"success": True, "venue": only_venue or "all", "cleared_orders": cleared}


def grid_status() -> Dict[str, Any]:
    cfg = load_config()
    st = _read_state()
    assets = {}
    for key, s in st.items():
        assets[key] = {
            "halted": s.get("halted"), "halt_reason": s.get("halt_reason"),
            "inventory_base": s.get("inventory_base"), "avg_cost_usd": s.get("avg_cost_usd"),
            "realized_pnl_usd": s.get("realized_pnl_usd"), "fills": s.get("fills"),
            "peak_realized_usd": s.get("peak_realized_usd"), "max_drawdown_usd": s.get("max_drawdown_usd"),
            "open_orders": len(s.get("open_orders") or []), "last_mid": s.get("last_mid"),
        }
    targets = grid_targets(cfg)
    venues_map: Dict[str, List[str]] = {}
    for v, a in targets:
        venues_map.setdefault(v, []).append(a)
    return {
        "success": True, "enabled": cfg.get("enabled"), "live": grid_live_enabled(),
        "venue": cfg.get("venue"), "assets_configured": cfg.get("assets"),
        "venues": venues_map, "targets_total": len(targets),
        "config": {k: cfg.get(k) for k in ("grid_levels", "grid_step_pct", "order_size_usd",
                                           "max_inventory_usd", "hard_loss_cap_usd",
                                           "min_spread_bps", "min_vol_pct",
                                           "allow_sell_existing_inventory")},
        "state": assets,
    }


def grid_profit() -> Dict[str, Any]:
    st = _read_state()
    realized = round(sum(float(s.get("realized_pnl_usd") or 0) for s in st.values()), 6)
    fills = sum(int(s.get("fills") or 0) for s in st.values())
    return {"success": True, "realized_pnl_usd": realized, "total_fills": fills,
            "assets": {k: round(float(s.get("realized_pnl_usd") or 0), 6) for k, s in st.items()}}


# ----------------------------- profit-driven pair selection -----------------------------

_GRID_VENUES = ("binance", "nonkyc", "xeggex")


def _load_pair_catalog() -> Dict[str, set]:
    """venue -> set of tradeable base symbols. XeggeX mirrors the NonKYC USDT list (same family)."""
    cat = ex._read_json(_PAIR_CATALOG_PATH, {}) or {}
    binance = {str(s).upper() for s in (cat.get("binance_usdc_bases") or [])}
    nonkyc = {str(s).upper() for s in (cat.get("nonkyc_usdt_bases") or [])}
    return {"binance": binance, "nonkyc": nonkyc, "xeggex": set(nonkyc)}


def _load_profit_history() -> Dict[str, Dict[str, Any]]:
    """symbol -> measured edge/hit-rate/fills from the ledger profit index."""
    idx = ex._read_json(_PROFIT_INDEX_PATH, {}) or {}
    hist: Dict[str, Dict[str, Any]] = {}
    for h in (idx.get("hits") or []):
        if not isinstance(h, dict):
            continue
        sym = str(h.get("symbol") or "").upper()
        if not sym:
            continue
        cur = hist.setdefault(sym, {"avg_net_bps": 0.0, "hit_rate_pct": 0.0, "fill_count": 0, "venues": set()})
        cur["avg_net_bps"] = max(cur["avg_net_bps"], float(h.get("avg_net_bps") or 0))
        cur["hit_rate_pct"] = max(cur["hit_rate_pct"], float(h.get("hit_rate_pct") or 0))
        cur["fill_count"] += int(h.get("fill_count") or 0)
        for v in (h.get("buy_venue"), h.get("sell_venue")):
            if v:
                cur["venues"].add(str(v).lower())
    return hist


def _common_cross_symbols(venues: List[str], catalog: Optional[Dict[str, set]] = None) -> List[str]:
    """Base symbols listed on >=2 of the target venues (a real cross-trade needs two venues)."""
    catalog = catalog or _load_pair_catalog()
    counts: Dict[str, int] = {}
    for v in venues:
        for s in catalog.get(v, set()):
            counts[s] = counts.get(s, 0) + 1
    return sorted([s for s, c in counts.items() if c >= 2])


def scan_cross_venue_differences(*, venues: Optional[List[str]] = None,
                                 symbols: Optional[List[str]] = None,
                                 min_net_bps: float = 0.0,
                                 notional_usd: float = 100.0) -> Dict[str, Any]:
    """Search the price difference of each pair across the venues (cross-trade / spatial arb).

    For every symbol listed on 2+ of the target venues, find the cheapest ask and the richest
    bid across them; the gap (net of both venues' taker fees) is the cross-venue difference.
    This is the 'difference in trading pair prices' created by trading across the three exchanges.
    Returns them ranked; only real venue↔venue routes (no internal) are included.
    """
    venues = [str(v).lower() for v in (venues or list(_GRID_VENUES))]
    catalog = _load_pair_catalog()
    if symbols is None:
        symbols = _common_cross_symbols(venues, catalog)
    diffs: List[Dict[str, Any]] = []
    try:
        from backend.services.exchange_arbitrage_service import scan_opportunities
        scan = scan_opportunities(symbols=symbols, venues=venues, notional_usd=notional_usd)
        for o in (scan.get("opportunities") or []):
            if not isinstance(o, dict):
                continue
            bv = str(o.get("buy_venue") or "").lower()
            sv = str(o.get("sell_venue") or "").lower()
            if bv not in venues or sv not in venues or bv == sv:
                continue  # only real cross-venue routes between the target exchanges
            nb = float(o.get("net_bps") or 0)
            if nb < min_net_bps:
                continue
            sym = str(o.get("symbol") or "").upper()
            diffs.append({
                "symbol": sym, "buy_venue": bv, "sell_venue": sv,
                "gross_bps": o.get("gross_bps"), "fee_bps": o.get("fee_bps"),
                "net_bps": round(nb, 2), "buy_ask": o.get("buy_ask"), "sell_bid": o.get("sell_bid"),
                "est_profit_usd": o.get("est_profit_usd"),
                "route": f"{bv}\u2192{sv}",
                "venues": [v for v in _GRID_VENUES if sym in catalog.get(v, set())],
            })
    except Exception as exc:
        return {"success": False, "error": str(exc), "venues": venues, "differences": []}
    diffs.sort(key=lambda d: d["net_bps"], reverse=True)
    return {"success": True, "venues": venues, "scanned_symbols": len(symbols),
            "min_net_bps": min_net_bps, "count": len(diffs), "differences": diffs}


def _live_arb_edges() -> Dict[str, float]:
    """symbol -> best current cross-venue net edge (bps) among the grid venues. Empty if unreachable."""
    edges: Dict[str, float] = {}
    res = scan_cross_venue_differences(min_net_bps=-1e9)
    for d in (res.get("differences") or []):
        s = str(d.get("symbol") or "").upper()
        if s:
            edges[s] = max(edges.get(s, 0.0), float(d.get("net_bps") or 0))
    return edges


def autoselect_cross_venue_pairs(*, min_net_bps: float = 5.0, notional_usd: float = 100.0,
                                 apply: bool = False) -> Dict[str, Any]:
    """Search cross-venue price differences and add the profitable pairs to the multi-venue config
    (added on each venue where they're listed, so the grid posts spot orders there)."""
    cfg = load_config()
    scan = scan_cross_venue_differences(min_net_bps=min_net_bps, notional_usd=notional_usd)
    diffs = scan.get("differences") or []
    add: Dict[str, List[str]] = {}
    for d in diffs:
        for v in d.get("venues") or []:
            add.setdefault(v, []).append(d["symbol"])
    for v in add:
        add[v] = sorted(set(add[v]))
    result: Dict[str, Any] = {"success": scan.get("success", True), "differences": diffs,
                              "venues_add": add, "applied": False, "min_net_bps": min_net_bps,
                              "error": scan.get("error")}
    if apply and add:
        venues = {k: list(v) for k, v in (cfg.get("venues") or {}).items()}
        legacy_assets = {str(a).upper() for a in (cfg.get("assets") or [])}
        for v, syms in add.items():
            existing = {str(x).upper() for x in (venues.get(v) or [])}
            if v == "binance":
                existing |= legacy_assets
            venues[v] = sorted(existing | set(syms))
        cfg["venues"] = venues
        ex._write_json(_CFG_PATH, cfg)
        result["applied"] = True
        result["config_venues"] = venues
        result["targets_total"] = len(grid_targets(cfg))
    return result


def rank_profit_pairs(*, include_live: bool = True, min_score: float = 3.0,
                      cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Rank candidate pairs by *measured* profitability so we add the ones that actually make money.

    Score blends the ledger's historical net edge (avg_net_bps) with the current live arb edge,
    discounted by hit-rate and sample-size confidence, and keeps only symbols the venue catalog
    lists. Deterministic and offline-safe (live edges are additive, not required).
    """
    cfg = cfg or load_config()
    catalog = _load_pair_catalog()
    hist = _load_profit_history()
    live = _live_arb_edges() if include_live else {}
    fee_bps = float(cfg.get("maker_fee_bps") or 10.0)

    ranked: List[Dict[str, Any]] = []
    for sym in (set(hist) | set(live)):
        h = hist.get(sym, {})
        hist_edge = float(h.get("avg_net_bps") or 0)
        live_edge = float(live.get(sym, 0.0))
        edge = max(hist_edge, live_edge)
        # net of a round-trip of fees so the "profit difference" is honest
        net_edge = edge - 2 * fee_bps
        hit = float(h.get("hit_rate_pct") or (100.0 if sym in live else 0.0)) / 100.0
        fills = int(h.get("fill_count") or 0)
        conf = min(1.0, (fills + (5 if sym in live else 0)) / 10.0)
        score = max(0.0, net_edge) * (0.5 + 0.5 * hit) * (0.3 + 0.7 * conf)
        venues = [v for v in _GRID_VENUES if sym in catalog.get(v, set())]
        if not venues or score < min_score:
            continue
        ranked.append({
            "symbol": sym, "edge_bps": round(edge, 2), "net_edge_bps": round(net_edge, 2),
            "hit_rate_pct": round(hit * 100, 1), "fill_count": fills,
            "confidence": round(conf, 2), "score": round(score, 2),
            "venues": venues, "source": "live+ledger" if (sym in live and sym in hist)
                        else ("live" if sym in live else "ledger"),
        })
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked


def autoselect_profit_pairs(*, min_score: float = 3.0, top_n: Optional[int] = None,
                            include_live: bool = True, apply: bool = False) -> Dict[str, Any]:
    """Rank pairs by measured profit and (optionally) add them to the multi-venue config."""
    cfg = load_config()
    ranked = rank_profit_pairs(include_live=include_live, min_score=min_score, cfg=cfg)
    if top_n:
        ranked = ranked[: int(top_n)]
    add: Dict[str, List[str]] = {}
    for r in ranked:
        for v in r["venues"]:
            add.setdefault(v, []).append(r["symbol"])
    result: Dict[str, Any] = {"success": True, "selected": ranked, "venues_add": add,
                              "applied": False, "min_score": min_score}
    if apply and add:
        venues = {k: list(v) for k, v in (cfg.get("venues") or {}).items()}
        legacy_assets = {str(a).upper() for a in (cfg.get("assets") or [])}
        for v, syms in add.items():
            existing = {str(x).upper() for x in (venues.get(v) or [])}
            if v == "binance":
                existing |= legacy_assets
            venues[v] = sorted(existing | set(syms))
        cfg["venues"] = venues
        ex._write_json(_CFG_PATH, cfg)
        result["applied"] = True
        result["config_venues"] = venues
        result["targets_total"] = len(grid_targets(cfg))
    return result


def grid_targets(cfg: Optional[Dict[str, Any]] = None) -> List[tuple]:
    """Resolve the full (venue, asset) set to trade, merging the legacy single-venue
    ``venue``+``assets`` with the optional multi-venue ``venues`` map. De-duplicated."""
    cfg = cfg or load_config()
    targets: List[tuple] = []
    seen = set()

    def _add(venue: Any, asset: Any) -> None:
        v = str(venue or "binance").lower()
        a = str(asset).upper().strip()
        if a and (v, a) not in seen:
            seen.add((v, a))
            targets.append((v, a))

    legacy_venue = str(cfg.get("venue") or "binance").lower()
    for a in (cfg.get("assets") or []):
        _add(legacy_venue, a)
    venues = cfg.get("venues")
    if isinstance(venues, dict):
        for v, alist in venues.items():
            if isinstance(alist, list):
                for a in alist:
                    _add(v, a)
    return targets


def run_all(*, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Daemon entry: tick every configured (venue, asset) when enabled."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "disabled"}
    results = []
    for venue, asset in grid_targets(cfg):
        try:
            results.append(run_grid_tick(venue, asset, dry_run=dry_run))
        except Exception as exc:
            results.append({"success": False, "venue": venue, "asset": asset, "error": str(exc)})
    return {"success": True, "ticks": results,
            "realized_pnl_usd": grid_profit()["realized_pnl_usd"]}
