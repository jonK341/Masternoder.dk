"""
Shop V9.2 monetization service.

Implements the revenue mechanics layered on top of the existing Shop V.9 catalog:

  * VIP Pass         — 30-day membership: daily coin claim, catalog discount, free spins.
  * Mystery Boxes    — weighted loot crates paid in coins or MN2.
  * Spin the Wheel   — 1 free daily spin (more for VIP) + paid extra spins.
  * Flash Sales      — time-boxed, deterministic rotating discounts.
  * Gifting          — send coins to another profile.
  * Loyalty/Cashback — earn loyalty points on monetization spend, redeem for rewards.
  * Featured Auction — pay coins to promote an auction listing to the top.

State persists as a single JSON document under logs/shop_monetization/state.json so the
features work even when shop DB migrations have not been applied (same pattern as
shop_db_service file mode and shop_auction_service). All balance changes go through
unified_points_db so coins/MN2 stay consistent with the rest of the platform.
"""
from __future__ import annotations

import hashlib
import os
import random
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()
_FILENAME = "state.json"


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _log_root() -> str:
    base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    root = os.path.join(base, "shop_monetization")
    os.makedirs(root, exist_ok=True)
    return root


def _state_path() -> str:
    return os.path.join(_log_root(), _FILENAME)


def _empty_state() -> Dict[str, Any]:
    return {"vip": {}, "spins": {}, "loyalty": {}, "gifts": [], "auction_features": {}, "top25": {}}


def _load_state() -> Dict[str, Any]:
    import json

    path = _state_path()
    with _LOCK:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    base = _empty_state()
                    base.update({k: data.get(k, base[k]) for k in base})
                    return base
            except Exception:
                pass
        return _empty_state()


def _save_state(state: Dict[str, Any]) -> None:
    import json

    path = _state_path()
    with _LOCK:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def get_config() -> Dict[str, Any]:
    """shop_monetization block from monetization_config.json (empty dict if unavailable)."""
    try:
        from backend.services.monetization_config_service import get_shop_monetization

        return get_shop_monetization() or {}
    except Exception:
        return {}


def _booster_sku_map() -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.monetization_config_service import _load_raw

        cfg = _load_raw() or {}
        return {s.get("id"): s for s in (cfg.get("shop_booster_skus") or []) if s.get("id")}
    except Exception:
        return {}


def _catalog_item_name(item_id: str) -> str:
    try:
        from backend.routes.shop_routes import _get_shop_items

        for it in _get_shop_items() or []:
            if it.get("id") == item_id:
                return it.get("name") or item_id
    except Exception:
        pass
    return item_id


# ---------------------------------------------------------------------------
# Points helpers (all balance changes funnel through unified_points_db)
# ---------------------------------------------------------------------------

def _points_db():
    from backend.services.unified_points_database import unified_points_db

    return unified_points_db


def _coin_balance(user_id: str) -> int:
    try:
        snap = _points_db().get_all_points(user_id)
        if snap and snap.get("success"):
            return int((snap.get("points") or {}).get("coins", 0) or 0)
    except Exception:
        pass
    return 0


def _mn2_balance(user_id: str) -> float:
    try:
        snap = _points_db().get_all_points(user_id)
        pts = (snap or {}).get("points") or {}
        bal = float(pts.get("mn2_balance", 0) or 0)
        if bal == 0 and isinstance(pts.get("systems"), dict):
            bal = float(pts["systems"].get("mn2_balance", 0) or 0)
        return bal
    except Exception:
        return 0.0


def _coins_per_mn2() -> float:
    import json

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        with open(os.path.join(base, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            return float(json.load(f).get("coins_per_mn2") or 100)
    except Exception:
        return 100.0


def _charge(user_id: str, coins: int, *, payment_method: str, source: str, metadata: Dict[str, Any]) -> Tuple[bool, str]:
    """Debit a coin-priced cost via coins or MN2. Returns (ok, error)."""
    coins = int(coins or 0)
    if coins <= 0:
        return True, ""
    method = (payment_method or "coins").strip().lower()
    db = _points_db()
    if method == "mn2":
        cpm = _coins_per_mn2()
        if cpm <= 0:
            return False, "MN2 pricing not configured"
        price_mn2 = coins / cpm
        if _mn2_balance(user_id) < price_mn2:
            return False, f"Insufficient MN2. Need {price_mn2:.8f}"
        res = db.add_points(user_id=user_id, point_type="mn2_balance", amount=-price_mn2,
                            source=source + "_mn2", metadata=metadata)
        return bool(res.get("success", True)), "" if res.get("success", True) else "MN2 debit failed"
    if _coin_balance(user_id) < coins:
        return False, f"Insufficient coins. Need {coins}"
    res = db.add_points(user_id=user_id, point_type="coins", amount=-coins, source=source, metadata=metadata)
    return bool(res.get("success", True)), "" if res.get("success", True) else "Coin debit failed"


def _grant(user_id: str, grant: Dict[str, Any], *, source: str) -> Dict[str, Any]:
    """Apply a single reward grant. Returns a small descriptor of what was granted."""
    gtype = (grant.get("type") or "coins").strip().lower()
    label = grant.get("label") or ""
    db = _points_db()
    if gtype == "coins":
        amount = int(grant.get("amount") or 0)
        if amount > 0:
            db.add_points(user_id=user_id, point_type="coins", amount=amount, source=source,
                          metadata={"grant": grant})
        return {"type": "coins", "amount": amount, "label": label or f"{amount} coins"}
    if gtype == "loyalty":
        amount = int(grant.get("amount") or 0)
        if amount > 0:
            _add_loyalty_points(user_id, amount, source=source)
        return {"type": "loyalty", "amount": amount, "label": label or f"{amount} loyalty"}
    if gtype == "mn2":
        amount = float(grant.get("amount") or 0)
        if amount > 0:
            try:
                from backend.services.shop_mn2_fulfillment_service import fulfill_mn2_purchase

                fulfill_mn2_purchase(
                    user_id,
                    grant.get("ref") or f"grant:{source}",
                    1,
                    source=source,
                    reference=f"{source}:{grant.get('ref') or 'mn2'}:{amount}",
                    metadata={"grant": grant},
                    item={"mn2_granted": amount},
                )
            except Exception:
                pass
        return {"type": "mn2", "amount": amount, "label": label or f"{amount} MN2"}
    if gtype == "game_time":
        minutes = int(grant.get("minutes") or grant.get("amount") or 0)
        if minutes > 0:
            db.add_game_time_minutes(user_id, minutes)
        return {"type": "game_time", "minutes": minutes, "label": label or f"+{minutes}m game time"}
    if gtype == "booster":
        ref = grant.get("ref") or ""
        sku = _booster_sku_map().get(ref) or {}
        minutes = int(sku.get("duration_minutes") or grant.get("duration_minutes") or 60)
        name = sku.get("name") or grant.get("label") or ref
        if (sku.get("effect") or "booster").lower() == "game_time":
            db.add_game_time_minutes(user_id, minutes)
        else:
            db.add_booster(user_id, ref or "booster", minutes, name=name)
        return {"type": "booster", "ref": ref, "minutes": minutes, "label": label or name}
    if gtype == "item":
        ref = grant.get("ref") or ""
        name = grant.get("label") or _catalog_item_name(ref)
        try:
            from backend.services.shop_db_service import add_to_inventory

            add_to_inventory(user_id, ref, name, int(grant.get("quantity") or 1))
        except Exception:
            pass
        return {"type": "item", "ref": ref, "label": name}
    return {"type": "nothing", "label": label or "No win"}


def _weighted_pick(entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    pool = [e for e in entries if isinstance(e, dict) and float(e.get("weight") or 0) > 0]
    if not pool:
        return entries[0] if entries else None
    total = sum(float(e.get("weight") or 0) for e in pool)
    roll = random.uniform(0, total)
    cum = 0.0
    for e in pool:
        cum += float(e.get("weight") or 0)
        if roll <= cum:
            return e
    return pool[-1]


# ---------------------------------------------------------------------------
# VIP Pass
# ---------------------------------------------------------------------------

def _vip_cfg() -> Dict[str, Any]:
    return get_config().get("vip_pass") or {}


def get_vip_status(user_id: str) -> Dict[str, Any]:
    cfg = _vip_cfg()
    state = _load_state()
    rec = (state.get("vip") or {}).get(user_id) or {}
    expires = _parse_iso(rec.get("expires_at"))
    active = bool(expires and expires > _now())
    days_remaining = int((expires - _now()).total_seconds() // 86400) + 1 if active else 0
    last_daily = _parse_iso(rec.get("last_daily_at"))
    can_claim_daily = active and (last_daily is None or last_daily.date() < _now().date())
    return {
        "active": active,
        "expires_at": rec.get("expires_at") if active else None,
        "days_remaining": days_remaining,
        "discount_pct": int(cfg.get("discount_pct") or 0) if active else 0,
        "daily_coins": int(cfg.get("daily_coins") or 0),
        "can_claim_daily": can_claim_daily,
        "badge": cfg.get("badge") if active else None,
        "perks": cfg.get("perks") or [],
        "free_spins_per_day": int(cfg.get("vip_free_spins_per_day") or 0) if active else 0,
    }


def activate_vip(user_id: str, *, days: Optional[int] = None, source: str = "vip_purchase") -> Dict[str, Any]:
    """Start or extend a VIP membership. Called by shop purchase fulfillment."""
    cfg = _vip_cfg()
    days = int(days or cfg.get("duration_days") or 30)
    with _LOCK:
        state = _load_state()
        vip = state.setdefault("vip", {})
        rec = vip.get(user_id) or {}
        current = _parse_iso(rec.get("expires_at"))
        start = current if (current and current > _now()) else _now()
        rec["expires_at"] = _iso(start + timedelta(days=days))
        rec["activated_at"] = _iso(_now())
        rec["source"] = source
        vip[user_id] = rec
        _save_state(state)
    return get_vip_status(user_id)


def claim_vip_daily(user_id: str) -> Dict[str, Any]:
    cfg = _vip_cfg()
    status = get_vip_status(user_id)
    if not status.get("active"):
        return {"success": False, "error": "VIP membership is not active"}
    if not status.get("can_claim_daily"):
        return {"success": False, "error": "Daily reward already claimed today"}
    coins = int(cfg.get("daily_coins") or 0)
    with _LOCK:
        state = _load_state()
        rec = (state.get("vip") or {}).get(user_id) or {}
        rec["last_daily_at"] = _iso(_now())
        state.setdefault("vip", {})[user_id] = rec
        _save_state(state)
    if coins > 0:
        _grant(user_id, {"type": "coins", "amount": coins}, source="vip_daily_claim")
    return {"success": True, "coins_granted": coins, "vip": get_vip_status(user_id)}


def _vip_discount_pct(user_id: str) -> int:
    return int(get_vip_status(user_id).get("discount_pct") or 0)


def _apply_vip_discount(user_id: str, price_coins: int) -> int:
    pct = _vip_discount_pct(user_id)
    if pct <= 0:
        return int(price_coins)
    return max(1, int(round(price_coins * (1 - pct / 100.0))))


# ---------------------------------------------------------------------------
# Mystery boxes
# ---------------------------------------------------------------------------

def list_mystery_boxes(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    boxes = get_config().get("mystery_boxes") or []
    out = []
    for box in boxes:
        if not isinstance(box, dict) or not box.get("id"):
            continue
        base_price = int(box.get("price_coins") or 0)
        loot = box.get("loot") or []
        total_w = sum(float(l.get("weight") or 0) for l in loot) or 1.0
        odds = [
            {"label": l.get("label") or l.get("type"), "chance_pct": round(100 * float(l.get("weight") or 0) / total_w, 1)}
            for l in loot
        ]
        row = {
            "id": box.get("id"),
            "name": box.get("name") or box.get("id"),
            "description": box.get("description") or "",
            "icon": box.get("icon") or "📦",
            "rarity": box.get("rarity") or "common",
            "price_coins": base_price,
            "price_usd": float(box.get("price_usd") or 0),
            "odds": odds,
        }
        if user_id:
            row["effective_price_coins"] = _apply_vip_discount(user_id, base_price)
        out.append(row)
    return out


def open_mystery_box(user_id: str, box_id: str, *, payment_method: str = "coins") -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "Create or log in to a profile before opening boxes"}
    box = next((b for b in (get_config().get("mystery_boxes") or []) if b.get("id") == box_id), None)
    if not box:
        return {"success": False, "error": f"Mystery box {box_id} not found"}
    price = _apply_vip_discount(uid, int(box.get("price_coins") or 0))
    ok, err = _charge(uid, price, payment_method=payment_method, source="mystery_box",
                      metadata={"box_id": box_id})
    if not ok:
        return {"success": False, "error": err}
    prize = _weighted_pick(box.get("loot") or []) or {"type": "nothing"}
    reward = _grant(uid, prize, source=f"mystery_box:{box_id}")
    loyalty = _accrue_loyalty_for_spend(uid, price)
    return {
        "success": True,
        "box_id": box_id,
        "box_name": box.get("name") or box_id,
        "price_paid_coins": price,
        "payment_method": (payment_method or "coins").lower(),
        "reward": reward,
        "loyalty_earned": loyalty,
    }


# ---------------------------------------------------------------------------
# Spin the wheel
# ---------------------------------------------------------------------------

def _spin_cfg() -> Dict[str, Any]:
    return get_config().get("spin_wheel") or {}


def get_spin_status(user_id: str) -> Dict[str, Any]:
    cfg = _spin_cfg()
    cooldown_h = float(cfg.get("free_cooldown_hours") or 24)
    state = _load_state()
    rec = (state.get("spins") or {}).get(user_id) or {}
    last_free = _parse_iso(rec.get("last_free_at"))
    vip = get_vip_status(user_id)
    vip_free = int(cfg.get("vip_free_spins_per_day") or 0) if vip.get("active") else 0
    free_used_today = int(rec.get("free_used_today") or 0) if (last_free and last_free.date() == _now().date()) else 0
    free_allow = 1 + vip_free
    free_available = free_used_today < free_allow
    next_free = None
    if not free_available and last_free:
        nf = last_free + timedelta(hours=cooldown_h)
        next_free = _iso(nf)
    return {
        "free_available": free_available,
        "free_spins_per_day": free_allow,
        "free_used_today": free_used_today,
        "spin_cost_coins": int(cfg.get("spin_cost_coins") or 0),
        "next_free_at": next_free,
        "prizes": [{"label": p.get("label"), "type": p.get("type")} for p in (cfg.get("prizes") or [])],
        "vip_active": bool(vip.get("active")),
    }


def spin_wheel(user_id: str, *, paid: bool = False, payment_method: str = "coins") -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "Create or log in to a profile before spinning"}
    cfg = _spin_cfg()
    prizes = cfg.get("prizes") or []
    if not prizes:
        return {"success": False, "error": "Spin wheel is not configured"}
    status = get_spin_status(uid)
    price_paid = 0
    used_free = False
    if not paid and status.get("free_available"):
        used_free = True
    else:
        price = int(cfg.get("spin_cost_coins") or 0)
        ok, err = _charge(uid, price, payment_method=payment_method, source="spin_wheel",
                          metadata={"paid": True})
        if not ok:
            return {"success": False, "error": err}
        price_paid = price
    if used_free:
        with _LOCK:
            state = _load_state()
            spins = state.setdefault("spins", {})
            rec = spins.get(uid) or {}
            last_free = _parse_iso(rec.get("last_free_at"))
            if last_free and last_free.date() == _now().date():
                rec["free_used_today"] = int(rec.get("free_used_today") or 0) + 1
            else:
                rec["free_used_today"] = 1
            rec["last_free_at"] = _iso(_now())
            spins[uid] = rec
            _save_state(state)
    prize = _weighted_pick(prizes) or {"type": "nothing"}
    reward = _grant(uid, prize, source="spin_wheel")
    loyalty = _accrue_loyalty_for_spend(uid, price_paid) if price_paid else {"earned": 0}
    return {
        "success": True,
        "free_spin": used_free,
        "price_paid_coins": price_paid,
        "reward": reward,
        "loyalty_earned": loyalty,
        "status": get_spin_status(uid),
    }


# ---------------------------------------------------------------------------
# Flash sales (deterministic rotating discounts)
# ---------------------------------------------------------------------------

def get_flash_sales() -> Dict[str, Any]:
    cfg = get_config().get("flash_sales") or {}
    count = int(cfg.get("count") or 3)
    min_d = int(cfg.get("min_discount") or 20)
    max_d = int(cfg.get("max_discount") or 50)
    rotate_h = max(1, int(cfg.get("rotate_hours") or 6))
    min_price = int(cfg.get("min_price_coins") or 30)
    try:
        from backend.routes.shop_routes import _get_shop_items

        items = [
            i for i in (_get_shop_items() or [])
            if isinstance(i.get("price"), (int, float)) and int(i.get("price") or 0) >= min_price
        ]
    except Exception:
        items = []
    if not items:
        return {"sales": [], "rotates_at": None, "window": None}
    now = _now()
    window = int(now.timestamp() // (rotate_h * 3600))
    rotates_at = _iso(datetime.fromtimestamp((window + 1) * rotate_h * 3600, tz=timezone.utc))
    sales: List[Dict[str, Any]] = []
    used = set()
    for n in range(min(count, len(items))):
        seed = f"flash:{window}:{n}"
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        idx = h % len(items)
        for _ in range(len(items)):
            if idx not in used:
                break
            idx = (idx + 1) % len(items)
        used.add(idx)
        item = items[idx]
        original = int(item.get("price") or 0)
        spread = max(0, max_d - min_d)
        discount = min_d + ((h >> 8) % (spread + 1))
        deal_price = max(1, int(round(original * (1 - discount / 100.0))))
        sales.append({
            "item_id": item.get("id"),
            "name": item.get("name"),
            "category": item.get("category"),
            "icon": item.get("icon") or "🛍️",
            "rarity": item.get("rarity") or "common",
            "original_price": original,
            "deal_price": deal_price,
            "discount_pct": discount,
        })
    return {"sales": sales, "rotates_at": rotates_at, "window": window}


# ---------------------------------------------------------------------------
# Gifting
# ---------------------------------------------------------------------------

def gift_coins(sender_id: str, recipient_id: str, coins: int, *, message: str = "") -> Dict[str, Any]:
    cfg = get_config().get("gifting") or {}
    min_c = int(cfg.get("min_coins") or 10)
    max_c = int(cfg.get("max_coins") or 100000)
    fee_pct = float(cfg.get("fee_pct") or 0)
    sender = (sender_id or "").strip()
    recipient = (recipient_id or "").strip()
    coins = int(coins or 0)
    if not sender or sender == "default_user":
        return {"success": False, "error": "Create or log in to a profile before gifting"}
    if not recipient or recipient == "default_user":
        return {"success": False, "error": "A valid recipient profile id is required"}
    if recipient == sender:
        return {"success": False, "error": "You cannot gift coins to yourself"}
    if coins < min_c:
        return {"success": False, "error": f"Minimum gift is {min_c} coins"}
    if coins > max_c:
        return {"success": False, "error": f"Maximum gift is {max_c} coins"}
    if _coin_balance(sender) < coins:
        return {"success": False, "error": f"Insufficient coins. Need {coins}"}
    db = _points_db()
    debit = db.add_points(user_id=sender, point_type="coins", amount=-coins, source="gift_sent",
                          metadata={"recipient_id": recipient, "message": message[:200]})
    if not debit.get("success", True):
        return {"success": False, "error": "Could not debit sender balance"}
    fee = int(round(coins * fee_pct / 100.0))
    net = max(0, coins - fee)
    credit = db.add_points(user_id=recipient, point_type="coins", amount=net, source="gift_received",
                           metadata={"sender_id": sender, "message": message[:200], "fee": fee})
    if not credit.get("success", True):
        db.add_points(user_id=sender, point_type="coins", amount=coins, source="gift_refund",
                      metadata={"recipient_id": recipient, "reason": "credit_failed"})
        return {"success": False, "error": "Could not deliver gift; coins were refunded"}
    record = {
        "sender_id": sender,
        "recipient_id": recipient,
        "coins": coins,
        "fee": fee,
        "net": net,
        "message": message[:200],
        "created_at": _iso(_now()),
    }
    with _LOCK:
        state = _load_state()
        gifts = state.setdefault("gifts", [])
        gifts.insert(0, record)
        state["gifts"] = gifts[:1000]
        _save_state(state)
    return {"success": True, "gift": record}


def list_gifts(user_id: str, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
    uid = (user_id or "").strip()
    state = _load_state()
    sent, received = [], []
    for g in state.get("gifts") or []:
        if not isinstance(g, dict):
            continue
        if g.get("sender_id") == uid:
            sent.append(g)
        if g.get("recipient_id") == uid:
            received.append(g)
    cap = max(1, min(int(limit or 50), 200))
    return {"sent": sent[:cap], "received": received[:cap]}


# ---------------------------------------------------------------------------
# Loyalty / cashback
# ---------------------------------------------------------------------------

def _loyalty_cfg() -> Dict[str, Any]:
    return get_config().get("loyalty") or {}


def _loyalty_tier(points: int) -> Dict[str, Any]:
    tiers = sorted(_loyalty_cfg().get("tiers") or [], key=lambda t: int(t.get("min_points") or 0))
    current = {"id": "bronze", "name": "Bronze", "min_points": 0, "cashback_pct": 0}
    nxt = None
    for t in tiers:
        if points >= int(t.get("min_points") or 0):
            current = t
        elif nxt is None:
            nxt = t
    return {"current": current, "next": nxt}


def _add_loyalty_points(user_id: str, points: int, *, source: str) -> int:
    points = int(points or 0)
    if points <= 0:
        return 0
    with _LOCK:
        state = _load_state()
        loy = state.setdefault("loyalty", {})
        rec = loy.get(user_id) or {"points": 0, "lifetime": 0}
        rec["points"] = int(rec.get("points") or 0) + points
        rec["lifetime"] = int(rec.get("lifetime") or 0) + points
        rec["updated_at"] = _iso(_now())
        loy[user_id] = rec
        _save_state(state)
    return points


def _accrue_loyalty_for_spend(user_id: str, coins_spent: int) -> Dict[str, Any]:
    cfg = _loyalty_cfg()
    coins_spent = int(coins_spent or 0)
    if coins_spent <= 0:
        return {"earned": 0}
    per_100 = float(cfg.get("earn_per_100_coins") or 0)
    base = int(coins_spent / 100.0 * per_100)
    # VIP and tier cashback bonus
    bonus_pct = 0
    tier = _loyalty_tier(get_loyalty(user_id)["points"]) if base else {"current": {}}
    bonus_pct += int((tier.get("current") or {}).get("cashback_pct") or 0)
    vip = get_vip_status(user_id)
    if vip.get("active"):
        bonus_pct += 5
    earned = int(round(base * (1 + bonus_pct / 100.0)))
    if earned > 0:
        _add_loyalty_points(user_id, earned, source="loyalty_cashback")
    return {"earned": earned, "base": base, "bonus_pct": bonus_pct}


def accrue_purchase_loyalty(user_id: str, coins_spent: int) -> Dict[str, Any]:
    """Public hook: award loyalty/cashback for a coin-priced shop purchase.

    Called from the main shop purchase flow so all coin spend (not just the V9.2
    mechanics) earns loyalty points. Safe to call with 0/invalid input.
    """
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"earned": 0}
    try:
        return _accrue_loyalty_for_spend(uid, int(coins_spent or 0))
    except Exception:
        return {"earned": 0}


def get_loyalty(user_id: str) -> Dict[str, Any]:
    state = _load_state()
    rec = (state.get("loyalty") or {}).get(user_id) or {"points": 0, "lifetime": 0}
    points = int(rec.get("points") or 0)
    tier = _loyalty_tier(points)
    return {
        "points": points,
        "lifetime": int(rec.get("lifetime") or 0),
        "tier": tier.get("current"),
        "next_tier": tier.get("next"),
        "earn_per_100_coins": float(_loyalty_cfg().get("earn_per_100_coins") or 0),
        "rewards": _loyalty_cfg().get("redeem") or [],
    }


def redeem_loyalty(user_id: str, reward_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "Create or log in to a profile before redeeming"}
    reward = next((r for r in (_loyalty_cfg().get("redeem") or []) if r.get("id") == reward_id), None)
    if not reward:
        return {"success": False, "error": f"Reward {reward_id} not found"}
    cost = int(reward.get("cost_points") or 0)
    current = get_loyalty(uid)["points"]
    if current < cost:
        return {"success": False, "error": f"Not enough loyalty points. Need {cost}, have {current}"}
    with _LOCK:
        state = _load_state()
        loy = state.setdefault("loyalty", {})
        rec = loy.get(uid) or {"points": 0, "lifetime": 0}
        if int(rec.get("points") or 0) < cost:
            return {"success": False, "error": "Not enough loyalty points"}
        rec["points"] = int(rec.get("points") or 0) - cost
        rec["updated_at"] = _iso(_now())
        loy[uid] = rec
        _save_state(state)
    granted = _grant(uid, reward.get("grant") or {}, source=f"loyalty_redeem:{reward_id}")
    return {"success": True, "reward_id": reward_id, "cost_points": cost, "granted": granted,
            "loyalty": get_loyalty(uid)}


# ---------------------------------------------------------------------------
# Featured auction listings
# ---------------------------------------------------------------------------

def _feature_cfg() -> Dict[str, Any]:
    return get_config().get("auction_feature") or {}


def feature_listing(user_id: str, listing_id: str, *, payment_method: str = "coins") -> Dict[str, Any]:
    uid = (user_id or "").strip()
    lid = (listing_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "Create or log in to a profile first"}
    if not lid:
        return {"success": False, "error": "listing_id is required"}
    # Verify the listing belongs to the user and is active.
    try:
        from backend.services.shop_auction_service import list_user_listings

        owned = {l.get("listing_id") for l in (list_user_listings(uid).get("selling") or [])}
    except Exception:
        owned = set()
    if lid not in owned:
        return {"success": False, "error": "You can only feature your own active listings"}
    cfg = _feature_cfg()
    price = int(cfg.get("price_coins") or 0)
    hours = int(cfg.get("duration_hours") or 48)
    ok, err = _charge(uid, price, payment_method=payment_method, source="auction_feature",
                      metadata={"listing_id": lid})
    if not ok:
        return {"success": False, "error": err}
    expires = _iso(_now() + timedelta(hours=hours))
    with _LOCK:
        state = _load_state()
        feats = state.setdefault("auction_features", {})
        feats[lid] = {"user_id": uid, "expires_at": expires}
        _save_state(state)
    return {"success": True, "listing_id": lid, "expires_at": expires, "price_paid_coins": price}


def get_featured_listing_ids() -> List[str]:
    state = _load_state()
    out = []
    now = _now()
    for lid, rec in (state.get("auction_features") or {}).items():
        exp = _parse_iso((rec or {}).get("expires_at"))
        if exp and exp > now:
            out.append(lid)
    return out


# ---------------------------------------------------------------------------
# Top 25 Legends collection (completion goal + trophy)
# ---------------------------------------------------------------------------

def _top25_cfg() -> Dict[str, Any]:
    cfg = get_config().get("top25_collection") or {}
    return {
        "series_prefix": cfg.get("series_prefix") or "top25-",
        "total": int(cfg.get("total") or 25),
        "completion_reward": cfg.get("completion_reward") or {},
    }


def _owned_item_ids(user_id: str) -> set:
    """Set of item_ids the user owns (inventory), best-effort across persistence modes."""
    try:
        from backend.services.shop_db_service import get_inventory

        inv = get_inventory(user_id) or []
    except Exception:
        inv = []
    out = set()
    for row in inv:
        if not isinstance(row, dict):
            continue
        iid = (row.get("item_id") or row.get("id") or "").strip()
        if iid:
            out.add(iid)
    return out


def _top25_owned(user_id: str) -> List[str]:
    cfg = _top25_cfg()
    prefix, total = cfg["series_prefix"], cfg["total"]
    series_ids = [f"{prefix}{n:02d}" for n in range(1, total + 1)]
    owned = _owned_item_ids(user_id)
    return [iid for iid in series_ids if iid in owned]


def get_top25_status(user_id: str) -> Dict[str, Any]:
    """Collection progress + whether the completion trophy is claimable/claimed."""
    cfg = _top25_cfg()
    total = cfg["total"]
    owned = _top25_owned(user_id)
    owned_count = len(owned)
    complete = owned_count >= total
    claimed = bool(((_load_state().get("top25") or {}).get(str(user_id)) or {}).get("claimed_at"))
    return {
        "success": True,
        "total": total,
        "owned_count": owned_count,
        "owned_ids": owned,
        "complete": complete,
        "claimed": claimed,
        "claimable": complete and not claimed,
        "reward": cfg["completion_reward"],
    }


def claim_top25_completion(user_id: str) -> Dict[str, Any]:
    """Grant the completion reward (coins + loyalty + trophy + badge) once all 25 are owned."""
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "Sign in to claim the Top 25 completion reward."}
    cfg = _top25_cfg()
    total = cfg["total"]
    owned = _top25_owned(uid)
    if len(owned) < total:
        return {"success": False, "error": f"Collection incomplete ({len(owned)}/{total} owned).",
                "owned_count": len(owned), "total": total}

    state = _load_state()
    top25 = state.setdefault("top25", {})
    rec = top25.get(uid) or {}
    if rec.get("claimed_at"):
        return {"success": False, "error": "Completion reward already claimed.", "claimed": True}

    reward = cfg["completion_reward"] or {}
    granted: List[Dict[str, Any]] = []
    coins = int(reward.get("coins") or 0)
    if coins > 0:
        granted.append(_grant(uid, {"type": "coins", "amount": coins}, source="top25_completion"))
    loyalty_pts = int(reward.get("loyalty_points") or 0)
    if loyalty_pts > 0:
        _add_loyalty_points(uid, loyalty_pts, source="top25_completion")
        granted.append({"type": "loyalty", "amount": loyalty_pts, "label": f"{loyalty_pts} loyalty"})
    trophy_id = (reward.get("trophy_item_id") or "").strip()
    if trophy_id:
        trophy_name = reward.get("trophy_name") or "Top 25 Collector Trophy"
        try:
            from backend.services.shop_db_service import add_to_inventory

            add_to_inventory(uid, trophy_id, trophy_name, 1)
        except Exception:
            pass
        granted.append({"type": "item", "ref": trophy_id, "label": trophy_name})

    top25[uid] = {"claimed_at": _iso(_now()), "badge": reward.get("badge") or "", "granted": granted}
    _save_state(state)
    return {"success": True, "message": "Top 25 Legends complete — reward claimed!",
            "granted": granted, "reward": reward}


# ---------------------------------------------------------------------------
# Aggregate overview (for the Deals & VIP tab)
# ---------------------------------------------------------------------------

def get_overview(user_id: str) -> Dict[str, Any]:
    return {
        "vip": get_vip_status(user_id),
        "loyalty": get_loyalty(user_id),
        "spin": get_spin_status(user_id),
        "mystery_boxes": list_mystery_boxes(user_id),
        "flash_sales": get_flash_sales(),
        "gifting": get_config().get("gifting") or {},
        "auction_feature": _feature_cfg(),
        "top25": get_top25_status(user_id),
        "coin_balance": _coin_balance(user_id),
    }
