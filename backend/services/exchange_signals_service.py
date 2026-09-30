"""Cross-trade signal feed — the site's profit daemon publishes trade signals that a remote
client (e.g. the laptop trader app) polls and executes where its IP can reach the venues.

Signals are advisory: cross-venue arbitrage spreads, grid market-making candidates, and
rebalance hints. Each carries a machine-usable ``action`` so the client can act on it.
Read-only: this module computes signals from live/cached market data and never places orders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _arb_signals(min_net_bps: float, limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from backend.services.exchange_arbitrage_service import scan_opportunities
        scan = scan_opportunities()
        opps = scan.get("opportunities") or []
        for o in opps:
            if not isinstance(o, dict):
                continue
            net = float(o.get("net_bps") or 0)
            if net < min_net_bps:
                continue
            buy_v = str(o.get("buy_venue") or "")
            sell_v = str(o.get("sell_venue") or "")
            # Only real external routes are actionable by the client (skip internal/simulated).
            actionable = buy_v not in ("", "internal") and sell_v not in ("", "internal")
            out.append({
                "type": "arbitrage",
                "symbol": o.get("symbol"),
                "buy_venue": buy_v,
                "sell_venue": sell_v,
                "net_bps": round(net, 2),
                "notional_usd": o.get("notional_usd"),
                "actionable": actionable,
                "action": {"kind": "spatial_arb", "symbol": o.get("symbol"),
                           "buy_venue": buy_v, "sell_venue": sell_v} if actionable else None,
                "note": None if actionable else "internal/simulated leg — informational only",
            })
    except Exception as exc:
        out.append({"type": "arbitrage", "error": str(exc)})
    out = [s for s in out if not s.get("error")]
    out.sort(key=lambda s: s.get("net_bps", 0), reverse=True)
    return out[:limit]


def _grid_signals(limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from backend.services import exchange_grid_bot_service as grid
        from backend.services import external_exchange_connector_service as conn
        cfg = grid.load_config()
        venue = str(cfg.get("venue") or "binance")
        candidates = []
        for sym in (cfg.get("assets") or []):
            tick = conn.fetch_ticker(venue, str(sym), timeout=4.0)
            if not tick:
                continue
            candidates.append({"symbol": str(sym).upper(),
                               "bid": float(tick.get("bid") or 0),
                               "ask": float(tick.get("ask") or 0),
                               "vol_pct": float(tick.get("vol_pct") or cfg.get("min_vol_pct") or 0)})
        for c in grid.select_assets(candidates, cfg):
            out.append({
                "type": "grid",
                "symbol": c["symbol"],
                "venue": venue,
                "spread_bps": c.get("spread_bps"),
                "mid": c.get("mid"),
                "actionable": True,
                "action": {"kind": "grid", "venue": venue, "symbol": c["symbol"]},
            })
    except Exception as exc:
        out.append({"type": "grid", "error": str(exc)})
    out = [s for s in out if not s.get("error")]
    return out[:limit]


def account_balances(venues: Optional[List[str]] = None) -> Dict[str, Any]:
    """Per-venue spot balances with USD value (real when the caller's IP can read them)."""
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_venue_api_service as vapi

    # Default set includes venues the app supports; a venue with no creds is shown as such.
    # Auto-include XeggeX only when it has credentials, to avoid noise for users who don't use it.
    if not venues:
        from backend.services import exchange_venue_api_service as vapi
        venues = ["binance", "nonkyc"]
        try:
            if vapi.venue_has_credentials("xeggex"):
                venues.append("xeggex")
        except Exception:
            pass
    venues = [str(v).lower() for v in venues]
    out: Dict[str, Any] = {"success": True, "generated_at": _iso(), "venues": {}, "total_usd": 0.0}
    grand = 0.0
    for v in venues:
        row: Dict[str, Any] = {"assets": [], "usd_total": 0.0}
        try:
            if not vapi.venue_has_credentials(v):
                # Binance keys may live in env rather than the vault.
                if v == "binance":
                    from backend.services.exchange_binance_withdraw_service import binance_credentials
                    c = binance_credentials()
                    has = bool(c.get("api_key") and c.get("api_secret"))
                else:
                    has = False
            else:
                has = True
            if not has:
                row["error"] = "no_credentials"
                out["venues"][v] = row
                continue
            bals = vapi.parse_spot_balances(v, dry_run=False) or {}
            if not bals:
                # Distinguish "read failed" (auth/IP/region) from "genuinely empty" so a $0
                # balance is never silent. parse_spot_balances swallows API errors -> re-read raw.
                raw = vapi.get_account_balance(v, dry_run=False)
                if raw.get("simulated"):
                    row["note"] = "paper mode (no live credentials/gate)"
                elif not raw.get("success"):
                    row["note"] = vapi.extract_order_error(raw) or "balance read failed"
                    row["http_status"] = raw.get("status_code")
                    row["read_ok"] = False
                else:
                    row["note"] = "no positive spot balances on this account/wallet"
            vtot = 0.0
            for sym, amt in bals.items():
                amount = float(amt or 0)
                if amount <= 0:
                    continue
                price = float(ex._price_usd(str(sym).upper()) or 0)
                usd = round(amount * price, 4)
                vtot += usd
                row["assets"].append({"symbol": str(sym).upper(), "amount": round(amount, 8),
                                      "price_usd": round(price, 8), "usd_value": usd})
            row["assets"].sort(key=lambda r: r["usd_value"], reverse=True)
            row["usd_total"] = round(vtot, 4)
            grand += vtot
        except Exception as exc:
            row["error"] = str(exc)
        out["venues"][v] = row
    out["total_usd"] = round(grand, 4)
    return out


def get_signals(*, min_net_bps: float = 5.0, limit: int = 25) -> Dict[str, Any]:
    """Aggregate current cross-trade signals for remote clients."""
    arb = _arb_signals(min_net_bps, limit)
    grid = _grid_signals(limit)
    signals = arb + grid
    return {
        "success": True,
        "generated_at": _iso(),
        "min_net_bps": min_net_bps,
        "counts": {"arbitrage": len(arb), "grid": len(grid), "actionable": sum(1 for s in signals if s.get("actionable"))},
        "signals": signals,
    }
