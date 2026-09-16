"""Fiat converter — consolidate the sales pool's crypto into a stable/fiat cash-out.

This is the "missing piece" between the internal sales-pool ledger and a real payout:

1. **Valuation** — price every pooled asset in USD.
2. **Plan** — for a chosen ``target`` (a stablecoin like ``USDC`` or a fiat like ``USD``),
   build the sell legs (crypto -> venue stable) plus, for fiat targets, a stable -> fiat
   off-ramp (PayPal payout) leg, with estimated fees and net proceeds.
3. **Execute** — run the plan. Paper by default (ledger-only, no funds move). Live requires
   ``EXCHANGE_FIAT_CONVERT_LIVE=1`` + ``EXCHANGE_ARBITRAGE_LIVE=1`` and, critically, that the
   pooled coins actually exist on the venue account (the internal ledger is not on-venue
   custody). Missing on-venue balance is surfaced as a blocker, never silently skipped.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONV_LEDGER_PATH = os.path.join(ex._DATA_DIR, "fiat_conversions.jsonl")

_STABLES = frozenset({"USDT", "USDC", "BUSD", "DAI", "TUSD", "USDD"})
_FIAT = frozenset({"USD", "EUR", "GBP"})
_DEFAULT_DUST_USD = 1.0


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _usd_price(sym: str) -> float:
    sym_u = str(sym or "").upper()
    price = float(ex._price_usd(sym_u) or 0)
    if price <= 0 and sym_u in _STABLES:
        return 1.0
    return price


def _pool_uid() -> str:
    try:
        from backend.services.exchange_sales_pool_service import sales_pool_user_id
        return sales_pool_user_id()
    except Exception:
        return "exchange_sales_pool"


def _venue_stable(venue: str) -> str:
    """The stable quote a venue settles crypto sales into."""
    try:
        from backend.services.external_exchange_connector_service import venue_quote
        q = str(venue_quote(venue) or "").upper()
        if q in _STABLES:
            return q
    except Exception:
        pass
    return "USDC" if venue == "binance" else "USDT"


def _venue_fee_bps(venue: str) -> float:
    try:
        from backend.services import external_exchange_connector_service as conn
        for v in (conn.load_connectors_config().get("venues") or []):
            if isinstance(v, dict) and str(v.get("id")) == venue:
                return float(v.get("fee_taker_bps") or 0)
    except Exception:
        pass
    return 20.0


def fiat_convert_live_enabled() -> bool:
    if os.environ.get("EXCHANGE_FIAT_CONVERT_LIVE", "").strip() not in ("1", "true", "yes"):
        return False
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        if not live_enabled():
            return False
    except Exception:
        return False
    try:
        from backend.services import mn2_spork_service as spork
        ok, _reason = spork.payout_live_spork_ok()
        if not ok:
            return False
    except Exception:
        pass
    return True


def pool_valuation() -> Dict[str, Any]:
    """Per-asset USD valuation of the sales pool."""
    pool_uid = _pool_uid()
    assets = (ex.get_wallet(pool_uid).get("assets") or {})
    rows: List[Dict[str, Any]] = []
    total = 0.0
    stable_usd = 0.0
    crypto_usd = 0.0
    for sym, amt in assets.items():
        amount = float(amt or 0)
        if amount <= 0:
            continue
        sym_u = str(sym).upper()
        price = _usd_price(sym_u)
        usd = round(amount * price, 4)
        is_stable = sym_u in _STABLES
        rows.append({
            "symbol": sym_u,
            "amount": round(amount, 12),
            "price_usd": round(price, 8),
            "usd_value": usd,
            "stable": is_stable,
            "priced": price > 0,
        })
        total += usd
        if is_stable:
            stable_usd += usd
        else:
            crypto_usd += usd
    rows.sort(key=lambda r: r["usd_value"], reverse=True)
    return {
        "success": True,
        "sales_pool_user_id": pool_uid,
        "assets": rows,
        "total_usd": round(total, 4),
        "stable_usd": round(stable_usd, 4),
        "crypto_usd": round(crypto_usd, 4),
        "asset_count": len(rows),
    }


def _resolve_target(target: str, venue: str) -> Dict[str, Any]:
    t = str(target or "USD").upper()
    if t in _FIAT:
        return {"target": t, "kind": "fiat", "stable": _venue_stable(venue)}
    if t in _STABLES:
        return {"target": t, "kind": "stable", "stable": t}
    return {"target": t, "kind": "stable", "stable": t if t in _STABLES else _venue_stable(venue)}


def plan_fiat_conversion(*, venue: str = "binance", target: str = "USD",
                         min_usd: Optional[float] = None,
                         dust_usd: Optional[float] = None) -> Dict[str, Any]:
    venue = str(venue or "binance").lower()
    resolved = _resolve_target(target, venue)
    stable = resolved["stable"]
    fee_bps = _venue_fee_bps(venue)
    dust = float(dust_usd if dust_usd is not None else _DEFAULT_DUST_USD)
    val = pool_valuation()

    sell_legs: List[Dict[str, Any]] = []
    est_stable_from_sells = 0.0
    est_fees_usd = 0.0
    skipped: List[Dict[str, Any]] = []
    stable_on_hand = 0.0

    for row in val["assets"]:
        sym = row["symbol"]
        if sym == stable:
            stable_on_hand += row["usd_value"]
            continue
        if sym in _STABLES:
            # Different stable already ~ cash; treat as convertible 1:1 (no venue leg).
            stable_on_hand += row["usd_value"]
            continue
        if not row["priced"]:
            skipped.append({"symbol": sym, "reason": "no_price"})
            continue
        if row["usd_value"] < dust:
            skipped.append({"symbol": sym, "reason": "below_dust", "usd_value": row["usd_value"]})
            continue
        fee_usd = round(row["usd_value"] * fee_bps / 10000.0, 4)
        net_stable = round(row["usd_value"] - fee_usd, 4)
        est_stable_from_sells += net_stable
        est_fees_usd += fee_usd
        sell_legs.append({
            "symbol": sym,
            "amount": row["amount"],
            "price_usd": row["price_usd"],
            "gross_usd": row["usd_value"],
            "fee_usd": fee_usd,
            "net_stable_usd": net_stable,
            "market": f"{sym}/{stable}",
            "side": "sell",
        })

    total_stable = round(stable_on_hand + est_stable_from_sells, 4)
    threshold = float(min_usd if min_usd is not None else 0.0)
    actionable = total_stable >= threshold and (bool(sell_legs) or (resolved["kind"] == "fiat" and total_stable > 0))

    offramp = None
    if resolved["kind"] == "fiat":
        offramp = _plan_fiat_offramp(total_stable, resolved["target"])

    return {
        "success": True,
        "venue": venue,
        "target": resolved["target"],
        "target_kind": resolved["kind"],
        "consolidation_stable": stable,
        "venue_fee_bps": fee_bps,
        "sell_legs": sell_legs,
        "skipped": skipped,
        "stable_on_hand_usd": round(stable_on_hand, 4),
        "est_stable_from_sells_usd": round(est_stable_from_sells, 4),
        "est_fees_usd": round(est_fees_usd, 4),
        "est_total_stable_usd": total_stable,
        "offramp": offramp,
        "actionable": actionable,
        "min_usd": threshold,
        "mode": "live" if fiat_convert_live_enabled() else "paper",
    }


def _plan_fiat_offramp(stable_usd: float, target_fiat: str) -> Dict[str, Any]:
    """Plan the stable -> fiat leg via the configured PayPal payout rail."""
    try:
        from backend.services import exchange_payout_service as pay
        cfg = pay._load()
        email = pay._owner_paypal_email(cfg)
        share = pay._paypal_share_pct(cfg)
        live = pay._paypal_live_enabled()
    except Exception:
        email, share, live = "", 1.0, False
    amount = round(stable_usd * float(share or 1.0), 4)
    return {
        "rail": "paypal" if email else "manual",
        "receiver_email": email or None,
        "share_pct": round(float(share or 1.0) * 100, 2),
        "amount_usd": amount,
        "fiat": target_fiat,
        "live_enabled": bool(live),
        "note": (
            "PayPal payout of the consolidated stable balance."
            if email else
            "No PayPal email configured — set EXCHANGE_PAYOUT_PAYPAL_EMAIL to enable fiat off-ramp."
        ),
    }


def execute_fiat_conversion(*, venue: str = "binance", target: str = "USD",
                            min_usd: Optional[float] = None,
                            dust_usd: Optional[float] = None,
                            dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Run the conversion. Paper by default; live is multi-gated + requires on-venue custody."""
    plan = plan_fiat_conversion(venue=venue, target=target, min_usd=min_usd, dust_usd=dust_usd)
    if not plan.get("actionable"):
        return {"success": False, "error": "not_actionable", "plan": plan}

    venue = plan["venue"]
    stable = plan["consolidation_stable"]
    pool_uid = _pool_uid()
    live = fiat_convert_live_enabled() if dry_run is None else (not dry_run)

    sells: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    credited_stable = 0.0

    venue_balances: Dict[str, float] = {}
    if live:
        try:
            from backend.services import exchange_venue_api_service as vapi
            venue_balances = {k.upper(): float(v) for k, v in
                              (vapi.parse_spot_balances(venue, dry_run=False) or {}).items()}
        except Exception:
            venue_balances = {}

    with ex._LOCK:
        for leg in plan["sell_legs"]:
            sym = leg["symbol"]
            amount = float(leg["amount"])
            # Re-read live pool balance; never oversell the ledger.
            cur = float((ex.get_wallet(pool_uid).get("assets") or {}).get(sym) or 0)
            amount = min(amount, round(cur, 12))
            if amount <= 0:
                continue

            if live:
                if float(venue_balances.get(sym, 0)) < amount:
                    blockers.append({
                        "symbol": sym,
                        "code": "venue_spot_insufficient",
                        "message": (
                            f"Pool ledger holds {round(cur, 8)} {sym} but {venue} spot has "
                            f"{round(float(venue_balances.get(sym, 0)), 8)}. Deposit real {sym} to {venue} first."
                        ),
                    })
                    continue
                from backend.services import exchange_venue_api_service as vapi
                order = vapi.place_market_order(venue, sym, "sell", amount)
                if not order.get("success"):
                    blockers.append({"symbol": sym, "code": "sell_failed",
                                     "message": vapi.extract_order_error(order) or "order_failed"})
                    continue
                proceeds = float(order.get("notional_usd") or leg["net_stable_usd"])
            else:
                proceeds = float(leg["net_stable_usd"])

            ex._adjust_balance(pool_uid, sym, -amount)
            ex._adjust_balance(pool_uid, stable, proceeds)
            credited_stable += proceeds
            row = {
                "ts": _iso(), "phase": "sell", "venue": venue, "symbol": sym,
                "amount": round(amount, 12), "proceeds_stable_usd": round(proceeds, 4),
                "stable": stable, "mode": "live" if live else "paper",
            }
            ex._append_jsonl(_CONV_LEDGER_PATH, row)
            sells.append(row)

    ex._audit("fiat_convert_consolidate", user_id="owner", venue=venue, stable=stable,
              legs=len(sells), credited_stable_usd=round(credited_stable, 4),
              mode="live" if live else "paper")

    offramp_result = None
    if plan["target_kind"] == "fiat":
        stable_balance = float((ex.get_wallet(pool_uid).get("assets") or {}).get(stable) or 0)
        offramp_result = _execute_fiat_offramp(stable, stable_balance, plan["target"], live=live)

    return {
        "success": True,
        "venue": venue,
        "target": plan["target"],
        "consolidation_stable": stable,
        "mode": "live" if live else "paper",
        "sells": sells,
        "blockers": blockers,
        "credited_stable_usd": round(credited_stable, 4),
        "offramp": offramp_result,
        "note": (
            None if live else
            "Paper conversion: pool ledger consolidated only; no funds moved. "
            "Set EXCHANGE_FIAT_CONVERT_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 (and fund the venue) for real conversion."
        ),
    }


def _execute_fiat_offramp(stable: str, stable_balance: float, target_fiat: str, *,
                          live: bool) -> Dict[str, Any]:
    pool_uid = _pool_uid()
    try:
        from backend.services import exchange_payout_service as pay
        cfg = pay._load()
        email = pay._owner_paypal_email(cfg)
        share = float(pay._paypal_share_pct(cfg) or 1.0)
        paypal_live = pay._paypal_live_enabled()
    except Exception:
        email, share, paypal_live = "", 1.0, False

    amount = round(max(0.0, stable_balance) * share, 4)
    if amount <= 0:
        return {"success": False, "error": "no_stable_balance", "stable": stable}
    if not email:
        return {"success": False, "error": "no_paypal_email", "amount_usd": amount,
                "hint": "Set EXCHANGE_PAYOUT_PAYPAL_EMAIL to off-ramp to fiat."}

    payout_ref: Dict[str, Any] = {}
    do_live = bool(live and paypal_live)
    if do_live:
        try:
            from backend.services.paypal_service import create_payout
            payout_ref = create_payout(email, amount,
                                       note=f"MasterNoder pool fiat cash-out ({target_fiat})")
        except Exception as exc:
            return {"success": False, "error": "paypal_error", "detail": str(exc)}
        if not payout_ref.get("success"):
            return {"success": False, "error": payout_ref.get("error", "paypal_payout_failed")}

    with ex._LOCK:
        cur = float((ex.get_wallet(pool_uid).get("assets") or {}).get(stable) or 0)
        debit = min(amount, round(cur, 8))
        if debit > 0:
            ex._adjust_balance(pool_uid, stable, -debit)

    row = {
        "ts": _iso(), "phase": "offramp", "rail": "paypal", "stable": stable,
        "fiat": target_fiat, "receiver_email": email, "amount_usd": amount,
        "mode": "live" if do_live else "paper",
        "payout_batch_id": payout_ref.get("payout_batch_id"),
    }
    ex._append_jsonl(_CONV_LEDGER_PATH, row)
    ex._audit("fiat_convert_offramp", user_id="owner", stable=stable, fiat=target_fiat,
              amount_usd=amount, mode=row["mode"])
    return {
        "success": True,
        "rail": "paypal",
        "amount_usd": amount,
        "fiat": target_fiat,
        "receiver_email": email,
        "mode": "live" if do_live else "paper",
        "payout": payout_ref or None,
        "note": (None if do_live else
                 "Paper off-ramp: recorded only. Set EXCHANGE_PAYOUT_PAYPAL_LIVE=1 to send a real PayPal payout."),
    }


def conversion_history(limit: int = 20) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    if os.path.isfile(_CONV_LEDGER_PATH):
        try:
            import json
            with open(_CONV_LEDGER_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        except Exception:
            pass
    return {"success": True, "count": len(rows), "conversions": rows[-int(limit or 20):][::-1]}


def fiat_converter_status() -> Dict[str, Any]:
    val = pool_valuation()
    plan = plan_fiat_conversion(venue="binance", target="USD")
    return {
        "success": True,
        "valuation": val,
        "live_enabled": fiat_convert_live_enabled(),
        "default_plan": {
            "venue": plan["venue"],
            "target": plan["target"],
            "est_total_stable_usd": plan["est_total_stable_usd"],
            "est_fees_usd": plan["est_fees_usd"],
            "sell_leg_count": len(plan["sell_legs"]),
            "offramp": plan.get("offramp"),
            "actionable": plan["actionable"],
        },
    }
