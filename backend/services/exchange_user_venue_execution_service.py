"""User-facing live execution on Binance / NonKYC via signed venue APIs.

Custodial model: platform venue keys place the market order; the user's exchange
wallet is debited/credited to mirror the fill. Paper mode when live gates are off.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn

_USER_VENUES = frozenset({"binance", "nonkyc"})


def _venue_quote(venue_id: str) -> str:
    vmap = {v["id"]: v for v in (conn.load_connectors_config().get("venues") or []) if v.get("id")}
    return str((vmap.get(venue_id) or {}).get("quote") or ("USDC" if venue_id == "binance" else "USDT")).upper()


def venue_supported(venue_id: str) -> bool:
    return str(venue_id or "").lower() in _USER_VENUES


def venue_ready(venue_id: str) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi
    from backend.services.exchange_live_execution_service import venue_live_ready

    vid = str(venue_id or "").lower()
    if not venue_supported(vid):
        return {"ok": False, "error": "unsupported_venue", "venue_id": vid}
    creds = vapi.venue_has_credentials(vid)
    live = venue_live_ready(vid)
    return {
        "ok": True,
        "venue_id": vid,
        "credentials_configured": creds,
        "live_ready": live,
        "mode": "live" if live else "paper",
        "quote_currency": _venue_quote(vid),
    }


def _external_price(venue_id: str, symbol: str, side: str) -> float:
    sym = str(symbol or "").upper()
    tick = conn.fetch_ticker(venue_id, sym, timeout=5.0) or {}
    side_l = str(side or "buy").lower()
    px = float(tick.get("ask") if side_l == "buy" else tick.get("bid") or tick.get("last") or 0)
    if px <= 0:
        batch = conn.fetch_prices([sym], venues=[venue_id], use_cache=True)
        row = ((batch.get("prices") or {}).get(sym) or {}).get(venue_id) or {}
        bid = float(row.get("bid") or 0)
        ask = float(row.get("ask") or 0)
        px = ask if side_l == "buy" else (bid or ask)
    return px


def quote_venue_swap(
    user_id: str,
    venue_id: str,
    symbol: str,
    side: str,
    amount: float,
    quote: Optional[str] = None,
) -> Dict[str, Any]:
    """Quote a spot swap routed to an external venue."""
    cfg = ex.load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "exchange_disabled"}
    vid = str(venue_id or "").lower()
    if not venue_supported(vid):
        return {"success": False, "error": "unsupported_venue"}
    sym = (symbol or "").strip().upper()
    side_l = (side or "").strip().lower()
    venue_quote = _venue_quote(vid)
    quote_cur = (quote or venue_quote).strip().upper()
    if quote_cur not in (venue_quote, "USDC", "USDT", "MN2", "COINS"):
        return {"success": False, "error": "invalid_quote_for_venue", "expected": venue_quote}
    if sym not in ex._asset_map(cfg):
        return {"success": False, "error": "unknown_asset"}
    if side_l not in ("buy", "sell"):
        return {"success": False, "error": "invalid_side"}
    amt = float(amount or 0)
    asset = ex._asset_map(cfg)[sym]
    if amt < float(asset.get("min_trade") or 0):
        return {"success": False, "error": "below_min_trade", "min_trade": asset.get("min_trade")}

    px_usd = _external_price(vid, sym, side_l)
    if px_usd <= 0:
        return {"success": False, "error": "no_external_price", "venue_id": vid}

    spread_bps = int((cfg.get("platform_fees") or {}).get("swap_spread_bps") or 50)
    fee_bps = ex._fee_bps(side_l, False, cfg, user_id or "anon")
    total_bps = spread_bps + fee_bps

    if quote_cur in ("MN2", "COINS"):
        price_q = ex._price_in_quote(sym, quote_cur, cfg)
    else:
        sym_usd = px_usd
        quote_usd = ex._price_usd(quote_cur, cfg) or 1.0
        price_q = sym_usd / quote_usd if quote_usd > 0 else 0.0

    if price_q <= 0:
        return {"success": False, "error": "no_price"}

    if side_l == "buy":
        quote_cost = amt * price_q * (1 + total_bps / 10000)
        fee_quote = amt * price_q * (total_bps / 10000)
        quote_received = 0.0
    else:
        quote_out = amt * price_q * (1 - total_bps / 10000)
        fee_quote = amt * price_q * (total_bps / 10000)
        quote_cost = 0.0
        quote_received = quote_out

    readiness = venue_ready(vid)
    qid = uuid.uuid4().hex[:16]
    payload: Dict[str, Any] = {
        "success": True,
        "quote_id": qid,
        "venue_id": vid,
        "execution_venue": vid,
        "mode": readiness.get("mode") or "paper",
        "symbol": sym,
        "side": side_l,
        "amount": amt,
        "quote_currency": quote_cur,
        "price_quote": round(price_q, 8),
        "external_price_usd": round(px_usd, 8),
        "fee_quote": round(fee_quote, 8),
        "fee_bps": total_bps,
        "usd_value": round(amt * px_usd, 4),
    }
    if side_l == "buy":
        payload["quote_cost"] = round(quote_cost, 8)
    else:
        payload["quote_received"] = round(quote_received, 8)
    return payload


def execute_venue_swap(
    user_id: str,
    venue_id: str,
    quote_id: str,
    symbol: str,
    side: str,
    amount: float,
    quote: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    from backend.services import exchange_venue_api_service as vapi

    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    q = quote_venue_swap(uid, venue_id, symbol, side, amount, quote)
    if not q.get("success"):
        return q

    vid = q["venue_id"]
    sym = q["symbol"]
    side_l = q["side"]
    amt = float(q["amount"])
    quote_cur = q["quote_currency"]
    readiness = venue_ready(vid)
    live = readiness.get("live_ready") and readiness.get("mode") == "live"

    ref = f"ex-venue:{vid}:{quote_id}:{uuid.uuid4().hex[:8]}"
    meta = {"reference": ref, "quote_id": quote_id, "venue_id": vid, "symbol": sym, "side": side_l}

    with ex._LOCK:
        if side_l == "buy":
            cost = float(q.get("quote_cost") or 0)
            bal = ex._get_quote_balance(uid, quote_cur)
            if bal < cost:
                return {"success": False, "error": f"insufficient_{quote_cur.lower()}"}
        else:
            if ex._get_balance(uid, sym) < amt:
                return {"success": False, "error": f"insufficient_{sym.lower()}"}

    order_side = "buy" if side_l == "buy" else "sell"
    order_res = vapi.place_market_order(
        vid, sym, order_side, amt,
        dry_run=not live,
        quote=_venue_quote(vid),
    )
    if not order_res.get("success"):
        return {
            "success": False,
            "error": order_res.get("error") or "venue_order_failed",
            "venue_id": vid,
            "order": order_res,
        }

    try:
        with ex._LOCK:
            if side_l == "buy":
                cost = float(q.get("quote_cost") or 0)
                ex._adjust_quote_balance(uid, quote_cur, -cost, "exchange_venue_buy", meta)
                ex._adjust_balance(uid, sym, amt)
            else:
                received = float(q.get("quote_received") or 0)
                ex._adjust_balance(uid, sym, -amt)
                ex._adjust_quote_balance(uid, quote_cur, received, "exchange_venue_sell", meta)

            fee_mn2 = ex._fee_quote_to_mn2(float(q.get("fee_quote") or 0), quote_cur, ex.load_config())
            ex._collect_fee(fee_mn2)
            ex._add_volume(uid, float(q.get("usd_value") or 0))
            ex._record_tax(
                uid, sym, side_l, amt, float(q.get("usd_value") or 0),
                ex._fee_quote_to_usd(float(q.get("fee_quote") or 0), quote_cur, ex.load_config()),
            )

            trade = {
                "ts": ex._iso(), "trade_id": ref, "user_id": uid, "type": "venue_swap",
                "venue_id": vid, "mode": order_res.get("mode") or readiness.get("mode") or "paper",
                "simulated": bool(order_res.get("simulated")),
                "symbol": sym, "side": side_l, "amount": amt, "quote": quote_cur,
                "usd_value": q.get("usd_value"), "fee_bps": q.get("fee_bps"),
                "order_id": order_res.get("order_id") or order_res.get("id"),
            }
            ex._append_jsonl(ex._TRADES_PATH, trade)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "venue_id": vid, "order": order_res}
    except Exception as exc:
        return {"success": False, "error": str(exc), "venue_id": vid, "order": order_res}

    ex._audit(
        "venue_swap", user_id=uid, amount_usd=float(q.get("usd_value") or 0),
        symbol=sym, side=side_l, amount=amt, quote=quote_cur, venue_id=vid,
        trade_id=ref, mode=trade.get("mode"),
    )
    return {
        "success": True,
        "trade": trade,
        "order": order_res,
        "wallet": ex.get_wallet(uid),
        "venue_id": vid,
        "mode": trade.get("mode"),
    }
