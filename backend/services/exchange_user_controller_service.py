"""Unified user control hub — rent agents, add skills, shop, multi-rail pay, profit cash-out."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import agent_marketplace_service as mkt
from backend.services import exchange_rental_service as rent
from backend.services import exchange_shop_service as shop

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_controller_config.json")
_STATE_DIR = os.path.join(ex._DATA_DIR, "exchange_controller")
_PAYPAL_ORDERS = os.path.join(ex._DATA_DIR, "controller_paypal_orders.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _coins_per_mn2() -> float:
    raw = ex._read_json(os.path.join(ex._BASE, "data", "mn2_config.json"), {})
    return max(float(raw.get("coins_per_mn2") or 100), 1.0)


def _state_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_STATE_DIR, f"{safe}.json")


def _load_state(user_id: str) -> Dict[str, Any]:
    data = ex._read_json(_state_path(user_id), {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("withdrawn_profit_usd", 0.0)
    data.setdefault("casino_coins_granted", 0)
    return data


def _save_state(user_id: str, data: Dict[str, Any]) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    ex._write_json(_state_path(user_id), data)


def _balances(user_id: str) -> Dict[str, float]:
    mn2 = float(ex._get_quote_balance(user_id, "MN2") or 0)
    coins = 0.0
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(user_id).get("points", {})
        coins = float(pts.get("coins") or 0)
        if mn2 <= 0:
            mn2 = float(pts.get("mn2_balance") or 0)
    except Exception:
        pass
    return {"mn2": mn2, "coins": coins}


def _price_bundle(price_mn2: float, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    cpm = _coins_per_mn2()
    mn2_usd = ex._mn2_usd()
    markup = float(cfg.get("usd_per_mn2_markup_pct") or 0) / 100.0
    price_usd = round(float(price_mn2) * mn2_usd * (1.0 + markup), 2)
    rails = list(cfg.get("payment_rails") or ["mn2", "coins", "paypal"])
    return {
        "price_mn2": float(price_mn2),
        "price_coins": max(1, int(round(float(price_mn2) * cpm))),
        "price_usd": max(0.99, price_usd) if price_mn2 > 0 else 0.0,
        "payment_rails": rails,
    }


def _resolve_target(action: str, target_id: str) -> Tuple[Optional[Dict[str, Any]], float, str]:
    action = (action or "").strip().lower()
    tid = (target_id or "").strip()
    if action == "rent":
        tmpl = rent._rental_map().get(tid)
        if not tmpl:
            return None, 0.0, "unknown_rental"
        return tmpl, float(tmpl.get("price_mn2") or 0), "rent"
    if action == "addon":
        addon = rent._addon_map().get(tid)
        if not addon:
            return None, 0.0, "unknown_addon"
        return addon, float(addon.get("price_mn2") or 0), "addon"
    if action == "shop":
        item = shop._item_map().get(tid)
        if not item:
            return None, 0.0, "unknown_item"
        return item, float(item.get("price_mn2") or 0), "shop"
    if action == "buy":
        tmpl = mkt._template_map().get(tid)
        if not tmpl:
            return None, 0.0, "unknown_template"
        return tmpl, float(tmpl.get("price_mn2") or 0), "buy"
    return None, 0.0, "unknown_action"


def hub_state(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_config()
    bal = _balances(user_id)
    port = mkt.user_portfolio(user_id)
    rentals = rent.list_user_rentals(user_id)
    st = _load_state(user_id)
    total_realized = float(port.get("total_realized_profit_usd") or 0)
    withdrawn = float(st.get("withdrawn_profit_usd") or 0)
    cash_cfg = cfg.get("cash_out") or {}
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "user_id": user_id,
        "balances": bal,
        "payment_rails": cfg.get("payment_rails") or ["mn2", "coins", "paypal"],
        "total_realized_profit_usd": total_realized,
        "withdrawn_profit_usd": withdrawn,
        "cash_out_available_usd": max(0.0, total_realized - withdrawn),
        "cash_out_min_usd": float(cash_cfg.get("min_usd") or 1.0),
        "cash_out_destinations": cash_cfg.get("destinations") or ["mn2", "coins"],
        "agent_count": len(port.get("agents") or []),
        "rental_count": int(rentals.get("count") or 0),
        "rentals": (rentals.get("rentals") or [])[:10],
        "agents": (port.get("agents") or [])[:10],
        "casino_bridge": cfg.get("casino_bridge") or {},
    }


def quote_purchase(user_id: str, action: str, target_id: str) -> Dict[str, Any]:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "controller_disabled"}
    target, price_mn2, kind = _resolve_target(action, target_id)
    if not target:
        return {"success": False, "error": kind}
    bal = _balances(user_id)
    prices = _price_bundle(price_mn2, cfg)
    return {
        "success": True,
        "action": kind,
        "target_id": target_id,
        "name": target.get("name") or target_id,
        "description": target.get("description", ""),
        "image": target.get("image"),
        "requires_agent_id": kind in ("addon", "shop") and target.get("category") in ("skill", "rental"),
        **prices,
        "balances": bal,
        "can_pay_mn2": bal["mn2"] >= prices["price_mn2"],
        "can_pay_coins": bal["coins"] >= prices["price_coins"],
    }


def _charge(user_id: str, payment_method: str, price_mn2: float, price_coins: int,
            source: str, meta: Dict[str, Any]) -> Optional[str]:
    method = (payment_method or "mn2").strip().lower()
    if method == "mn2":
        if ex._get_quote_balance(user_id, "MN2") < price_mn2:
            return "insufficient_mn2"
        if price_mn2 > 0:
            ex._adjust_quote_balance(user_id, "MN2", -price_mn2, source, meta)
        return None
    if method == "coins":
        try:
            from backend.services.unified_points_database import unified_points_db

            pts = unified_points_db.get_all_points(user_id).get("points", {})
            coins = float(pts.get("coins") or 0)
            if coins < price_coins:
                return "insufficient_coins"
            unified_points_db.add_points(user_id, "coins", -price_coins, source=source, metadata=meta)
            return None
        except Exception:
            return "coins_unavailable"
    return "unsupported_payment_method"


def _fulfill(action: str, user_id: str, target_id: str, *,
             agent_id: Optional[str] = None, auto_renew: bool = False,
             prepaid: bool = False) -> Dict[str, Any]:
    if action == "rent":
        return rent.rent_agent(user_id, target_id, prepaid=prepaid, auto_renew=auto_renew)
    if action == "addon":
        if not agent_id:
            return {"success": False, "error": "agent_id_required"}
        return rent.add_skill_addon(user_id, agent_id, target_id, prepaid=prepaid)
    if action == "shop":
        return shop.fulfill_item(user_id, target_id, agent_id=agent_id,
                                 record_purchase=True, price_mn2=0 if prepaid else float(shop._item_map().get(target_id, {}).get("price_mn2") or 0))
    if action == "buy":
        return mkt.purchase_agent(user_id, target_id, prepaid=prepaid)
    return {"success": False, "error": "unknown_action"}


def checkout(user_id: str, action: str, target_id: str, *,
             payment_method: str = "mn2", agent_id: Optional[str] = None,
             auto_renew: bool = False) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "controller_disabled"}
    target, price_mn2, kind = _resolve_target(action, target_id)
    if not target:
        return {"success": False, "error": kind}
    prices = _price_bundle(price_mn2, cfg)
    if kind == "addon" and not agent_id:
        return {"success": False, "error": "agent_id_required"}
    if kind == "shop" and target.get("category") in ("skill", "rental") and not agent_id:
        return {"success": False, "error": "agent_id_required"}

    method = (payment_method or "mn2").strip().lower()
    if method == "paypal":
        return {"success": False, "error": "use_paypal_create_order", "hint": "POST /api/exchange/controller/paypal/create"}

    err = _charge(user_id, method, prices["price_mn2"], prices["price_coins"],
                  f"controller_{kind}", {"action": kind, "target_id": target_id, "payment_method": method})
    if err:
        return {"success": False, "error": err, **prices}

    result = _fulfill(kind, user_id, target_id, agent_id=agent_id, auto_renew=auto_renew, prepaid=True)
    if not result.get("success"):
        return result
    ex._audit("controller_checkout", user_id=user_id, purchase_kind=kind, target_id=target_id,
              payment_method=method, amount_mn2=prices["price_mn2"])
    try:
        from backend.services.exchange_casino_quest_service import record_bridge_action

        if kind == "rent":
            record_bridge_action(user_id, "exchange_rent")
        elif kind == "addon":
            record_bridge_action(user_id, "exchange_skill_addon")
    except Exception:
        pass
    return {"success": True, "payment_method": method, "spent": prices, "result": result}


def record_paypal_order(order_id: str, user_id: str, payload: Dict[str, Any], *, approve_url: str = "") -> Dict[str, Any]:
    pending = {
        "order_id": order_id,
        "user_id": user_id,
        "payload": payload,
        "approve_url": approve_url,
        "created_at": _iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
    }
    rows = ex._read_json(_PAYPAL_ORDERS, {"pending": {}, "captured": {}})
    rows.setdefault("pending", {})[order_id] = pending
    ex._write_json(_PAYPAL_ORDERS, rows)
    return {"success": True, "order_id": order_id}


def fulfill_paypal_order(user_id: str, order_id: str, capture: Dict[str, Any]) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    order_id = (order_id or "").strip()
    rows = ex._read_json(_PAYPAL_ORDERS, {"pending": {}, "captured": {}})
    if order_id in rows.get("captured", {}):
        return {"success": True, "already_fulfilled": True, **rows["captured"][order_id]}
    pending = (rows.get("pending") or {}).get(order_id)
    if not pending:
        return {"success": False, "error": "order_not_found"}
    if pending.get("user_id") != uid:
        return {"success": False, "error": "user_mismatch"}
    if not capture.get("success"):
        return {"success": False, "error": capture.get("error", "capture_failed")}

    pl = pending.get("payload") or {}
    result = _fulfill(
        pl.get("action", ""),
        uid,
        pl.get("target_id", ""),
        agent_id=pl.get("agent_id"),
        auto_renew=bool(pl.get("auto_renew")),
        prepaid=True,
    )
    if not result.get("success"):
        return result
    cap = {"order_id": order_id, "fulfilled_at": _iso(), "result": result, "payload": pl}
    rows.setdefault("captured", {})[order_id] = cap
    rows.get("pending", {}).pop(order_id, None)
    ex._write_json(_PAYPAL_ORDERS, rows)
    ex._audit("controller_paypal_capture", user_id=uid, order_id=order_id, purchase_kind=pl.get("action"))
    return {"success": True, **cap}


def cash_out_profit(user_id: str, amount_usd: float, destination: str = "mn2") -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_config()
    co = cfg.get("cash_out") or {}
    if not co.get("enabled", True):
        return {"success": False, "error": "cash_out_disabled"}
    dest = (destination or "mn2").strip().lower()
    if dest not in (co.get("destinations") or ["mn2", "coins"]):
        return {"success": False, "error": "invalid_destination"}

    port = mkt.user_portfolio(user_id)
    total = float(port.get("total_realized_profit_usd") or 0)
    st = _load_state(user_id)
    withdrawn = float(st.get("withdrawn_profit_usd") or 0)
    available = max(0.0, total - withdrawn)
    amt = float(amount_usd or 0)
    min_usd = float(co.get("min_usd") or 1.0)
    if amt <= 0:
        amt = available
    if amt < min_usd:
        return {"success": False, "error": "below_min_usd", "min_usd": min_usd, "available_usd": available}
    if amt > available + 0.0001:
        return {"success": False, "error": "insufficient_profit", "available_usd": available}

    granted: Dict[str, Any] = {"destination": dest, "amount_usd": round(amt, 4)}
    if dest == "mn2":
        mn2_rate = co.get("mn2_per_usd")
        mn2_usd = ex._mn2_usd()
        mn2_amt = float(amt) / mn2_usd if not mn2_rate else float(mn2_rate) * float(amt)
        ex._adjust_quote_balance(user_id, "MN2", mn2_amt, "exchange_profit_cashout", {"usd": amt})
        granted["mn2"] = mn2_amt
    elif dest == "coins":
        cpm = _coins_per_mn2()
        coins = int(round(float(amt) * cpm))
        try:
            from backend.services.unified_points_database import unified_points_db

            unified_points_db.add_points(user_id, "coins", coins, source="exchange_profit_cashout", metadata={"usd": amt})
        except Exception:
            return {"success": False, "error": "coins_grant_failed"}
        granted["coins"] = coins
    elif dest == "casino_coins":
        cc = int(round(float(amt) * float(co.get("casino_coins_per_usd") or 100)))
        try:
            from backend.services.unified_points_database import unified_points_db

            unified_points_db.add_points(user_id, "coins", cc, source="exchange_casino_bridge", metadata={"usd": amt, "bridge": "casino"})
        except Exception:
            return {"success": False, "error": "casino_coins_failed"}
        granted["casino_coins"] = cc
        st["casino_coins_granted"] = int(st.get("casino_coins_granted") or 0) + cc

    st["withdrawn_profit_usd"] = round(withdrawn + amt, 6)
    _save_state(user_id, st)
    ex._audit("exchange_profit_cashout", user_id=user_id, amount_usd=amt, destination=dest)
    if dest == "casino_coins":
        try:
            from backend.services.exchange_casino_quest_service import record_bridge_action

            record_bridge_action(user_id, "exchange_cashout_casino")
        except Exception:
            pass
    return {"success": True, "granted": granted, "withdrawn_total_usd": st["withdrawn_profit_usd"]}


def grant_casino_bridge_bonus(user_id: str, reason: str, *, agent_id: Optional[str] = None) -> int:
    """Grant play coins when exchange events cross into casino (e.g. rental completion)."""
    cfg = load_config()
    bridge = cfg.get("casino_bridge") or {}
    if not bridge.get("enabled", True):
        return 0
    amount = 0
    if reason == "rental_completion":
        amount = int(bridge.get("rental_completion_casino_coins") or 0)
    if amount <= 0:
        return 0
    try:
        from backend.services.unified_points_database import unified_points_db

        unified_points_db.add_points(
            user_id, "coins", amount,
            source="exchange_casino_bridge_bonus",
            metadata={"reason": reason, "agent_id": agent_id},
        )
        st = _load_state(user_id)
        st["casino_coins_granted"] = int(st.get("casino_coins_granted") or 0) + amount
        _save_state(user_id, st)
        ex._audit("exchange_casino_bridge_bonus", user_id=user_id, reason=reason, coins=amount)
    except Exception:
        return 0
    return amount


def catalog_for_controller() -> Dict[str, Any]:
    rc = rent.rental_catalog()
    sc = shop.shop_catalog()
    mcat = mkt.get_catalog()
    addons = rc.get("skill_addons") or []
    rentals = rc.get("rentals") or []
    items = sc.get("items") or []
    buy_bots = mcat.get("templates") or []
    cfg = load_config()
    def _wrap(row: Dict[str, Any], action: str) -> Dict[str, Any]:
        p = float(row.get("price_mn2") or 0)
        return {**row, "action": action, **_price_bundle(p, cfg)}
    return {
        "success": True,
        "rentals": [_wrap(r, "rent") for r in rentals],
        "addons": [_wrap(a, "addon") for a in addons],
        "shop_items": [_wrap(i, "shop") for i in items],
        "buy_bots": [_wrap(b, "buy") for b in buy_bots],
        "payment_rails": cfg.get("payment_rails") or ["mn2", "coins", "paypal"],
    }
