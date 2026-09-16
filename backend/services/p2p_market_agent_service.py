"""
Autonomous P2P market demo — seeds p2p_agent_* users, maintains open listings,
and simulates trades on cron (no PayPal). Powers /market/ P2P chips with live data.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENT_COUNT = 10
AGENT_PREFIX = "p2p_agent_"
TARGET_OPEN_LISTINGS = 10
MIN_AGENT_MN2 = 250.0
LISTING_MN2_CHOICES = (15.0, 20.0, 25.0, 30.0, 40.0, 50.0)
TIER_TARGETS = {
    "budget": 0.05,
    "mid": 0.25,
    "premium": 0.75,
}


def _agent_ids() -> List[str]:
    return [f"{AGENT_PREFIX}{i:02d}" for i in range(1, AGENT_COUNT + 1)]


def _tier_for_index(i: int) -> str:
    tiers = ("budget", "mid", "premium")
    return tiers[i % len(tiers)]


def _price_for_tier(tier: str) -> float:
    """Pick a listing price inside the oracle corridor when possible."""
    target = float(TIER_TARGETS.get(tier, TIER_TARGETS["mid"]))
    try:
        from backend.services.mn2_p2p_oracle import get_corridor
        corridor = get_corridor()
    except Exception:
        corridor = {}
    if not corridor.get("oracle_available"):
        return round(target, 8)
    lo = float(corridor["min_price_usd_per_mn2"])
    hi = float(corridor["max_price_usd_per_mn2"])
    oracle = float(corridor["oracle_usd_per_mn2"])
    if lo <= target <= hi:
        return round(target, 8)
    if target < lo:
        return round(lo + (hi - lo) * 0.15, 8)
    if target > hi:
        return round(hi - (hi - lo) * 0.15, 8)
    return round(oracle, 8)


def _ensure_verified(user_id: str) -> bool:
    try:
        from backend.services.mn2_verification import add_verified, is_verified
        if is_verified(user_id):
            return False
        add_verified(user_id)
        return True
    except Exception:
        return False


def _ensure_balance(user_id: str, floor: float = MIN_AGENT_MN2) -> float:
    """Top up agent MN2 balance to floor. Returns amount credited."""
    try:
        from backend.services.unified_points_database import unified_points_db
        res = unified_points_db.get_all_points(user_id)
        bal = float((res.get("points") or {}).get("mn2_balance", 0) or 0)
        if bal >= floor:
            return 0.0
        delta = round(floor - bal, 8)
        unified_points_db.add_points(user_id, "mn2_balance", delta, source="p2p_agent_bankroll")
        return delta
    except Exception:
        return 0.0


def _open_listings_for_agent(seller_id: str) -> List[Dict[str, Any]]:
    import backend.services.mn2_p2p_service as p2p
    rows = []
    for l in p2p._read(p2p._LISTINGS_FILE).values():
        if l.get("seller_id") == seller_id and l.get("status") == "open":
            rows.append(l)
    return rows


def _all_open_listings() -> List[Dict[str, Any]]:
    import backend.services.mn2_p2p_service as p2p
    return [l for l in p2p._read(p2p._LISTINGS_FILE).values() if l.get("status") == "open"]


def _record_activity(action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        from backend.services.agent_db_service import agent_db_service
        agent_db_service.record_agent_activity(
            user_id="platform_p2p",
            agent_id="workflow_agent",
            action=action,
            skill="p2p_market",
            xp_gained=2,
            metadata={"cron": True, **(metadata or {})},
        )
    except Exception:
        pass


def ensure_agents(*, target_listings: int = TARGET_OPEN_LISTINGS) -> Dict[str, Any]:
    """Verify agents, fund wallets, and create listings until target count is met."""
    import backend.services.mn2_p2p_service as p2p

    cfg = p2p.get_config()
    if not cfg.get("enabled"):
        return {"success": False, "skipped": "p2p_disabled"}

    verified = 0
    funded = 0
    created = 0
    errors: List[str] = []
    agents = _agent_ids()

    for uid in agents:
        if _ensure_verified(uid):
            verified += 1
        credited = _ensure_balance(uid)
        if credited > 0:
            funded += 1

    open_rows = _all_open_listings()
    agent_open = [l for l in open_rows if p2p.is_agent_user(l.get("seller_id", ""))]
    need = max(0, target_listings - len(agent_open))

    for i, uid in enumerate(agents):
        if need <= 0:
            break
        if len(_open_listings_for_agent(uid)) >= int(cfg.get("max_open_listings_per_seller", 5)):
            continue
        tier = _tier_for_index(i)
        price = _price_for_tier(tier)
        mn2_amt = LISTING_MN2_CHOICES[i % len(LISTING_MN2_CHOICES)]
        res = p2p.create_listing(uid, mn2_amt, price)
        if res.get("success"):
            created += 1
            need -= 1
        else:
            err = str(res.get("error") or "create_listing_failed")
            if err not in errors:
                errors.append(f"{uid}:{err}"[:120])

    return {
        "success": True,
        "agent_count": len(agents),
        "verified_added": verified,
        "funded_agents": funded,
        "listings_created": created,
        "open_agent_listings": len([l for l in _all_open_listings() if p2p.is_agent_user(l.get("seller_id", ""))]),
        "errors": errors[:5],
    }


def _pick_trade_pair(listings: List[Dict[str, Any]]) -> Optional[Tuple[str, str, float]]:
    """Return (buyer_id, listing_id, mn2_amount) or None."""
    import backend.services.mn2_p2p_service as p2p

    candidates = [
        l for l in listings
        if p2p.is_agent_user(l.get("seller_id", ""))
        and float(l.get("mn2_available", 0) or 0) >= 5.0
    ]
    if not candidates:
        return None
    listing = random.choice(candidates)
    seller = str(listing.get("seller_id") or "")
    buyers = [u for u in _agent_ids() if u != seller]
    if not buyers:
        return None
    buyer = random.choice(buyers)
    available = float(listing.get("mn2_available", 0) or 0)
    price = float(listing.get("price_usd_per_mn2", 0) or 0)
    # Ensure order total >= $1.00 after spread
    min_mn2 = max(5.0, round(1.05 / max(price * 1.02, 0.0001), 2))
    trade_mn2 = min(available, max(min_mn2, round(available * 0.35, 2)))
    if trade_mn2 < min_mn2 or trade_mn2 > available:
        trade_mn2 = min(available, max(min_mn2, 10.0))
    if trade_mn2 <= 0 or trade_mn2 * price < 0.99:
        return None
    return buyer, str(listing.get("listing_id") or ""), round(trade_mn2, 8)


def simulate_trades(*, max_trades: int = 2) -> Dict[str, Any]:
    """Run up to max_trades agent-to-agent simulated purchases."""
    import backend.services.mn2_p2p_service as p2p

    if not p2p.get_config().get("enabled"):
        return {"success": False, "skipped": "p2p_disabled"}

    p2p.clear_matured()
    trades: List[Dict[str, Any]] = []
    errors: List[str] = []

    for _ in range(max(1, min(max_trades, 5))):
        listings = _all_open_listings()
        pair = _pick_trade_pair(listings)
        if not pair:
            break
        buyer, listing_id, mn2_amt = pair
        res = p2p.agent_simulate_purchase(buyer, listing_id, mn2_amt)
        if res.get("success"):
            trades.append({
                "buyer": buyer,
                "listing_id": listing_id,
                "mn2_amount": mn2_amt,
                "order_id": res.get("order_id"),
                "usd_amount": res.get("usd_amount"),
            })
            _record_activity("p2p_agent_trade", metadata=trades[-1])
        else:
            err = str(res.get("error") or "trade_failed")
            if err not in errors:
                errors.append(err[:120])

    return {
        "success": True,
        "trades": len(trades),
        "trade_details": trades,
        "open_listings": len(_all_open_listings()),
        "errors": errors[:5],
    }


def run_p2p_market_agent_job(
    *,
    target_listings: int = TARGET_OPEN_LISTINGS,
    max_trades: int = 2,
) -> Dict[str, Any]:
    """Cron entry: seed agents/listings then simulate trades."""
    seed = ensure_agents(target_listings=target_listings)
    trade = simulate_trades(max_trades=max_trades)
    out = {
        "success": seed.get("success") and trade.get("success"),
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "trade": trade,
    }
    if seed.get("errors") or trade.get("errors"):
        out["errors"] = {
            "seed": seed.get("errors") or [],
            "trade": trade.get("errors") or [],
        }
    return out
