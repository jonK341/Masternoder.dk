"""Exchange shop — rewards, skill packs, boosts, and rental items (MN2)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CATALOG_PATH = os.path.join(ex._BASE, "data", "exchange_shop_catalog.json")
_STATE_DIR = os.path.join(ex._DATA_DIR, "exchange_shop")
_PURCHASES_PATH = os.path.join(ex._DATA_DIR, "exchange_shop_purchases.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_catalog() -> Dict[str, Any]:
    cfg = ex._read_json(_CATALOG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _state_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_STATE_DIR, f"{safe}.json")


def _load_state(user_id: str) -> Dict[str, Any]:
    data = ex._read_json(_state_path(user_id), {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("purchases", [])
    data.setdefault("trust_bonus_until", None)
    data.setdefault("trust_bonus", 0)
    data.setdefault("fee_discount_bps", 0)
    data.setdefault("fee_discount_until", None)
    data.setdefault("profit_boost_until", None)
    data.setdefault("profit_multiplier", 1.0)
    data.setdefault("scan_tokens", 0)
    return data


def _save_state(user_id: str, data: Dict[str, Any]) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    ex._write_json(_state_path(user_id), data)


def _item_map() -> Dict[str, Dict[str, Any]]:
    return {i["id"]: i for i in (load_catalog().get("items") or []) if isinstance(i, dict) and i.get("id")}


def shop_catalog() -> Dict[str, Any]:
    cfg = load_catalog()
    from backend.services import exchange_bot_skills_service as sk
    items = []
    for it in cfg.get("items") or []:
        if not isinstance(it, dict):
            continue
        row = dict(it)
        if row.get("skill_ids"):
            row["skill_details"] = sk.skill_details(list(row.get("skill_ids") or []))
        items.append(row)
    return {"success": True, "enabled": bool(cfg.get("enabled", True)),
            "currency": cfg.get("currency", "MN2"), "items": items}


def user_shop_state(user_id: str) -> Dict[str, Any]:
    st = _load_state(user_id)
    now = _iso()
    active = {
        "trust_bonus": st.get("trust_bonus") if st.get("trust_bonus_until") and st["trust_bonus_until"] > now else 0,
        "fee_discount_bps": st.get("fee_discount_bps") if st.get("fee_discount_until") and st["fee_discount_until"] > now else 0,
        "profit_multiplier": st.get("profit_multiplier", 1.0) if st.get("profit_boost_until") and st["profit_boost_until"] > now else 1.0,
        "scan_tokens": int(st.get("scan_tokens") or 0),
    }
    return {"success": True, "user_id": user_id, "active_effects": active, "purchase_count": len(st.get("purchases") or [])}


def profit_multiplier(user_id: str) -> float:
    st = _load_state(user_id)
    until = st.get("profit_boost_until")
    if until and until > _iso():
        return float(st.get("profit_multiplier") or 1.0)
    return 1.0


def fulfill_item(user_id: str, item_id: str, *, agent_id: Optional[str] = None,
                 record_purchase: bool = True, price_mn2: float = 0) -> Dict[str, Any]:
    """Apply shop item effects without charging (used after main /shop checkout)."""
    user_id = (user_id or "").strip()
    item = _item_map().get((item_id or "").strip())
    if not item:
        return {"success": False, "error": "unknown_item"}

    st = _load_state(user_id)
    result: Dict[str, Any] = {"item_id": item_id, "category": item.get("category")}
    cat = item.get("category")

    if cat == "reward":
        mn2 = float(item.get("reward_mn2") or 0)
        xp = float(item.get("reward_xp") or 0)
        if mn2 > 0:
            ex._adjust_quote_balance(user_id, "MN2", mn2, "exchange_shop_reward", {"item_id": item_id})
        if xp > 0:
            try:
                from backend.services import exchange_leveling_service as lvl
                lvl.award_xp(user_id, xp, "exchange_shop_reward")
            except Exception:
                pass
        result.update({"reward_mn2": mn2, "reward_xp": xp})

    elif cat == "skill":
        if not agent_id:
            return {"success": False, "error": "agent_id_required"}
        from backend.services import agent_marketplace_service as mkt
        data = mkt._read_user_agents(user_id)
        agent = data.get("agents", {}).get(agent_id)
        if not agent:
            return {"success": False, "error": "agent_not_found"}
        extra = list(agent.get("extra_skills") or [])
        for sid in item.get("skill_ids") or []:
            if sid not in extra and sid not in (agent.get("skills") or []):
                extra.append(sid)
        agent["extra_skills"] = extra
        days = int(item.get("skill_days") or 14)
        agent.setdefault("extra_skill_expires", {})["pack"] = (
            datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
        data["agents"][agent_id] = agent
        mkt._write_user_agents(user_id, data)
        result["agent_id"] = agent_id
        result["skills_added"] = list(item.get("skill_ids") or [])

    elif cat == "rental":
        if not agent_id:
            return {"success": False, "error": "agent_id_required"}
        from backend.services import exchange_rental_service as rent
        ext = rent.extend_rental(user_id, agent_id, int(item.get("extend_days") or 3))
        if not ext.get("success"):
            return ext
        result.update(ext)

    elif cat == "trust":
        st["trust_bonus"] = float(item.get("trust_bonus") or 0)
        st["trust_bonus_until"] = (datetime.now(timezone.utc) + timedelta(days=int(item.get("trust_days") or 30))).isoformat().replace("+00:00", "Z")
        result["trust_bonus"] = st["trust_bonus"]

    elif cat == "boost":
        st["profit_multiplier"] = float(item.get("profit_multiplier") or 1.25)
        st["profit_boost_until"] = (datetime.now(timezone.utc) + timedelta(hours=int(item.get("boost_hours") or 24))).isoformat().replace("+00:00", "Z")
        result["profit_multiplier"] = st["profit_multiplier"]

    elif cat == "fee":
        st["fee_discount_bps"] = float(item.get("fee_discount_bps") or 0)
        st["fee_discount_until"] = (datetime.now(timezone.utc) + timedelta(days=int(item.get("fee_days") or 14))).isoformat().replace("+00:00", "Z")
        result["fee_discount_bps"] = st["fee_discount_bps"]

    elif cat == "tool":
        st["scan_tokens"] = int(st.get("scan_tokens") or 0) + int(item.get("scan_uses") or 0)
        result["scan_tokens"] = st["scan_tokens"]

    elif cat == "rental_voucher":
        rid = item.get("rental_id")
        if rid:
            from backend.services import exchange_rental_service as rent
            r = rent.rent_agent(user_id, rid, prepaid=True)
            result["rental"] = r

    if record_purchase:
        st["purchases"].append({"ts": _iso(), "item_id": item_id, "price_mn2": price_mn2})
        _save_state(user_id, st)
        ex._append_jsonl(_PURCHASES_PATH, {"ts": _iso(), "user_id": user_id, "item_id": item_id, "price_mn2": price_mn2})
        ex._audit("exchange_shop_purchase", user_id=user_id, item_id=item_id, amount_usd=price_mn2 * 0.05)
    else:
        _save_state(user_id, st)
    return {"success": True, "spent_mn2": price_mn2, "effect": result}


def purchase_item(user_id: str, item_id: str, *, agent_id: Optional[str] = None) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_catalog()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "shop_disabled"}
    item = _item_map().get((item_id or "").strip())
    if not item:
        return {"success": False, "error": "unknown_item"}
    price = float(item.get("price_mn2") or 0)
    if price > 0 and ex._get_quote_balance(user_id, "MN2") < price:
        return {"success": False, "error": "insufficient_mn2", "needed_mn2": price}

    if price > 0:
        ex._adjust_quote_balance(user_id, "MN2", -price, "exchange_shop",
                                 {"item_id": item_id, "category": item.get("category")})

    return fulfill_item(user_id, item_id, agent_id=agent_id, record_purchase=True, price_mn2=price)


def shop_items_for_catalog() -> List[Dict[str, Any]]:
    """Top exchange shop SKUs for the main /shop catalog (shop_linked items only)."""
    cfg = load_catalog()
    if not cfg.get("enabled", True):
        return []
    coins_per_mn2 = 100.0
    try:
        cfg_path = os.path.join(ex._BASE, "data", "mn2_config.json")
        raw = ex._read_json(cfg_path, {})
        coins_per_mn2 = float(raw.get("coins_per_mn2") or 100)
    except Exception:
        pass
    out: List[Dict[str, Any]] = []
    for item in cfg.get("items") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        if item.get("shop_linked") is False:
            continue
        price_mn2 = float(item.get("price_mn2") or 0)
        price_coins = max(1, int(round(price_mn2 * coins_per_mn2)))
        cat = item.get("category") or "exchange"
        out.append({
            "id": item["id"],
            "name": item.get("name") or item["id"],
            "description": item.get("description") or "",
            "category": "exchange",
            "price": price_coins,
            "price_mn2": price_mn2,
            "icon": "📈",
            "image": item.get("image"),
            "rarity": "legendary" if price_mn2 >= 150 else ("epic" if price_mn2 >= 80 else "rare"),
            "tags": ["exchange", "exchange_shop", str(cat)],
            "payment_rails": ["mn2", "coins"],
            "delivery": "exchange_shop",
            "exchange_item_id": item["id"],
            "requires_agent_id": cat in ("skill", "rental"),
            "featured": bool(item.get("featured")),
        })
    return out
