"""Binance spot asset reuse — resting limit sells at +profit_pct, cancel/reseed on −loss_cancel_pct.

Places one maker sell per held coin so idle spot inventory targets a fixed profit margin instead of
sitting unpriced. Wired into the unified profit daemon loop (see ``run_spot_reuse_tick``).

Live gate: ``EXCHANGE_SPOT_REUSE_LIVE=1`` and ``EXCHANGE_ARBITRAGE_LIVE=1`` plus venue credentials.
Paper by default (state-only simulation).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "crypto_exchange", "spot_reuse_config.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "spot_reuse_state.json")
_STABLES = frozenset({"USDT", "USDC", "USD", "BUSD", "FDUSD", "EUR", "DAI", "TUSD"})


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
        "profit_pct": 0.10,
        "loss_cancel_pct": 0.15,
        "min_notional_usd": 8.0,
        "reserve_pct": 0.02,
        "skip_grid_targets": True,
        "assets_allowlist": [],
    }


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
    allow = cfg.get("assets_allowlist")
    cfg["assets_allowlist"] = [str(a).upper() for a in allow if a] if isinstance(allow, list) else []
    return cfg


def save_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k in (
        "enabled",
        "venue",
        "profit_pct",
        "loss_cancel_pct",
        "min_notional_usd",
        "reserve_pct",
        "skip_grid_targets",
        "assets_allowlist",
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


def _eligible_assets(
    cfg: Dict[str, Any],
    balances: Dict[str, float],
    mids: Dict[str, float],
) -> List[Tuple[str, float, float]]:
    """Return (asset, qty, usd) rows above min notional."""
    venue = cfg["venue"]
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


def run_spot_reuse_tick(*, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Daemon / API entry — scan balances and maintain +profit_pct limit sells."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "disabled"}

    venue = cfg["venue"]
    live = spot_reuse_live_enabled() if dry_run is None else (not dry_run)
    paper = not live

    from backend.services import exchange_venue_api_service as vapi

    if not vapi.venue_has_credentials(venue) and live:
        return {"success": True, "skipped": True, "reason": "no_credentials", "venue": venue}

    balances: Dict[str, float] = {}
    if live:
        balances = vapi.parse_spot_balances(venue, dry_run=False) or {}
    elif paper:
        # Paper: reuse persisted synthetic balances if any, else empty tick
        st0 = _read_state()
        balances = st0.get("paper_balances") if isinstance(st0.get("paper_balances"), dict) else {}

    state = _read_state()
    assets_state = state.get("assets") if isinstance(state.get("assets"), dict) else {}
    mids: Dict[str, float] = {}
    rows_out: List[Dict[str, Any]] = []

    eligible = _eligible_assets(cfg, balances, mids)
    for sym, _q, _usd in eligible:
        mids[sym] = _mid_price(venue, sym)

    eligible = _eligible_assets(cfg, balances, mids)

    for sym, qty, usd in eligible:
        mid = mids.get(sym) or 0.0
        key = _state_key(venue, sym)
        row = assets_state.get(key) if isinstance(assets_state.get(key), dict) else {}
        detail = manage_asset(venue, sym, qty, mid, cfg, row, dry_run=paper)
        detail["usd_est"] = round(usd, 2)
        assets_state[key] = row
        rows_out.append(detail)

    # Drop state for assets no longer held
    active_keys = {_state_key(venue, sym) for sym, _, _ in eligible}
    for k in list(assets_state.keys()):
        if k.startswith(f"{venue}:") and k not in active_keys:
            stale = assets_state.pop(k, {})
            oid = str((stale or {}).get("sell_order_id") or "")
            if oid and live:
                asset = k.split(":", 1)[-1]
                _cancel_tracked(venue, asset, oid, dry_run=False)

    state["assets"] = assets_state
    state["last_tick_at"] = _iso()
    state["last_live"] = live
    state["last_count"] = len(rows_out)
    _write_state(state)

    placed = sum(1 for r in rows_out if r.get("action") == "placed_sell")
    resting = sum(1 for r in rows_out if r.get("action") == "resting")
    fills = sum(1 for r in rows_out if "tp_filled" in (r.get("events") or []))

    return {
        "success": True,
        "skipped": False,
        "live": live,
        "venue": venue,
        "profit_pct": cfg["profit_pct"],
        "loss_cancel_pct": cfg["loss_cancel_pct"],
        "assets": rows_out,
        "placed": placed,
        "resting": resting,
        "fills_this_tick": fills,
        "managed_count": len(rows_out),
    }


def ops_state() -> Dict[str, Any]:
    cfg = load_config()
    st = _read_state()
    return {
        "config": {
            "enabled": cfg.get("enabled"),
            "venue": cfg.get("venue"),
            "profit_pct": cfg.get("profit_pct"),
            "loss_cancel_pct": cfg.get("loss_cancel_pct"),
            "min_notional_usd": cfg.get("min_notional_usd"),
            "live_gate": spot_reuse_live_enabled(),
        },
        "last_tick_at": st.get("last_tick_at"),
        "last_count": st.get("last_count"),
        "last_live": st.get("last_live"),
        "assets": st.get("assets") if isinstance(st.get("assets"), dict) else {},
    }


def status() -> Dict[str, Any]:
    return {"success": True, **ops_state()}
