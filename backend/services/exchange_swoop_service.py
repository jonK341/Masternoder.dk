"""MN2 / USDT / USDC swoop — guided swaps between pool assets.

Maps a simple from/to/amount request onto the existing swap engine (symbol, side, quote).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_SWOOP_ASSETS = frozenset({"MN2", "USDT", "USDC"})


def swoop_assets() -> list:
    return sorted(_SWOOP_ASSETS)


def resolve_swoop(from_asset: str, to_asset: str, amount: float) -> Dict[str, Any]:
    """Map swoop legs to swap symbol, side, quote, and amount."""
    src = (from_asset or "").strip().upper()
    dst = (to_asset or "").strip().upper()
    amt = float(amount or 0)

    if src not in _SWOOP_ASSETS or dst not in _SWOOP_ASSETS:
        return {"success": False, "error": "invalid_swoop_asset"}
    if src == dst:
        return {"success": False, "error": "same_asset"}
    if amt <= 0:
        return {"success": False, "error": "invalid_amount"}

    symbol, side, quote = _map_legs(src, dst)
    return {
        "success": True,
        "from_asset": src,
        "to_asset": dst,
        "amount": amt,
        "symbol": symbol,
        "side": side,
        "quote": quote,
    }


def _map_legs(src: str, dst: str) -> Tuple[str, str, str]:
    """Return (symbol, side, quote) for spending src to receive dst."""
    if src == "MN2" and dst in ("USDT", "USDC"):
        return "MN2", "sell", dst
    if src in ("USDT", "USDC") and dst == "MN2":
        return src, "sell", "MN2"
    if src == "USDT" and dst == "USDC":
        return "USDC", "buy", "USDT"
    if src == "USDC" and dst == "USDT":
        return "USDT", "buy", "USDC"
    raise ValueError(f"unsupported_swoop:{src}->{dst}")


def _receive_amount(quote_payload: Dict[str, Any]) -> float:
    side = str(quote_payload.get("side") or "").lower()
    if side == "buy":
        return float(quote_payload.get("amount") or 0)
    return float(quote_payload.get("quote_received") or 0)


def quote_swoop(user_id: str, from_asset: str, to_asset: str, amount: float) -> Dict[str, Any]:
    resolved = resolve_swoop(from_asset, to_asset, amount)
    if not resolved.get("success"):
        return resolved

    q = ex.quote_swap(
        user_id,
        resolved["symbol"],
        resolved["side"],
        resolved["amount"],
        resolved["quote"],
    )
    if not q.get("success"):
        return q

    q["swoop"] = True
    q["from_asset"] = resolved["from_asset"]
    q["to_asset"] = resolved["to_asset"]
    q["from_amount"] = resolved["amount"]
    q["to_amount"] = round(_receive_amount(q), 12)
    return q


def execute_swoop(
    user_id: str,
    from_asset: str,
    to_asset: str,
    amount: float,
    quote_id: str = "",
) -> Dict[str, Any]:
    q = quote_swoop(user_id, from_asset, to_asset, amount)
    if not q.get("success"):
        return q

    res = ex.execute_swap(
        user_id,
        quote_id or q.get("quote_id") or "",
        q["symbol"],
        q["side"],
        float(q["amount"]),
        q["quote_currency"],
    )
    if not res.get("success"):
        return res

    res["swoop"] = True
    res["from_asset"] = q["from_asset"]
    res["to_asset"] = q["to_asset"]
    res["from_amount"] = q["from_amount"]
    res["to_amount"] = q["to_amount"]
    res["pool_backed"] = q.get("pool_backed")
    res["pool_reserve_quote"] = q.get("pool_reserve_quote")
    res["pool_reserve_bps"] = q.get("pool_reserve_bps")
    res["pool_reserve_currency"] = q.get("pool_reserve_currency")
    return res


def swoop_balance_hint(wallet: Dict[str, Any], asset: str) -> float:
    sym = (asset or "").strip().upper()
    if sym == "MN2":
        return float(wallet.get("mn2_balance") or 0)
    assets = wallet.get("assets") if isinstance(wallet.get("assets"), dict) else {}
    return float(assets.get(sym) or 0)
