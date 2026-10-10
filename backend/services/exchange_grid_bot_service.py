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
from datetime import datetime, timedelta, timezone
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
        # --- fee-positive market-making guards ---
        # Every completed round trip earns the grid STEP and pays a round trip of maker fees.
        # Keep the step above fees so each pair is guaranteed net-positive.
        "min_edge_over_fee_bps": 2.0,        # required margin of step over round-trip fees
        "enforce_fee_positive_step": True,   # auto-bump step so step_bps >= 2*maker + margin
        "require_spread_over_fee": True,     # only seed a fresh grid when the venue's live
                                             # spread clears a round trip of fees (worth MM'ing)
        # Per-venue overrides (illiquid venues want WIDE steps to capture their fat spread;
        # liquid venues want DENSE steps for frequent small captures).
        "venue_overrides": {},
        # Per-exchange circuit breaker: auto-pause a venue whose realized PnL stays negative
        # over the window; auto-resume after the cooldown.
        "circuit_breaker": {
            "enabled": True,
            "window_hours": 6.0,
            "loss_threshold_usd": 3.0,   # pause when realized over window <= -this
            "cooldown_hours": 12.0,      # auto-resume this long after pausing
        },
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
    base["min_edge_over_fee_bps"] = _clampf(base.get("min_edge_over_fee_bps"), 0.0, 1000.0, 2.0)
    base["enforce_fee_positive_step"] = bool(base.get("enforce_fee_positive_step"))
    base["require_spread_over_fee"] = bool(base.get("require_spread_over_fee"))
    if not isinstance(base.get("venue_overrides"), dict):
        base["venue_overrides"] = {}
    # Normalize the circuit-breaker block (deep-merge with defaults + clamp).
    cb = base.get("circuit_breaker") if isinstance(base.get("circuit_breaker"), dict) else {}
    dcb = {"enabled": True, "window_hours": 6.0, "loss_threshold_usd": 3.0, "cooldown_hours": 12.0}
    dcb.update({k: v for k, v in cb.items() if v is not None})
    dcb["enabled"] = bool(dcb["enabled"])
    dcb["window_hours"] = _clampf(dcb.get("window_hours"), 0.1, 720.0, 6.0)
    dcb["loss_threshold_usd"] = _clampf(dcb.get("loss_threshold_usd"), 0.0, 1e6, 3.0)
    # Cooldown must be >= window so a resumed venue's old losses fall outside the loss window.
    dcb["cooldown_hours"] = _clampf(dcb.get("cooldown_hours"), dcb["window_hours"], 720.0, 12.0)
    base["circuit_breaker"] = dcb
    return base


# Per-venue fields that may be overridden (illiquid vs liquid venues want different grids).
_OVERRIDABLE = ("grid_step_pct", "order_size_usd", "grid_levels", "max_inventory_usd",
                "hard_loss_cap_usd", "min_notional_usd", "maker_fee_bps", "taker_fee_bps",
                "min_spread_bps", "min_edge_over_fee_bps")
_OVERRIDABLE_FLAGS = ("require_spread_over_fee", "enforce_fee_positive_step")

# Exchange specialization profiles — each exchange runs as its own tuned market-maker.
_VENUE_PROFILES: Dict[str, Dict[str, Any]] = {
    # Tight-spread, deep-liquidity venues (e.g. Binance): dense grid, profit from oscillation
    # across many small fee-positive steps; no spread gate (the book is always tight).
    "liquid_dense": {
        "grid_step_pct": 0.003, "grid_levels": 6, "order_size_usd": 6.0,
        "max_inventory_usd": 60.0, "hard_loss_cap_usd": 8.0, "min_notional_usd": 5.0,
        "min_spread_bps": 1.0, "require_spread_over_fee": False, "enforce_fee_positive_step": True,
    },
    # Wide-spread, thin venues (e.g. NonKYC): patient passive maker — post only when the live
    # spread is genuinely fat, wide steps, small size, tight inventory.
    "illiquid_wide": {
        "grid_step_pct": 0.010, "grid_levels": 3, "order_size_usd": 6.0,
        "max_inventory_usd": 30.0, "hard_loss_cap_usd": 5.0, "min_notional_usd": 5.0,
        "min_spread_bps": 40.0, "require_spread_over_fee": True, "enforce_fee_positive_step": True,
    },
    # Very thin / unproven book (e.g. XeggeX): most conservative — widest steps, fewest levels,
    # smallest size, demands the widest spread before it posts anything.
    "thin_conservative": {
        "grid_step_pct": 0.012, "grid_levels": 2, "order_size_usd": 5.0,
        "max_inventory_usd": 15.0, "hard_loss_cap_usd": 3.0, "min_notional_usd": 5.0,
        "min_spread_bps": 60.0, "require_spread_over_fee": True, "enforce_fee_positive_step": True,
    },
}
_DEFAULT_VENUE_PROFILE = {"binance": "liquid_dense", "nonkyc": "illiquid_wide",
                          "xeggex": "thin_conservative"}


def list_venue_profiles() -> Dict[str, Any]:
    return {"success": True, "profiles": _VENUE_PROFILES,
            "recommended": _DEFAULT_VENUE_PROFILE}


def apply_venue_profile(venue: str, profile: str) -> Dict[str, Any]:
    """Specialize one exchange by applying a named profile to its per-venue overrides."""
    venue = str(venue or "").lower()
    profile = str(profile or "")
    if profile not in _VENUE_PROFILES:
        return {"success": False, "error": "unknown_profile", "profiles": list(_VENUE_PROFILES)}
    cfg = load_config()
    overrides = dict(cfg.get("venue_overrides") or {})
    block = dict(_VENUE_PROFILES[profile])
    block["_profile"] = profile
    overrides[venue] = block
    cfg["venue_overrides"] = overrides
    ex._write_json(_CFG_PATH, cfg)
    return {"success": True, "venue": venue, "profile": profile,
            "effective": {k: effective_config(venue, cfg).get(k)
                          for k in ("grid_step_pct", "grid_levels", "order_size_usd",
                                    "max_inventory_usd", "hard_loss_cap_usd", "min_spread_bps",
                                    "require_spread_over_fee")}}


def effective_config(venue: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Base config merged with any per-venue override, then re-clamped, with the step bumped so
    each completed round trip clears a round trip of maker fees (fee-positive market-making)."""
    base = dict(cfg or load_config())
    venue = str(venue or "").lower()
    ov = (base.get("venue_overrides") or {}).get(venue) or {}
    if isinstance(ov, dict):
        for k in _OVERRIDABLE:
            if ov.get(k) is not None:
                base[k] = ov[k]
        for k in _OVERRIDABLE_FLAGS:
            if ov.get(k) is not None:
                base[k] = bool(ov[k])
        if ov.get("_profile"):
            base["_profile"] = ov["_profile"]
    # Re-clamp the (possibly overridden) numeric fields.
    base["grid_levels"] = int(_clampf(base.get("grid_levels"), 1, 20, 3))
    base["grid_step_pct"] = _clampf(base.get("grid_step_pct"), 0.0005, 0.2, 0.004)
    base["order_size_usd"] = _clampf(base.get("order_size_usd"), 1.0, 100000.0, 6.0)
    base["max_inventory_usd"] = _clampf(base.get("max_inventory_usd"), 0.0, 1e9, 15.0)
    base["hard_loss_cap_usd"] = _clampf(base.get("hard_loss_cap_usd"), 0.0, 1e9, 5.0)
    base["min_notional_usd"] = _clampf(base.get("min_notional_usd"), 0.0, 1e6, 5.0)
    base["maker_fee_bps"] = _clampf(base.get("maker_fee_bps"), 0.0, 100.0, 10.0)
    base["min_spread_bps"] = _clampf(base.get("min_spread_bps"), 0.0, 1e5, 8.0)
    # Fee-positive step: step_bps must exceed a round trip of maker fees plus the margin.
    if base.get("enforce_fee_positive_step"):
        maker = float(base.get("maker_fee_bps") or 0)
        margin = float(base.get("min_edge_over_fee_bps") or 0)
        min_step = (2.0 * maker + margin) / 10000.0
        if float(base.get("grid_step_pct") or 0) < min_step:
            base["grid_step_pct"] = round(min_step, 8)
            base["step_bumped_for_fees"] = True
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
                  spot_free_base: Optional[float] = None,
                  spread_bps: Optional[float] = None) -> Dict[str, Any]:
    """One grid tick: reconcile fills, enforce risk, refresh grid. Paper unless live gate on.

    ``mid`` overrides the market price (tests). ``simulate_fill_mid`` (paper) drives which open
    orders fill this tick before the grid is refreshed. ``spot_free_base`` overrides the free
    balance of ``asset`` on the venue (tests). ``spread_bps`` overrides the measured venue spread
    (tests) for the fee-positive spread gate. Config is resolved per-venue via effective_config.
    """
    base_cfg = load_config()
    venue = str(venue or base_cfg.get("venue") or "binance").lower()
    cfg = effective_config(venue, base_cfg)
    asset = str(asset).upper()
    live = grid_live_enabled() if dry_run is None else (not dry_run)

    all_state = _read_state()
    key = _key(venue, asset)
    st = all_state.get(key) or _new_asset_state()

    # Resolve current mid price (and the live spread, for the fee-positive gate)
    if mid is None:
        try:
            from backend.services import external_exchange_connector_service as conn
            tick = conn.fetch_ticker(venue, asset, timeout=5.0)
            if tick:
                bid = float(tick.get("bid") or 0); askp = float(tick.get("ask") or 0)
                if bid > 0 and askp > 0:
                    mid = (bid + askp) / 2.0
                    if spread_bps is None and mid > 0:
                        spread_bps = (askp - bid) / mid * 10000.0
                else:
                    mid = float(tick.get("last") or 0)
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
            _why = vapi.extract_order_error(oo) or (str(oo.get("status_code")) if oo.get("status_code") else "") or "unknown"
            reconcile_note = "open_orders_read_failed:" + str(_why)[:40]
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
    # One live balance read serves both: the free BASE (seeds sells in sell-from-existing) and
    # the free QUOTE (gates buys so we never spam the venue with orders it will reject).
    _spot_bals = None
    if live:
        try:
            from backend.services import exchange_venue_api_service as vapi
            _spot_bals = vapi.parse_spot_balances(venue, dry_run=False)
        except Exception:
            _spot_bals = None
    existing_free = 0.0
    if allow_sell_existing:
        if spot_free_base is not None:
            existing_free = max(0.0, float(spot_free_base or 0))
        elif _spot_bals:
            existing_free = max(0.0, float(_spot_bals.get(asset) or 0))
    # Known free quote (buy budget). None => unknown (read failed / paper) => don't gate buys.
    quote_free: Optional[float] = None
    if _spot_bals:
        try:
            from backend.services import exchange_venue_api_service as vapi
            quote_asset = str(vapi.venue_quote_asset(venue)).upper()
        except Exception:
            quote_asset = ""
        if quote_asset:
            quote_free = float(_spot_bals.get(quote_asset) or 0)
    st_open: List[Dict[str, Any]] = list(st.get("open_orders") or [])
    place_errors: List[Dict[str, Any]] = []
    _seq = [0]
    _quote_left = [quote_free]  # remaining buy budget (None => unknown, don't gate)
    _buys_skipped = [0]

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
        # Quote-balance gate: don't even send a buy the venue can't fund (avoids reject spam on
        # a live account). Only when we actually read the quote balance.
        if side == "buy" and _quote_left[0] is not None:
            if _quote_left[0] < price * size_base:
                _buys_skipped[0] += 1
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
        if side == "buy" and _quote_left[0] is not None:
            _quote_left[0] -= price * size_base
        st_open.append(order)

    # SAFETY: if we could not read this venue's order book (e.g. 401 on the order endpoint),
    # do NOT place any new orders here. Placing orders we can't reconcile would let sells fill
    # untracked and never get rebought — a one-way liquidation of your holdings. Trade only where
    # we can see the book.
    skip_placement = live and bool(reconcile_note) and str(reconcile_note).startswith("open_orders_read_failed")

    # Paired replacement for orders that filled this tick.
    if not skip_placement:
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

    # Fee-positive spread gate: only seed a fresh grid when the venue's live spread clears a
    # round trip of maker fees — i.e. the venue is actually worth market-making right now.
    # (Paired replacement of already-established levels is unaffected.) Unknown spread = pass.
    maker_bps = float(cfg.get("maker_fee_bps") or 0)
    # Threshold = a round trip of fees, but at least the venue's specialized min_spread_bps.
    gate_threshold = max(2.0 * maker_bps, float(cfg.get("min_spread_bps") or 0))
    spread_gate_ok = True
    if cfg.get("require_spread_over_fee") and spread_bps is not None:
        spread_gate_ok = float(spread_bps) >= gate_threshold
    if not spread_gate_ok:
        reconcile_note = reconcile_note or "spread_below_fee"

    # Seed a fresh grid if we have no resting orders. Sells need something to sell: either
    # bot-accumulated inventory, or (sell-from-existing) the coin you already hold on the venue.
    if not st_open and spread_gate_ok and not skip_placement:
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
        "buys_skipped_no_quote": _buys_skipped[0],
        "reconcile_note": reconcile_note,
        "spread_bps": round(float(spread_bps), 2) if spread_bps is not None else None,
        "grid_step_pct": cfg.get("grid_step_pct"),
        "spread_gate_ok": spread_gate_ok,
        "profile": cfg.get("_profile"),
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
    for key, s in _asset_states(st).items():
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
                                           "allow_sell_existing_inventory",
                                           "enforce_fee_positive_step", "require_spread_over_fee",
                                           "min_edge_over_fee_bps", "venue_overrides")},
        "effective_by_venue": {
            v: {"profile": effective_config(v, cfg).get("_profile"),
                "grid_step_pct": effective_config(v, cfg).get("grid_step_pct"),
                "grid_levels": effective_config(v, cfg).get("grid_levels"),
                "order_size_usd": effective_config(v, cfg).get("order_size_usd"),
                "max_inventory_usd": effective_config(v, cfg).get("max_inventory_usd"),
                "maker_fee_bps": effective_config(v, cfg).get("maker_fee_bps"),
                "min_spread_bps": effective_config(v, cfg).get("min_spread_bps"),
                "require_spread_over_fee": effective_config(v, cfg).get("require_spread_over_fee")}
            for v in venues_map
        },
        "venue_profiles_available": list(_VENUE_PROFILES),
        "paused_venues": paused_venues(),
        "circuit_breaker": cfg.get("circuit_breaker"),
        "state": assets,
    }


def _read_ledger_tail(max_lines: int = 20000) -> List[Dict[str, Any]]:
    """Parse the grid fill ledger (jsonl), newest window. Tolerant of bad lines."""
    import json as _json
    rows: List[Dict[str, Any]] = []
    try:
        if not os.path.isfile(_LEDGER_PATH):
            return rows
        with open(_LEDGER_PATH, encoding="utf-8") as fh:
            lines = fh.readlines()[-int(max_lines):]
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(_json.loads(ln))
            except Exception:
                pass
    except Exception:
        pass
    return rows


def _parse_ts(ts: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def venue_performance(window_hours: float = 24.0) -> Dict[str, Any]:
    """Which venue is actually paying? Aggregate real fills + realized PnL per venue over a
    trailing window (from the fill ledger) so you can shift size toward the winners.

    Returns per-venue fills, fills/day, realized $, realized/day, realized/fill, plus a ranked
    focus suggestion (best realized/day, then realized/fill)."""
    window_hours = max(0.1, float(window_hours or 24.0))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    scale = 24.0 / window_hours
    agg: Dict[str, Dict[str, Any]] = {}
    for r in _read_ledger_tail():
        ts = _parse_ts(r.get("ts"))
        if ts is None or ts < cutoff:
            continue
        v = str(r.get("venue") or "?").lower()
        a = str(r.get("asset") or "?").upper()
        rd = float(r.get("realized_delta_usd") or 0)
        side = str(r.get("side") or "").lower()
        row = agg.setdefault(v, {"venue": v, "fills": 0, "buys": 0, "sells": 0,
                                 "realized_usd": 0.0, "by_asset": {}, "last_fill_ts": None})
        row["fills"] += 1
        row["buys"] += 1 if side == "buy" else 0
        row["sells"] += 1 if side == "sell" else 0
        row["realized_usd"] += rd
        ass = row["by_asset"].setdefault(a, {"fills": 0, "realized_usd": 0.0})
        ass["fills"] += 1
        ass["realized_usd"] += rd
        if row["last_fill_ts"] is None or str(r.get("ts")) > row["last_fill_ts"]:
            row["last_fill_ts"] = str(r.get("ts"))
    venues: List[Dict[str, Any]] = []
    for v, row in agg.items():
        fills = int(row["fills"])
        realized = round(float(row["realized_usd"]), 6)
        row["realized_usd"] = realized
        row["fills_per_day"] = round(fills * scale, 2)
        row["realized_per_day_usd"] = round(realized * scale, 4)
        row["realized_per_fill_usd"] = round(realized / fills, 6) if fills else 0.0
        for a, ass in row["by_asset"].items():
            ass["realized_usd"] = round(float(ass["realized_usd"]), 6)
        venues.append(row)
    venues.sort(key=lambda r: (r["realized_per_day_usd"], r["realized_per_fill_usd"]), reverse=True)
    focus = venues[0]["venue"] if venues else None
    return {
        "success": True, "window_hours": window_hours,
        "venues": venues,
        "focus_suggestion": focus,
        "note": ("Shift size toward '%s' — best realized/day in the window." % focus) if focus
                else "No fills recorded in this window yet.",
    }


def paused_venues() -> Dict[str, Any]:
    st = _read_state()
    pv = st.get("paused_venues")
    return pv if isinstance(pv, dict) else {}


def pause_venue(venue: str, *, reason: str = "manual", manual: bool = True,
                realized_usd: Optional[float] = None) -> Dict[str, Any]:
    """Pause one exchange — its (venue, asset) targets are skipped until resumed."""
    venue = str(venue or "").lower()
    st = _read_state()
    pv = st.get("paused_venues") if isinstance(st.get("paused_venues"), dict) else {}
    pv[venue] = {"reason": reason, "manual": bool(manual), "paused_at": _iso(),
                 "realized_usd": realized_usd}
    st["paused_venues"] = pv
    _write_state(st)
    return {"success": True, "venue": venue, "paused": True, "reason": reason}


def resume_venue(venue: str) -> Dict[str, Any]:
    """Resume a paused exchange."""
    venue = str(venue or "").lower()
    st = _read_state()
    pv = st.get("paused_venues") if isinstance(st.get("paused_venues"), dict) else {}
    existed = pv.pop(venue, None) is not None
    st["paused_venues"] = pv
    _write_state(st)
    return {"success": True, "venue": venue, "resumed": existed}


def check_circuit_breakers() -> Dict[str, Any]:
    """Auto-pause venues whose realized PnL over the window stays at/below the loss threshold;
    auto-resume (non-manual) pauses after the cooldown. Manual pauses persist until resumed."""
    cfg = load_config()
    cb = cfg.get("circuit_breaker") or {}
    events: List[Dict[str, Any]] = []
    st = _read_state()
    pv = st.get("paused_venues") if isinstance(st.get("paused_venues"), dict) else {}
    if not cb.get("enabled", True):
        return {"success": True, "enabled": False, "paused": pv, "events": events}

    window = float(cb.get("window_hours") or 6.0)
    loss_thr = float(cb.get("loss_threshold_usd") or 0.0)
    cooldown = float(cb.get("cooldown_hours") or 12.0)
    now = datetime.now(timezone.utc)

    # Auto-resume expired (non-manual) pauses.
    for v, info in list(pv.items()):
        if info.get("manual"):
            continue
        pat = _parse_ts(info.get("paused_at"))
        if pat is not None and (now - pat) >= timedelta(hours=cooldown):
            pv.pop(v, None)
            events.append({"venue": v, "action": "auto_resume"})

    # Pause fresh losers (only venues actually configured to trade).
    if loss_thr > 0:
        target_venues = {v for v, _ in grid_targets(cfg)}
        realized_by = {row["venue"]: float(row.get("realized_usd") or 0)
                       for row in venue_performance(window_hours=window).get("venues", [])}
        for v in target_venues:
            if v in pv:
                continue
            realized = realized_by.get(v, 0.0)
            if realized <= -loss_thr:
                pv[v] = {"reason": "realized_loss", "manual": False, "paused_at": _iso(),
                         "realized_usd": round(realized, 6), "window_hours": window}
                events.append({"venue": v, "action": "pause", "realized_usd": round(realized, 6)})

    if events:
        log = st.get("cb_event_log")
        if not isinstance(log, list):
            log = []
        for e in events:
            log.append({"ts": _iso(), **e})
        st["cb_event_log"] = log[-200:]
    st["paused_venues"] = pv
    _write_state(st)
    return {"success": True, "enabled": True, "paused": pv, "events": events,
            "window_hours": window, "loss_threshold_usd": loss_thr, "cooldown_hours": cooldown}


def go_live_preflight(*, venues: Optional[List[str]] = None,
                      include_cross_trade: bool = True) -> Dict[str, Any]:
    """The 'last check before flipping live' — verifies gates, per-venue reachability, funded
    legs, and fee-positive config, and returns a checklist + blockers so you know exactly what's
    missing. Read-only (uses real balance reads); places no orders."""
    from backend.services import exchange_venue_api_service as vapi
    cfg = load_config()
    venue_assets: Dict[str, List[str]] = {}
    for v, a in grid_targets(cfg):
        venue_assets.setdefault(v, []).append(a)
    if venues:
        venue_assets = {v: venue_assets.get(v, []) for v in [x.lower() for x in venues]}

    checks: List[Dict[str, Any]] = []
    blockers: List[str] = []

    def add(name: str, ok: bool, detail: str, severity: str = "fail") -> None:
        checks.append({"name": name, "status": "pass" if ok else severity, "detail": detail})
        if not ok and severity == "fail":
            blockers.append(name)

    # --- gates (informational; these are the switches you flip to go live) ---
    grid_live = grid_live_enabled()
    checks.append({"name": "grid live gate", "status": "pass" if grid_live else "info",
                   "detail": "ON" if grid_live else
                   "OFF — set EXCHANGE_GRID_LIVE=1 (+ EXCHANGE_ARBITRAGE_LIVE=1) to trade real"})
    if include_cross_trade:
        try:
            from backend.services import exchange_cross_trade_service as ct
            ctl = ct.cross_trade_live_enabled()
            checks.append({"name": "cross-trade live gate", "status": "pass" if ctl else "info",
                           "detail": "ON" if ctl else
                           "OFF — set EXCHANGE_CROSS_TRADE_LIVE=1 to auto-execute cross-trades"})
        except Exception:
            pass

    # --- per-venue reachability + funding + fee-positive config ---
    funded_any = False
    for v, assets in venue_assets.items():
        e = effective_config(v, cfg)
        try:
            quote = str(vapi.venue_quote_asset(v)).upper()
        except Exception:
            quote = "USDT"
        raw = vapi.get_account_balance(v, dry_run=False)
        reachable = bool(raw.get("success")) and not raw.get("simulated")
        add(f"{v}: balance read", reachable,
            "reachable" if reachable else (vapi.extract_order_error(raw) or "unreachable (auth/IP/region)"))
        if not reachable:
            continue
        bals = vapi.parse_spot_balances(v, dry_run=False) or {}
        free_quote = float(bals.get(quote) or 0)
        one_level = float(e["order_size_usd"])
        full_grid = one_level * int(e["grid_levels"])
        quote_ok = free_quote >= one_level
        add(f"{v}: {quote} funded (buys)", quote_ok,
            f"free {free_quote:.2f} {quote} — need >= {one_level:.2f} for 1 level, "
            f"{full_grid:.2f} for the full grid", severity="warn")
        held = {a: float(bals.get(a.upper()) or 0) for a in assets if float(bals.get(a.upper()) or 0) > 0}
        checks.append({"name": f"{v}: coin held (sell-from-existing)",
                       "status": "pass" if held else "info",
                       "detail": (", ".join(f"{k}:{amt:.4f}" for k, amt in list(held.items())[:5])
                                  if held else "none — sells seed only after buys fill")})
        if quote_ok or held:
            funded_any = True
        step_bps = float(e["grid_step_pct"]) * 1e4
        rt_fee = 2.0 * float(e["maker_fee_bps"])
        add(f"{v}: fee-positive step", step_bps > rt_fee,
            f"step {step_bps:.0f}bps vs round-trip fees {rt_fee:.0f}bps")

    add("at least one venue funded", funded_any,
        "fund quote for buys or hold coin for sells on >= 1 reachable venue")

    cb = cfg.get("circuit_breaker") or {}
    checks.append({"name": "circuit breaker", "status": "pass" if cb.get("enabled") else "warn",
                   "detail": (f"loss cap ${cb.get('loss_threshold_usd')} / {cb.get('window_hours')}h, "
                              f"resume {cb.get('cooldown_hours')}h" if cb.get("enabled") else "disabled")})

    ready = len(blockers) == 0
    actions: List[str] = []
    for b in blockers:
        actions.append("Fix: " + b)
    if ready and not grid_live:
        actions.append("Prerequisites met — set EXCHANGE_GRID_LIVE=1 in config.json to flip the grid live")
    verdict = ("READY — set the live gate to trade" if (ready and not grid_live)
               else "LIVE — trading real" if (ready and grid_live)
               else f"BLOCKED — {len(blockers)} issue(s) to fix")
    return {"success": True, "ready_to_flip_live": ready, "grid_live": grid_live,
            "verdict": verdict, "blockers": blockers, "checks": checks, "actions": actions,
            "note": "'Ready' means prerequisites (reachability, funding, fee-positive config) are "
                    "met; flipping the live gate is the final manual step."}


def daily_digest(window_hours: float = 24.0) -> Dict[str, Any]:
    """Passive summary of the trailing window: per-venue realized + fills, totals, currently
    paused venues, and the day's circuit-breaker pause/resume counts."""
    perf = venue_performance(window_hours=window_hours)
    venues = perf.get("venues") or []
    total_realized = round(sum(float(v.get("realized_usd") or 0) for v in venues), 6)
    total_fills = sum(int(v.get("fills") or 0) for v in venues)
    paused = paused_venues()
    st = _read_state()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ev_today = [e for e in (st.get("cb_event_log") or []) if str(e.get("ts", "")).startswith(today)]
    pauses = [e for e in ev_today if e.get("action") == "pause"]
    resumes = [e for e in ev_today if e.get("action") in ("auto_resume", "resume")]
    parts = [f"{int(round(window_hours))}h: {total_fills} fills, realized ${total_realized:.2f} "
             f"across {len(venues)} venue(s)"]
    if venues:
        parts.append("; ".join(f"{v['venue']} ${float(v.get('realized_usd') or 0):.2f}/"
                               f"{int(v.get('fills') or 0)}f" for v in venues[:6]))
    if paused:
        parts.append("paused: " + ", ".join(sorted(paused.keys())))
    if pauses or resumes:
        parts.append(f"breaker {len(pauses)} pause / {len(resumes)} resume")
    return {
        "success": True, "date": today, "window_hours": window_hours,
        "total_realized_usd": total_realized, "total_fills": total_fills,
        "venues": venues, "paused": sorted(paused.keys()),
        "pauses_today": len(pauses), "resumes_today": len(resumes),
        "focus_suggestion": perf.get("focus_suggestion"),
        "message": " | ".join(parts),
    }


def maybe_emit_daily_digest(record_fn=None, *, force: bool = False) -> Dict[str, Any]:
    """Emit the digest at most once per UTC day. ``record_fn(kind, message, level)`` receives it
    (e.g. the app's alerts feed). Idempotent via a date marker in state — safe to call every
    daemon loop / UI refresh."""
    st = _read_state()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not force and st.get("last_digest_date") == today:
        return {"success": True, "emitted": False, "reason": "already_emitted_today"}
    dg = daily_digest()
    if record_fn is not None:
        try:
            record_fn("digest", dg["message"], "info")
        except Exception:
            pass
    st = _read_state()
    st["last_digest_date"] = today
    _write_state(st)
    return {"success": True, "emitted": True, "digest": dg}


def _asset_states(st: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Only the per-(venue:asset) grid states — filters out metadata keys like paused_venues,
    cb_event_log, last_digest_date that also live in the state file."""
    return {k: s for k, s in st.items()
            if isinstance(s, dict) and ":" in str(k) and "inventory_base" in s}


def grid_profit() -> Dict[str, Any]:
    states = _asset_states(_read_state())
    realized = round(sum(float(s.get("realized_pnl_usd") or 0) for s in states.values()), 6)
    fills = sum(int(s.get("fills") or 0) for s in states.values())
    return {"success": True, "realized_pnl_usd": realized, "total_fills": fills,
            "assets": {k: round(float(s.get("realized_pnl_usd") or 0), 6) for k, s in states.items()}}


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
    """Daemon entry: tick every configured (venue, asset) when enabled. Venues tripped by the
    circuit breaker (persistent realized loss) are skipped until they auto-resume."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "disabled"}
    cb = check_circuit_breakers()
    paused = set((cb.get("paused") or {}).keys())
    results = []
    for venue, asset in grid_targets(cfg):
        if venue in paused:
            results.append({"success": True, "skipped": True, "venue": venue, "asset": asset,
                            "reason": "venue_paused"})
            continue
        try:
            results.append(run_grid_tick(venue, asset, dry_run=dry_run))
        except Exception as exc:
            results.append({"success": False, "venue": venue, "asset": asset, "error": str(exc)})
    return {"success": True, "ticks": results,
            "paused_venues": sorted(paused), "circuit_breaker_events": cb.get("events") or [],
            "realized_pnl_usd": grid_profit()["realized_pnl_usd"]}
