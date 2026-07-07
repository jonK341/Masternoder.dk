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
                  simulate_fill_mid: Optional[float] = None) -> Dict[str, Any]:
    """One grid tick: reconcile fills, enforce risk, refresh grid. Paper unless live gate on.

    ``mid`` overrides the market price (tests). ``simulate_fill_mid`` (paper) drives which open
    orders fill this tick before the grid is refreshed.
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
    if live:
        # Live: an order missing from the venue's open list since last tick is treated as filled.
        from backend.services import exchange_venue_api_service as vapi
        oo = vapi.get_open_orders(venue, asset, dry_run=False)
        live_ids = {str(o.get("orderId") or o.get("id") or o.get("_id")) for o in (oo.get("orders") or oo.get("body") or []) if isinstance(o, dict)}
        remaining = []
        for o in st.get("open_orders", []):
            if str(o.get("order_id")) not in live_ids:
                fills_applied.append(o)
            else:
                remaining.append(o)
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
    st_open: List[Dict[str, Any]] = list(st.get("open_orders") or [])
    place_errors: List[Dict[str, Any]] = []
    _seq = [0]

    def _place(side: str, price: float, size_base: float) -> None:
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
        st_open.append({"order_id": oid, "side": side, "price": price,
                        "size_base": size_base, "ts": _iso()})

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

    # Seed a fresh grid if we have no resting orders.
    if not st_open:
        for od in compute_grid_orders(mid, cfg):
            if od["side"] == "sell" and float(st.get("inventory_base") or 0) <= 0:
                continue
            _place(od["side"], od["price"], od["size_base"])

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
    venue = str(venue or cfg.get("venue") or "binance").lower()
    live = grid_live_enabled()
    all_state = _read_state()
    cleared = 0
    for asset in (cfg.get("assets") or []):
        key = _key(venue, str(asset))
        st = all_state.get(key)
        if not st:
            continue
        for o in st.get("open_orders") or []:
            if live:
                try:
                    from backend.services import exchange_venue_api_service as vapi
                    vapi.cancel_order(venue, str(asset), o.get("order_id"), dry_run=False)
                except Exception:
                    pass
            cleared += 1
        st["open_orders"] = []
        st["halted"] = False
        st["halt_reason"] = None
        all_state[key] = st
    _write_state(all_state)
    return {"success": True, "venue": venue, "cleared_orders": cleared}


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
    return {
        "success": True, "enabled": cfg.get("enabled"), "live": grid_live_enabled(),
        "venue": cfg.get("venue"), "assets_configured": cfg.get("assets"),
        "config": {k: cfg.get(k) for k in ("grid_levels", "grid_step_pct", "order_size_usd",
                                           "max_inventory_usd", "hard_loss_cap_usd",
                                           "min_spread_bps", "min_vol_pct")},
        "state": assets,
    }


def grid_profit() -> Dict[str, Any]:
    st = _read_state()
    realized = round(sum(float(s.get("realized_pnl_usd") or 0) for s in st.values()), 6)
    fills = sum(int(s.get("fills") or 0) for s in st.values())
    return {"success": True, "realized_pnl_usd": realized, "total_fills": fills,
            "assets": {k: round(float(s.get("realized_pnl_usd") or 0), 6) for k, s in st.items()}}


def run_all(*, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Daemon entry: tick every configured asset when enabled."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "disabled"}
    venue = str(cfg.get("venue") or "binance").lower()
    results = []
    for asset in (cfg.get("assets") or []):
        try:
            results.append(run_grid_tick(venue, str(asset), dry_run=dry_run))
        except Exception as exc:
            results.append({"success": False, "asset": asset, "error": str(exc)})
    return {"success": True, "ticks": results,
            "realized_pnl_usd": grid_profit()["realized_pnl_usd"]}
