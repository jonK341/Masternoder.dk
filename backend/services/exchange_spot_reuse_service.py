"""Binance-first spot reuse — rotate all TRADING USDC/USDT pairs for entry/TP orders.

Optional entry limit buys (quote → base) at a discount below mid to refill inventory for the
next take-profit sell. Runs in the unified profit daemon (``run_spot_reuse_tick``).

Live: ``EXCHANGE_SPOT_REUSE_LIVE=1`` + ``EXCHANGE_ARBITRAGE_LIVE=1`` + venue credentials.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "crypto_exchange", "spot_reuse_config.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "spot_reuse_state.json")
_STABLES = frozenset({"USDT", "USDC", "USD", "BUSD", "FDUSD", "EUR", "DAI", "TUSD"})
_DEFAULT_VENUES = ("binance", "nonkyc")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clampf(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def _default_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "venue": "binance",
        "venues": ["binance", "nonkyc"],
        "binance_priority": True,
        "binance_full_catalog_entries": True,
        "entry_catalog_batch": 32,
        "profit_pct": 0.10,
        "loss_cancel_pct": 0.15,
        "min_notional_usd": 8.0,
        "reserve_pct": 0.02,
        "skip_grid_targets": True,
        "assets_allowlist": [],
        "entry_buy_enabled": True,
        "entry_buy_discount_pct": 0.08,
        "entry_quote_usd": 12.0,
        "entry_max_symbols": 16,
    }


def resolved_venues(cfg: Dict[str, Any]) -> List[str]:
    raw = cfg.get("venues")
    out: List[str] = []
    seen = set()
    if isinstance(raw, list) and raw:
        for v in raw:
            vid = str(v or "").lower().strip()
            if vid and vid not in seen:
                seen.add(vid)
                out.append(vid)
    if not out:
        out = [str(cfg.get("venue") or "binance").lower()]
    if cfg.get("binance_priority") and "binance" in out:
        out = ["binance"] + [v for v in out if v != "binance"]
    return out


def load_config() -> Dict[str, Any]:
    raw = ex._read_json(_CFG_PATH, None)
    if not isinstance(raw, dict):
        raw = _default_config()
        ex._write_json(_CFG_PATH, raw)
    cfg = _default_config()
    cfg.update({k: v for k, v in raw.items() if v is not None})
    cfg["enabled"] = bool(cfg.get("enabled"))
    cfg["venue"] = str(cfg.get("venue") or "binance").lower()
    cfg["profit_pct"] = _clampf(cfg.get("profit_pct"), 0.01, 0.5, 0.10)
    cfg["loss_cancel_pct"] = _clampf(cfg.get("loss_cancel_pct"), 0.01, 0.5, 0.15)
    cfg["min_notional_usd"] = _clampf(cfg.get("min_notional_usd"), 1.0, 1e6, 8.0)
    cfg["reserve_pct"] = _clampf(cfg.get("reserve_pct"), 0.0, 0.25, 0.02)
    cfg["skip_grid_targets"] = bool(cfg.get("skip_grid_targets"))
    cfg["entry_buy_enabled"] = bool(cfg.get("entry_buy_enabled"))
    cfg["entry_buy_discount_pct"] = _clampf(cfg.get("entry_buy_discount_pct"), 0.01, 0.35, 0.08)
    cfg["entry_quote_usd"] = _clampf(cfg.get("entry_quote_usd"), 5.0, 5000.0, 12.0)
    cfg["entry_max_symbols"] = int(_clampf(cfg.get("entry_max_symbols"), 0, 80, 16))
    cfg["entry_catalog_batch"] = int(_clampf(cfg.get("entry_catalog_batch"), 0, 120, 32))
    cfg["binance_priority"] = bool(cfg.get("binance_priority", True))
    cfg["binance_full_catalog_entries"] = bool(cfg.get("binance_full_catalog_entries", True))
    allow = cfg.get("assets_allowlist")
    cfg["assets_allowlist"] = [str(a).upper() for a in allow if a] if isinstance(allow, list) else []
    cfg["venues"] = resolved_venues(cfg)
    return cfg


def save_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k in (
        "enabled",
        "venue",
        "venues",
        "profit_pct",
        "loss_cancel_pct",
        "min_notional_usd",
        "reserve_pct",
        "skip_grid_targets",
        "assets_allowlist",
        "entry_buy_enabled",
        "entry_buy_discount_pct",
        "entry_quote_usd",
        "entry_max_symbols",
        "entry_catalog_batch",
        "binance_priority",
        "binance_full_catalog_entries",
    ):
        if k in patch and patch[k] is not None:
            cfg[k] = patch[k]
    ex._write_json(_CFG_PATH, cfg)
    return {"success": True, "config": load_config()}


def spot_reuse_live_enabled() -> bool:
    def _on(k: str) -> bool:
        return str(os.environ.get(k, "")).strip().lower() in ("1", "true", "yes", "on")

    return _on("EXCHANGE_SPOT_REUSE_LIVE") and _on("EXCHANGE_ARBITRAGE_LIVE")


def _read_state() -> Dict[str, Any]:
    data = ex._read_json(_STATE_PATH, {})
    return data if isinstance(data, dict) else {}


def _write_state(data: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, data)


def _state_key(venue: str, asset: str) -> str:
    return f"{venue.lower()}:{asset.upper()}"


def _mid_price(venue: str, asset: str) -> float:
    try:
        from backend.services import external_exchange_connector_service as conn

        tick = conn.fetch_ticker(venue, asset, timeout=5.0)
        if tick:
            bid = float(tick.get("bid") or 0)
            ask = float(tick.get("ask") or 0)
            if bid > 0 and ask > 0:
                return (bid + ask) / 2.0
            last = float(tick.get("last") or tick.get("price") or 0)
            if last > 0:
                return last
    except Exception:
        pass
    try:
        return float(ex._price_usd(asset) or 0)
    except Exception:
        return 0.0


def _grid_target_set() -> Set[Tuple[str, str]]:
    try:
        from backend.services.exchange_grid_bot_service import grid_targets, load_config as grid_cfg

        g = grid_cfg()
        if not g.get("enabled"):
            return set()
        return set(grid_targets(g))
    except Exception:
        return set()


def _entry_symbol_candidates(
    cfg: Dict[str, Any],
    venue: str,
    *,
    assets_state: Dict[str, Any],
    catalog_offset: int = 0,
) -> Tuple[List[str], int]:
    """Symbols to attempt entry buys this tick (hot first, then full Binance catalog rotation)."""
    allow = list(cfg.get("assets_allowlist") or [])
    cap = int(cfg.get("entry_max_symbols") or 16)
    if allow:
        return allow[:cap], catalog_offset

    hot: List[str] = []
    try:
        from backend.services.exchange_profit_pair_search_service import read_index, get_hot_symbols

        for s in get_hot_symbols(limit=24) or []:
            sym = str(s or "").upper()
            if sym and sym not in _STABLES and sym not in hot:
                hot.append(sym)
        idx = read_index()
        for s in idx.get("hot_symbols") or []:
            sym = str(s or "").upper()
            if sym and sym not in _STABLES and sym not in hot:
                hot.append(sym)
    except Exception:
        pass

    pending: List[str] = []
    prefix = f"{venue.lower()}:"
    for key, row in (assets_state or {}).items():
        if not str(key).startswith(prefix) or not isinstance(row, dict):
            continue
        if row.get("buy_order_id") and not row.get("sell_order_id"):
            sym = key.split(":", 1)[-1].upper()
            if sym not in pending:
                pending.append(sym)

    catalog_slice: List[str] = []
    next_off = catalog_offset
    if (
        str(venue).lower() == "binance"
        and cfg.get("binance_full_catalog_entries")
        and int(cfg.get("entry_catalog_batch") or 0) > 0
    ):
        try:
            from backend.services import exchange_venue_api_service as vapi
            from backend.services.exchange_binance_spot_catalog_service import catalog_batch

            quote = str(vapi.venue_quote_asset("binance")).upper()
            batch, next_off, _n = catalog_batch(
                batch_size=int(cfg["entry_catalog_batch"]),
                offset=catalog_offset,
                quote=quote,
            )
            catalog_slice = batch
        except Exception:
            pass

    merged: List[str] = []
    seen = set()
    for group in (hot, pending, catalog_slice):
        for sym in group:
            s = str(sym).upper()
            if s and s not in _STABLES and s not in seen:
                seen.add(s)
                merged.append(s)
            if len(merged) >= cap:
                return merged[:cap], next_off
    return merged[:cap], next_off


def _eligible_assets(
    venue: str,
    cfg: Dict[str, Any],
    balances: Dict[str, float],
    mids: Dict[str, float],
) -> List[Tuple[str, float, float]]:
    """Return (asset, qty, usd) rows above min notional."""
    min_usd = float(cfg["min_notional_usd"])
    allow = set(cfg.get("assets_allowlist") or [])
    skip_grid = cfg.get("skip_grid_targets")
    grid_set = _grid_target_set() if skip_grid else set()
    out: List[Tuple[str, float, float]] = []
    for asset, qty in (balances or {}).items():
        sym = str(asset or "").upper()
        if not sym or sym in _STABLES:
            continue
        if allow and sym not in allow:
            continue
        if skip_grid and (venue, sym) in grid_set:
            continue
        q = float(qty or 0)
        if q <= 0:
            continue
        mid = float(mids.get(sym) or 0)
        usd = q * mid if mid > 0 else 0.0
        if usd < min_usd:
            continue
        out.append((sym, q, usd))
    return out


def _cancel_tracked(
    venue: str,
    asset: str,
    order_id: str,
    *,
    dry_run: bool,
) -> Dict[str, Any]:
    if not order_id:
        return {"success": True, "skipped": True}
    from backend.services import exchange_venue_api_service as vapi

    return vapi.cancel_order(venue, asset, order_id, dry_run=dry_run)


def _quote_free(balances: Dict[str, float], venue: str) -> float:
    from backend.services import exchange_venue_api_service as vapi

    quote = str(vapi.venue_quote_asset(venue)).upper()
    return float(balances.get(quote) or 0)


def manage_entry_buy(
    venue: str,
    asset: str,
    mid: float,
    quote_free: float,
    cfg: Dict[str, Any],
    row: Dict[str, Any],
    *,
    dry_run: bool,
) -> Optional[Dict[str, Any]]:
    """Place/maintain a discount limit buy when we hold quote but little base."""
    if not cfg.get("entry_buy_enabled"):
        return None
    entry_usd = float(cfg["entry_quote_usd"])
    min_usd = float(cfg["min_notional_usd"])
    if quote_free < entry_usd or entry_usd < min_usd or mid <= 0:
        return None

    from backend.services import exchange_venue_api_service as vapi

    discount = float(cfg["entry_buy_discount_pct"])
    ref = float(row.get("ref_price") or mid)
    buy_px = round(ref * (1.0 - discount), 8)
    if buy_px <= 0:
        return None

    events: List[str] = []
    buy_id = str(row.get("buy_order_id") or "")

    if mid > 0 and ref > 0 and mid <= ref * (1.0 - float(cfg["loss_cancel_pct"])):
        if buy_id:
            _cancel_tracked(venue, asset, buy_id, dry_run=dry_run)
            buy_id = ""
            row["buy_order_id"] = ""
            events.append("entry_loss_cancel")

    if buy_id:
        st = vapi.get_order_status(venue, asset, buy_id, dry_run=dry_run)
        if st.get("filled"):
            row["buy_fills"] = int(row.get("buy_fills") or 0) + 1
            row["buy_order_id"] = ""
            fill_px = float(row.get("entry_buy_price") or buy_px)
            row["ref_price"] = round(fill_px, 8)
            row["ref_set_at"] = _iso()
            events.append("entry_filled")
            return {"asset": asset, "action": "entry_filled", "events": events, "mid": mid}

    qty = round(entry_usd / buy_px, 8)
    if qty * buy_px < min_usd:
        return None

    if buy_id and row.get("entry_buy_price"):
        if abs(float(row["entry_buy_price"]) - buy_px) <= buy_px * 0.002:
            return {"asset": asset, "action": "entry_resting", "events": events, "buy_price": buy_px}

    if buy_id:
        _cancel_tracked(venue, asset, buy_id, dry_run=dry_run)
        buy_id = ""

    coid = f"spotreuse-buy-{asset.lower()}-{int(datetime.now(timezone.utc).timestamp())}"
    pr = vapi.place_limit_order(venue, asset, "buy", qty, buy_px, dry_run=dry_run, client_order_id=coid)
    if not pr.get("success"):
        return {
            "asset": asset,
            "action": "entry_place_failed",
            "error": vapi.extract_order_error(pr) or pr.get("error"),
            "events": events,
        }
    row["buy_order_id"] = str(pr.get("order_id") or "")
    row["entry_buy_price"] = buy_px
    row["entry_buy_qty"] = qty
    events.append("entry_placed")
    return {"asset": asset, "action": "entry_placed", "buy_price": buy_px, "qty": qty, "events": events}


def manage_asset(
    venue: str,
    asset: str,
    qty_free: float,
    mid: float,
    cfg: Dict[str, Any],
    row: Dict[str, Any],
    *,
    dry_run: bool,
) -> Dict[str, Any]:
    """One asset: loss cancel, fill detection, ensure TP limit sell."""
    from backend.services import exchange_venue_api_service as vapi

    profit_pct = float(cfg["profit_pct"])
    loss_pct = float(cfg["loss_cancel_pct"])
    reserve = float(cfg["reserve_pct"])
    min_usd = float(cfg["min_notional_usd"])

    ref = float(row.get("ref_price") or 0)
    if ref <= 0 and mid > 0:
        ref = mid
        row["ref_price"] = round(ref, 8)
        row["ref_set_at"] = _iso()

    events: List[str] = []
    order_id = str(row.get("sell_order_id") or "")

    if mid > 0 and ref > 0 and mid <= ref * (1.0 - loss_pct):
        if order_id:
            cr = _cancel_tracked(venue, asset, order_id, dry_run=dry_run)
            events.append("loss_cancel")
            row["last_cancel"] = {"at": _iso(), "reason": "loss_margin", "result": cr}
            order_id = ""
            row["sell_order_id"] = ""
        buy_id = str(row.get("buy_order_id") or "")
        if buy_id:
            _cancel_tracked(venue, asset, buy_id, dry_run=dry_run)
            row["buy_order_id"] = ""
        row["ref_price"] = round(mid, 8)
        row["ref_set_at"] = _iso()
        ref = mid
        row["loss_events"] = int(row.get("loss_events") or 0) + 1

    if order_id:
        st = vapi.get_order_status(venue, asset, order_id, dry_run=dry_run)
        if st.get("filled"):
            row["last_fill"] = {
                "at": _iso(),
                "order_id": order_id,
                "ref_price": ref,
                "tp_price": row.get("tp_price"),
            }
            row["fills"] = int(row.get("fills") or 0) + 1
            events.append("tp_filled")
            order_id = ""
            row["sell_order_id"] = ""
            row["tp_price"] = None
            if mid > 0:
                row["ref_price"] = round(mid, 8)
                ref = mid

    sell_qty = max(0.0, float(qty_free) * (1.0 - reserve))
    tp_price = round(ref * (1.0 + profit_pct), 8) if ref > 0 else 0.0
    notional = sell_qty * tp_price if tp_price > 0 else 0.0

    if sell_qty <= 0 or notional < min_usd:
        return {
            "asset": asset,
            "mid": round(mid, 8),
            "ref_price": ref,
            "events": events,
            "action": "skip_dust",
        }

    need_place = not order_id
    if order_id and row.get("tp_price") and abs(float(row["tp_price"]) - tp_price) > tp_price * 0.001:
        _cancel_tracked(venue, asset, order_id, dry_run=dry_run)
        order_id = ""
        row["sell_order_id"] = ""
        need_place = True
        events.append("reprice")

    action = "resting"
    if need_place:
        coid = f"spotreuse-{asset.lower()}-{int(datetime.now(timezone.utc).timestamp())}"
        pr = vapi.place_limit_order(
            venue,
            asset,
            "sell",
            sell_qty,
            tp_price,
            dry_run=dry_run,
            client_order_id=coid,
        )
        if pr.get("success"):
            order_id = str(pr.get("order_id") or "")
            row["sell_order_id"] = order_id
            row["tp_price"] = tp_price
            row["sell_qty"] = round(sell_qty, 8)
            row["placed_at"] = _iso()
            action = "placed_sell"
            events.append("placed")
        else:
            action = "place_failed"
            events.append("place_failed")
            row["last_error"] = vapi.extract_order_error(pr) or pr.get("error")

    row["updated_at"] = _iso()
    return {
        "asset": asset,
        "mid": round(mid, 8),
        "ref_price": round(ref, 8),
        "tp_price": tp_price,
        "sell_qty": round(sell_qty, 8),
        "order_id": order_id or None,
        "events": events,
        "action": action,
    }


def _tick_venue(
    venue: str,
    cfg: Dict[str, Any],
    assets_state: Dict[str, Any],
    *,
    live: bool,
    paper: bool,
    catalog_offset: int = 0,
) -> Tuple[List[Dict[str, Any]], Dict[str, float], int]:
    from backend.services import exchange_venue_api_service as vapi

    dry_run = paper
    if live and not vapi.venue_has_credentials(venue):
        return [{"venue": venue, "skipped": True, "reason": "no_credentials"}], {}, catalog_offset

    balances: Dict[str, float] = {}
    if live:
        balances = vapi.parse_spot_balances(venue, dry_run=False) or {}
    elif paper:
        st0 = _read_state()
        pb = st0.get("paper_balances") if isinstance(st0.get("paper_balances"), dict) else {}
        if isinstance(pb.get(venue), dict):
            balances = pb[venue]

    mids: Dict[str, float] = {}
    rows_out: List[Dict[str, Any]] = []

    pre = _eligible_assets(venue, cfg, balances, mids)
    for sym, _q, _usd in pre:
        mids[sym] = _mid_price(venue, sym)

    held = {sym for sym, _, _ in _eligible_assets(venue, cfg, balances, mids)}
    quote_left = _quote_free(balances, venue)

    entry_syms, next_cat_off = _entry_symbol_candidates(
        cfg, venue, assets_state=assets_state, catalog_offset=catalog_offset,
    )

    for sym in entry_syms:
        if sym in held:
            continue
        mid = mids.get(sym) or _mid_price(venue, sym)
        mids[sym] = mid
        key = _state_key(venue, sym)
        row = assets_state.get(key) if isinstance(assets_state.get(key), dict) else {}
        ent = manage_entry_buy(venue, sym, mid, quote_left, cfg, row, dry_run=dry_run)
        if ent:
            ent["venue"] = venue
            rows_out.append(ent)
            assets_state[key] = row
            if ent.get("action") == "entry_placed":
                quote_left = max(0.0, quote_left - float(cfg["entry_quote_usd"]))

    eligible = _eligible_assets(venue, cfg, balances, mids)
    for sym, qty, usd in eligible:
        mid = mids.get(sym) or 0.0
        key = _state_key(venue, sym)
        row = assets_state.get(key) if isinstance(assets_state.get(key), dict) else {}
        detail = manage_asset(venue, sym, qty, mid, cfg, row, dry_run=dry_run)
        detail["usd_est"] = round(usd, 2)
        detail["venue"] = venue
        assets_state[key] = row
        rows_out.append(detail)

    prefix = f"{venue}:"
    active_keys = {_state_key(venue, sym) for sym, _, _ in eligible}
    for k in list(assets_state.keys()):
        if not k.startswith(prefix):
            continue
        if k in active_keys:
            continue
        stale = assets_state.get(k) if isinstance(assets_state.get(k), dict) else {}
        if stale.get("sell_order_id") or stale.get("buy_order_id"):
            continue
        assets_state.pop(k, None)

    return rows_out, balances, next_cat_off if str(venue).lower() == "binance" else catalog_offset


def run_spot_reuse_tick(*, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Daemon / API entry — scan balances and maintain +profit_pct limit sells."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "disabled"}

    live = spot_reuse_live_enabled() if dry_run is None else (not dry_run)
    paper = not live

    state = _read_state()
    assets_state = state.get("assets") if isinstance(state.get("assets"), dict) else {}
    all_rows: List[Dict[str, Any]] = []
    venues = resolved_venues(cfg)
    cat_off = int(state.get("binance_catalog_offset") or 0)

    if "binance" in venues and cfg.get("binance_full_catalog_entries"):
        try:
            from backend.services.exchange_binance_spot_catalog_service import refresh_binance_spot_catalog

            refresh_binance_spot_catalog()
        except Exception:
            pass

    for venue in venues:
        off = cat_off if venue == "binance" else 0
        rows, _bal, cat_off = _tick_venue(
            venue, cfg, assets_state, live=live, paper=paper, catalog_offset=off,
        )
        all_rows.extend(rows)

    state["assets"] = assets_state
    state["last_tick_at"] = _iso()
    state["last_live"] = live
    state["last_count"] = len(all_rows)
    state["last_venues"] = venues
    state["binance_catalog_offset"] = cat_off
    _write_state(state)

    coverage: Dict[str, Any] = {}
    try:
        from backend.services.exchange_binance_spot_catalog_service import coverage_snapshot

        coverage = coverage_snapshot(assets_state)
    except Exception:
        pass

    placed = sum(1 for r in all_rows if r.get("action") in ("placed_sell", "entry_placed"))
    resting = sum(1 for r in all_rows if r.get("action") in ("resting", "entry_resting"))
    fills = sum(1 for r in all_rows if "tp_filled" in (r.get("events") or []))

    return {
        "success": True,
        "skipped": False,
        "live": live,
        "venues": venues,
        "profit_pct": cfg["profit_pct"],
        "loss_cancel_pct": cfg["loss_cancel_pct"],
        "entry_buy_enabled": cfg.get("entry_buy_enabled"),
        "assets": all_rows,
        "placed": placed,
        "resting": resting,
        "fills_this_tick": fills,
        "managed_count": len(all_rows),
        "binance_coverage": coverage,
        "binance_catalog_offset": cat_off,
    }


def maybe_run_on_exchange_tick() -> Optional[Dict[str, Any]]:
    """Optional hook from exchange master daemon (throttled)."""
    if str(os.environ.get("EXCHANGE_SPOT_REUSE_ON_EXCHANGE", "")).strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return None
    try:
        interval = max(60, int(os.environ.get("EXCHANGE_SPOT_REUSE_EXCHANGE_INTERVAL", "180") or "180"))
    except ValueError:
        interval = 180
    st = _read_state()
    last = str(st.get("last_exchange_hook_at") or "")
    if last:
        try:
            prev = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - prev).total_seconds() < interval:
                return None
        except Exception:
            pass
    res = run_spot_reuse_tick()
    st = _read_state()
    st["last_exchange_hook_at"] = _iso()
    _write_state(st)
    return res


def ops_state() -> Dict[str, Any]:
    cfg = load_config()
    st = _read_state()
    assets_state = st.get("assets") if isinstance(st.get("assets"), dict) else {}
    coverage: Dict[str, Any] = {}
    try:
        from backend.services.exchange_binance_spot_catalog_service import coverage_snapshot

        coverage = coverage_snapshot(assets_state)
    except Exception:
        pass
    return {
        "config": {
            "enabled": cfg.get("enabled"),
            "venue": cfg.get("venue"),
            "venues": cfg.get("venues"),
            "binance_priority": cfg.get("binance_priority"),
            "binance_full_catalog_entries": cfg.get("binance_full_catalog_entries"),
            "entry_catalog_batch": cfg.get("entry_catalog_batch"),
            "profit_pct": cfg.get("profit_pct"),
            "loss_cancel_pct": cfg.get("loss_cancel_pct"),
            "min_notional_usd": cfg.get("min_notional_usd"),
            "entry_buy_enabled": cfg.get("entry_buy_enabled"),
            "live_gate": spot_reuse_live_enabled(),
        },
        "last_tick_at": st.get("last_tick_at"),
        "last_count": st.get("last_count"),
        "last_live": st.get("last_live"),
        "last_venues": st.get("last_venues"),
        "binance_catalog_offset": st.get("binance_catalog_offset"),
        "binance_coverage": coverage,
        "assets": assets_state,
    }


def status() -> Dict[str, Any]:
    return {"success": True, **ops_state()}
