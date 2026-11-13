"""Courier arm — cross-venue quote balancer for the profit body.

Moves free quote toward a per-venue floor (and a 50/50 split when funded) by
selling raise inventory on the starved venue. Distinct from hunter backfill:
courier equalizes BN↔NK so arms stop dying on one-sided funding.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "courier_arm_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "courier_arm_ledger.jsonl")
_VENUES = ("binance", "nonkyc")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cfg_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def courier_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("courier"):
            return False
    except Exception:
        pass
    raw = os.environ.get("COURIER_ARM_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "courier"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _quote_snaps() -> List[Dict[str, Any]]:
    from backend.services import exchange_venue_api_service as vapi

    out: List[Dict[str, Any]] = []
    for venue in _VENUES:
        quote = str(vapi.venue_quote_asset(venue) or "").upper()
        bals = vapi.parse_spot_balances(venue, dry_run=False, force_refresh=True) or {}
        free = float(bals.get(quote) or 0) if quote else 0.0
        out.append({"venue": venue, "quote": quote, "free": round(free, 4)})
    return out


def _imbalance(snaps: List[Dict[str, Any]], *, floor: float) -> Dict[str, Any]:
    total = sum(float(s.get("free") or 0) for s in snaps)
    by_id = {str(s.get("venue") or ""): s for s in snaps}
    # Keep Binance current: if BN is under floor, treat it as the starved venue even
    # when another venue is slightly poorer in absolute free quote.
    priority = (os.environ.get("COURIER_PRIORITY_VENUE") or "binance").strip().lower()
    rows = sorted(snaps, key=lambda s: float(s.get("free") or 0))
    poor = rows[0] if rows else {}
    rich = rows[-1] if rows else {}
    pri = by_id.get(priority) or {}
    if pri and float(pri.get("free") or 0) < floor:
        poor = pri
        others = [s for s in snaps if str(s.get("venue")) != priority]
        rich = max(others, key=lambda s: float(s.get("free") or 0)) if others else rich
    poor_free = float(poor.get("free") or 0)
    rich_free = float(rich.get("free") or 0)
    share_poor = (poor_free / total) if total > 0 else 0.0
    need_floor = max(0.0, floor - poor_free)
    # Aim toward ~45/55 band once total can fund both floors.
    target_poor = max(floor, total * 0.45) if total >= floor * 2 else floor
    need_ratio = max(0.0, target_poor - poor_free)
    move = round(min(max(need_floor, need_ratio), _cfg_float("COURIER_MAX_MOVE_USD", 25.0)), 2)
    skewed = poor_free < floor or (total >= floor * 2 and share_poor < 0.35)
    return {
        "skewed": skewed,
        "total_free_usd": round(total, 4),
        "poor": poor,
        "rich": rich,
        "share_poor": round(share_poor, 4),
        "move_usd": move,
        "floor_usd": floor,
        "priority_venue": priority,
        "keep_binance": priority == "binance" and float((by_id.get("binance") or {}).get("free") or 0) < floor,
    }


def _hot_sell_on_binance() -> Optional[str]:
    """Symbol the body wants to sell on Binance (seed inventory there)."""
    try:
        from backend.services.exchange_profit_head_service import get_prefund_hint, get_kill_shot

        for blob in (get_kill_shot(), get_prefund_hint()):
            if not isinstance(blob, dict):
                continue
            sym = str(blob.get("symbol") or "").upper()
            route = str(blob.get("route") or "").lower()
            if sym and ("→binance" in route or "->binance" in route or route.endswith("binance")):
                return sym
            if sym and not route:
                return sym
    except Exception:
        pass
    board = ex._read_json(os.path.join(ex._DATA_DIR, "spread_hunter_board.json"), {})
    for gap in (board.get("gaps") if isinstance(board, dict) else None) or []:
        if not isinstance(gap, dict):
            continue
        if str(gap.get("sell_venue") or "").lower() == "binance" and gap.get("symbol"):
            return str(gap["symbol"]).upper()
    state = ex._read_json(os.path.join(ex._DATA_DIR, "spread_hunter_arm_state.json"), {})
    top = (state.get("last_tick") or {}).get("top") if isinstance(state, dict) else None
    if isinstance(top, dict) and str(top.get("sell_venue") or "").lower() == "binance":
        return str(top.get("symbol") or "").upper() or None
    return None


def sync_binance(
    *,
    floor_usd: float = 12.0,
    unlock_usd: float = 25.0,
    seed_symbol: Optional[str] = None,
    seed_usd: float = 15.0,
) -> Dict[str, Any]:
    """Keep Binance current: unlock LD earn → spot, top up sell inventory, refresh grid."""
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn

    out: Dict[str, Any] = {
        "venue": "binance",
        "earn_unlock": None,
        "seed": None,
        "grid_reseed": None,
        "free_before": None,
        "free_after": None,
        "did_work": False,
    }
    quote = str(vapi.venue_quote_asset("binance") or "USDC").upper()
    bals = vapi.parse_spot_balances("binance", dry_run=False, force_refresh=True) or {}
    free = float(bals.get(quote) or 0)
    out["free_before"] = round(free, 4)

    # 1) Unlock Flexible Earn LD* wrappers into spot so Binance can trade.
    try:
        from backend.services.exchange_binance_earn_service import list_ld_balances, unlock_earn_to_spot

        ld = list_ld_balances(bals)
        if ld and os.environ.get("BINANCE_EARN_UNLOCK", "1").strip().lower() not in ("0", "false", "no", "off"):
            need = max(float(unlock_usd), max(0.0, float(floor_usd) - free) + 5.0)
            earn = unlock_earn_to_spot(target_usd=need, max_redeems=_cfg_int_safe(3))
            out["earn_unlock"] = {
                "success": earn.get("success"),
                "freed_usd_est": earn.get("freed_usd_est"),
                "reason": earn.get("reason"),
                "ld_n": len(ld),
            }
            if earn.get("success"):
                out["did_work"] = True
                vapi.invalidate_venue_balance_cache("binance")
                bals = vapi.parse_spot_balances("binance", dry_run=False, force_refresh=True) or {}
                free = float(bals.get(quote) or 0)
    except Exception as exc:
        out["earn_unlock"] = {"success": False, "error": str(exc)[:160]}

    # 2) If Binance quote still thin, sell unlocked spot (not LD*) into USDC.
    if free < float(floor_usd):
        from backend.services.exchange_spread_hunter_arm_service import _raise_quote_on_buy_venue

        raise_res = _raise_quote_on_buy_venue(
            "binance",
            need_usd=float(floor_usd),
            raise_symbols=None,
            min_sell_usd=_cfg_float("COURIER_MIN_MOVE_USD", 3.0),
            max_fraction=_cfg_float("COURIER_MAX_FRACTION", 0.55),
            scan_all_balances=True,
        )
        out["raise_quote"] = {
            "success": raise_res.get("success"),
            "skipped": raise_res.get("skipped"),
            "symbol": raise_res.get("symbol"),
            "sell_usd": raise_res.get("sell_usd"),
            "reason": raise_res.get("reason"),
        }
        if raise_res.get("success") and not raise_res.get("skipped"):
            out["did_work"] = True
            bals = vapi.parse_spot_balances("binance", dry_run=False, force_refresh=True) or {}
            free = float(bals.get(quote) or 0)

    # 3) Seed sell inventory on Binance for the hot nonkyc→binance route.
    # Fall back through API-key-whitelisted majors if the hot symbol is blocked.
    seed_candidates: List[str] = []
    if seed_symbol:
        seed_candidates.append(str(seed_symbol).upper())
    for s in ("ADA", "LINK", "XRP", "DOGE", "SOL", "BNB", "ALGO", "TRX"):
        if s not in seed_candidates:
            seed_candidates.append(s)
    if free >= max(float(floor_usd), float(seed_usd) * 0.5):
        seed_attempts: List[Dict[str, Any]] = []
        for sym in seed_candidates:
            qty = float(bals.get(sym) or 0)
            tick = conn.fetch_ticker("binance", sym) or {}
            ask = float(tick.get("ask") or 0)
            bid = float(tick.get("bid") or 0)
            px = ask or bid
            have_usd = qty * (bid or px) if (bid or px) > 0 else 0.0
            need_seed = float(seed_usd) - have_usd
            if px <= 0:
                seed_attempts.append({"symbol": sym, "skipped": True, "reason": "no_price"})
                continue
            if need_seed < _cfg_float("COURIER_MIN_MOVE_USD", 3.0):
                out["seed"] = {
                    "success": True, "skipped": True, "reason": "already_seeded",
                    "symbol": sym, "have_usd": round(have_usd, 2),
                }
                break
            buy_usd = min(need_seed, free - float(floor_usd), _cfg_float("COURIER_SEED_MAX_USD", 20.0))
            if buy_usd < _cfg_float("COURIER_MIN_MOVE_USD", 3.0):
                seed_attempts.append({"symbol": sym, "skipped": True, "reason": "insufficient_free"})
                continue
            buy_qty = round((buy_usd / px) * 0.995, 6)
            order = vapi.place_market_order("binance", sym, "buy", buy_qty, dry_run=False, quote=quote)
            ok = bool(order.get("success"))
            vapi.invalidate_venue_balance_cache("binance")
            row = {
                "success": ok,
                "symbol": sym,
                "buy_usd": round(buy_usd, 2),
                "buy_qty": buy_qty,
                "error": order.get("error") if not ok else None,
            }
            seed_attempts.append(row)
            if ok:
                out["seed"] = row
                out["did_work"] = True
                bals = vapi.parse_spot_balances("binance", dry_run=False, force_refresh=True) or {}
                free = float(bals.get(quote) or 0)
                break
            # Whitelist / permission errors → try next major.
            err = str(order.get("error") or "").lower()
            if "whitelist" not in err and "not allowed" not in err and "permission" not in err:
                out["seed"] = row
                break
        if "seed" not in out and seed_attempts:
            out["seed"] = {**seed_attempts[-1], "attempts": seed_attempts[:4]}

    # 4) Periodically reseed Binance grid ladders so BN stays live with the daemon.
    state = _load_state()
    reseed_every = _cfg_float("COURIER_BN_GRID_RESEED_SEC", 300.0)
    last = state.get("last_bn_grid_reseed_at")
    due = True
    if last:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(str(last).replace("Z", "+00:00"))).total_seconds()
            due = age >= reseed_every
        except Exception:
            due = True
    if due and os.environ.get("COURIER_BN_GRID_RESEED", "1").strip().lower() not in ("0", "false", "no", "off"):
        try:
            from backend.services.exchange_grid_bot_service import reset_open_orders

            cleared = reset_open_orders("binance")
            out["grid_reseed"] = {"success": True, "cleared": cleared.get("cleared") if isinstance(cleared, dict) else cleared}
            state["last_bn_grid_reseed_at"] = _iso()
            _save_state(state)
            out["did_work"] = True
        except Exception as exc:
            out["grid_reseed"] = {"success": False, "error": str(exc)[:160]}

    out["free_after"] = round(float((vapi.parse_spot_balances("binance", dry_run=False, force_refresh=True) or {}).get(quote) or free), 4)
    return out


def _cfg_int_safe(default: int) -> int:
    return int(_cfg_float("COURIER_EARN_MAX_REDEEMS", float(default)))


def quote_bridge_for_route(
    opp: Dict[str, Any],
    *,
    need_usd: float = 15.0,
    raise_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Fund the buy-venue quote leg for a BN↔NK route (USDC↔USDT bridge via raise sells).

    Venues settle in different stables; we cannot wire USDC→USDT directly, so the
    bridge sells raise inventory on the buy venue until free quote clears ``need_usd``.
    """
    from backend.services import exchange_venue_api_service as vapi
    from backend.services.exchange_spread_hunter_arm_service import _raise_quote_on_buy_venue

    buy_v = str(opp.get("buy_venue") or "").lower()
    sell_v = str(opp.get("sell_venue") or "").lower()
    if buy_v not in _VENUES:
        return {"success": False, "skipped": True, "reason": "bad_buy_venue", "technique": "quote_bridge_rotation"}

    quote = str(vapi.venue_quote_asset(buy_v) or "").upper()
    bals = vapi.parse_spot_balances(buy_v, dry_run=False, force_refresh=True) or {}
    free = float(bals.get(quote) or 0) if quote else 0.0
    target = max(float(need_usd), _cfg_float("COURIER_FLOOR_USD", 12.0))
    if free >= target:
        return {
            "success": True,
            "skipped": True,
            "reason": "buy_quote_funded",
            "technique": "quote_bridge_rotation",
            "venue": buy_v,
            "quote": quote,
            "free": round(free, 4),
            "sell_venue": sell_v,
        }

    preferred: List[str] = []
    sym = str(opp.get("symbol") or "").upper()
    if sym:
        preferred.append(sym)
    for s in raise_symbols or []:
        u = str(s or "").upper()
        if u and u not in preferred:
            preferred.append(u)

    action = _raise_quote_on_buy_venue(
        buy_v,
        need_usd=target,
        raise_symbols=preferred or None,
        min_sell_usd=_cfg_float("COURIER_MIN_MOVE_USD", 3.0),
        max_fraction=_cfg_float("COURIER_MAX_FRACTION", 0.55),
        scan_all_balances=True,
    )
    ok = bool(action.get("success")) and not action.get("skipped")
    if ok:
        vapi.invalidate_venue_balance_cache(buy_v)
        _append(
            "quote_bridge",
            buy_venue=buy_v,
            sell_venue=sell_v,
            symbol=action.get("symbol"),
            sell_usd=action.get("sell_usd"),
        )
    return {
        "success": bool(action.get("success")),
        "skipped": bool(action.get("skipped")),
        "technique": "quote_bridge_rotation",
        "venue": buy_v,
        "quote": quote,
        "free_before": round(free, 4),
        "need_usd": round(target, 2),
        "action": action,
        "reason": action.get("reason"),
    }


def _top_unfunded_route() -> Optional[Dict[str, Any]]:
    book = ex._read_json(os.path.join(ex._DATA_DIR, "profit_order_book.json"), {})
    for row in (book.get("top5") if isinstance(book, dict) else None) or []:
        if isinstance(row, dict) and row.get("qualifies") and not row.get("funded"):
            return row
    board = ex._read_json(os.path.join(ex._DATA_DIR, "spread_hunter_board.json"), {})
    gaps = board.get("gaps") if isinstance(board, dict) else None
    if isinstance(gaps, list) and gaps and isinstance(gaps[0], dict):
        return gaps[0]
    return None


def run_courier_tick(*, force: bool = False) -> Dict[str, Any]:
    """Keep Binance current, quote-bridge top route, then equalize if still starved."""
    if not courier_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "courier"}

    floor = _cfg_float("COURIER_FLOOR_USD", 12.0)
    seed_sym = _hot_sell_on_binance()
    bn_sync = sync_binance(
        floor_usd=floor,
        unlock_usd=_cfg_float("COURIER_BN_UNLOCK_USD", 25.0),
        seed_symbol=seed_sym,
        seed_usd=_cfg_float("COURIER_SEED_USD", 15.0),
    )

    bridge = None
    if os.environ.get("COURIER_QUOTE_BRIDGE", "1").strip().lower() not in ("0", "false", "no", "off"):
        top = _top_unfunded_route()
        if top:
            bridge = quote_bridge_for_route(
                top,
                need_usd=float(top.get("notional_usd") or _cfg_float("COURIER_SEED_USD", 15.0)),
            )
            if bridge.get("success") and not bridge.get("skipped"):
                bn_sync["did_work"] = True

    snaps = _quote_snaps()
    imb = _imbalance(snaps, floor=floor)
    out: Dict[str, Any] = {
        "success": True,
        "limb": "courier",
        "name": "courier",
        "scanned_at": _iso(),
        "quotes": snaps,
        "imbalance": imb,
        "binance_sync": bn_sync,
        "quote_bridge": bridge,
        "moved": False,
        "action": None,
        "skip_reason": None,
    }
    if bridge and bridge.get("success") and not bridge.get("skipped"):
        out["moved"] = True
        out["action"] = bridge.get("action") or bridge

    # Prefer raising on Binance when it is the priority starved venue.
    do_raise = bool(imb.get("skewed")) and not out["moved"]
    poor = imb.get("poor") or {}
    venue = str(poor.get("venue") or "")
    # If Binance is already funded, do not keep draining NonKYC just to chase 45/55 —
    # only raise NonKYC when it is under the hard floor.
    if venue == "nonkyc" and float(poor.get("free") or 0) >= floor:
        do_raise = False

    if do_raise:
        move = float(imb.get("move_usd") or 0)
        if venue and move >= _cfg_float("COURIER_MIN_MOVE_USD", 3.0):
            preferred: List[str] = []
            try:
                from backend.services.exchange_profit_head_service import get_prefund_hint

                hint = get_prefund_hint()
                if hint and hint.get("symbol"):
                    preferred.append(str(hint["symbol"]).upper())
            except Exception:
                pass
            from backend.services.exchange_spread_hunter_arm_service import _raise_quote_on_buy_venue

            need = float(poor.get("free") or 0) + move
            action = _raise_quote_on_buy_venue(
                venue,
                need_usd=need,
                raise_symbols=preferred or None,
                min_sell_usd=_cfg_float("COURIER_MIN_MOVE_USD", 3.0),
                max_fraction=_cfg_float("COURIER_MAX_FRACTION", 0.5),
                scan_all_balances=True,
            )
            out["action"] = action
            out["moved"] = bool(action.get("success")) and not action.get("skipped")
            if not out["moved"]:
                out["skip_reason"] = str(action.get("reason") or "raise_failed")
        else:
            out["skip_reason"] = "gap_too_small"
    elif out["moved"]:
        out["skip_reason"] = None
    else:
        out["skip_reason"] = "bn_synced" if bn_sync.get("did_work") else "balanced"

    after = _quote_snaps()
    imb_after = _imbalance(after, floor=floor)
    out["quotes_after"] = after
    out["imbalance_after"] = imb_after
    hint = {
        "from_venue": (imb.get("rich") or {}).get("venue"),
        "to_venue": venue or "binance",
        "amount_usd": float(imb.get("move_usd") or 0),
        "reason": "keep_binance_current" if (bn_sync.get("did_work") or imb.get("keep_binance")) else "quote_imbalance",
        "poor_free": (imb.get("poor") or {}).get("free"),
        "rich_free": (imb.get("rich") or {}).get("free"),
        "binance_free": next((s.get("free") for s in after if s.get("venue") == "binance"), None),
        "seed_symbol": seed_sym,
    }
    out["courier_hint"] = hint
    try:
        from backend.services.exchange_profit_head_service import set_courier_hint

        set_courier_hint(hint if (imb_after.get("skewed") or bn_sync.get("did_work")) else None)
    except Exception:
        pass

    _append(
        "courier_tick",
        moved=out["moved"],
        venue=venue,
        bn_sync=bool(bn_sync.get("did_work")),
        seed=seed_sym,
        earn=(bn_sync.get("earn_unlock") or {}).get("success"),
        skip=out.get("skip_reason"),
    )
    _persist(out)
    bn_bits = []
    if (bn_sync.get("earn_unlock") or {}).get("success"):
        bn_bits.append(f"earn=${float((bn_sync.get('earn_unlock') or {}).get('freed_usd_est') or 0):.0f}")
    if (bn_sync.get("seed") or {}).get("success") and not (bn_sync.get("seed") or {}).get("skipped"):
        bn_bits.append(f"seed={seed_sym}")
    if (bn_sync.get("grid_reseed") or {}).get("success"):
        bn_bits.append("grid_reseed")
    if bridge and bridge.get("success") and not bridge.get("skipped"):
        bn_bits.append("quote_bridge")
    summary = (
        f"moved={'yes' if out['moved'] else 'no'} "
        f"bn={'|'.join(bn_bits) if bn_bits else ('ok' if not bn_sync.get('did_work') else 'sync')} "
        f"bn_free=${float(bn_sync.get('free_after') or 0):.2f}"
    )
    if venue and do_raise:
        summary += (
            f" poor={venue}:${float((imb.get('poor') or {}).get('free') or 0):.2f} "
            f"need=${float(imb.get('move_usd') or 0):.2f}"
        )
    if out.get("skip_reason"):
        summary += f" skip={out['skip_reason']}"
    out["summary"] = summary
    return out


def _persist(out: Dict[str, Any]) -> None:
    state = _load_state()
    bn = out.get("binance_sync") if isinstance(out.get("binance_sync"), dict) else {}
    state.update({
        "updated_at": _iso(),
        "last_tick": {
            "moved": out.get("moved"),
            "skip_reason": out.get("skip_reason"),
            "imbalance": out.get("imbalance"),
            "binance_sync": {
                "did_work": bn.get("did_work"),
                "free_after": bn.get("free_after"),
                "earn": (bn.get("earn_unlock") or {}).get("success"),
                "seed": bn.get("seed"),
                "grid_reseed": bool((bn.get("grid_reseed") or {}).get("success")),
            },
            "action": {
                "success": (out.get("action") or {}).get("success"),
                "symbol": (out.get("action") or {}).get("symbol"),
                "sell_usd": (out.get("action") or {}).get("sell_usd"),
                "venue": (out.get("action") or {}).get("venue"),
            } if out.get("action") else None,
            "courier_hint": out.get("courier_hint"),
        },
    })
    if out.get("moved"):
        state["move_count"] = int(state.get("move_count") or 0) + 1
        state["last_move_at"] = out.get("scanned_at")
    _save_state(state)
    if not out.get("summary"):
        out["summary"] = (
            f"moved={'yes' if out.get('moved') else 'no'} "
            f"skip={out.get('skip_reason') or '-'}"
        )
