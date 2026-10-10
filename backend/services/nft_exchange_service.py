"""Site-issued NFT editions and a coin resale book.

Primary sales are house mints (PayPal USD or shop coins). Secondary sales
transfer one serial and keep a house fee. This is an internal edition
registry, not a public-chain mint.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import backend.services.unified_points_database as points_mod
from backend.services.mn2_earn_auth import require_earn_user

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG = os.path.join(_BASE, "data", "nft_catalog.json")
_STATE = os.path.join(_BASE, "data", "nft_exchange_state.json")
_AGENT_OWNER_PREFIX = "agent:"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_catalog() -> Dict[str, Any]:
    with open(_CATALOG, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return {"skus": [], "secondary_fee_percent": 5, "min_list_coins": 20}
    data.setdefault("skus", [])
    data.setdefault("secondary_fee_percent", 5)
    data.setdefault("min_list_coins", 20)
    return data


def _sku_map() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in _load_catalog().get("skus") or []:
        if isinstance(row, dict) and row.get("sku"):
            out[str(row["sku"])] = row
    return out


def is_nft_sku(sku: str) -> bool:
    return str(sku or "").strip() in _sku_map()


def paypal_item_map() -> Dict[str, Dict[str, Any]]:
    """SKU map shaped for the shop PayPal item list."""
    result: Dict[str, Dict[str, Any]] = {}
    for sku, row in _sku_map().items():
        try:
            price = float(row.get("price_usd") or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            continue
        result[sku] = {"price_usd": price, "name": row.get("name") or sku}
    return result


def _empty_state() -> Dict[str, Any]:
    return {"editions": [], "listings": [], "trades": []}


def _read_state() -> Dict[str, Any]:
    if not os.path.isfile(_STATE):
        return _empty_state()
    try:
        with open(_STATE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()
    data.setdefault("editions", [])
    data.setdefault("listings", [])
    data.setdefault("trades", [])
    return data


def _write_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE), exist_ok=True)
    tmp = _STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp, _STATE)


def _fee_percent() -> int:
    try:
        return max(0, min(50, int(_load_catalog().get("secondary_fee_percent") or 0)))
    except (TypeError, ValueError):
        return 5


def _min_list_coins() -> int:
    try:
        return max(1, int(_load_catalog().get("min_list_coins") or 20))
    except (TypeError, ValueError):
        return 20


def _fee_coins(price_coins: int) -> int:
    return int(price_coins) * _fee_percent() // 100


def _minted_count(state: Dict[str, Any], sku: str) -> int:
    return sum(1 for row in state.get("editions") or [] if row.get("sku") == sku)


def _public_sku(row: Dict[str, Any], minted: int) -> Dict[str, Any]:
    supply = int(row.get("supply") or 0)
    return {
        "sku": row.get("sku"),
        "name": row.get("name"),
        "series": row.get("series"),
        "rarity": row.get("rarity"),
        "description": row.get("description"),
        "supply": supply,
        "minted": minted,
        "remaining": max(0, supply - minted),
        "price_usd": float(row.get("price_usd") or 0),
        "price_coins": int(row.get("price_coins") or 0),
        "secondary_fee_percent": _fee_percent(),
        "trophy_id": row.get("trophy_id"),
        "emblem_icon": row.get("emblem_icon"),
        "avatar_url": row.get("avatar_url"),
    }


def _sku_meta(sku: str) -> Dict[str, Any]:
    return dict(_sku_map().get(str(sku or "").strip()) or {})


def _public_edition(row: Dict[str, Any]) -> Dict[str, Any]:
    meta = _sku_meta(str(row.get("sku") or ""))
    return {
        "edition_id": row.get("edition_id"),
        "sku": row.get("sku"),
        "name": row.get("name"),
        "serial": row.get("serial"),
        "owner_id": row.get("owner_id"),
        "status": row.get("status"),
        "minted_at": row.get("minted_at"),
        "mint_source": row.get("mint_source"),
        "trophy_id": meta.get("trophy_id"),
        "emblem_icon": meta.get("emblem_icon"),
        "avatar_url": meta.get("avatar_url"),
    }


def _public_listing(row: Dict[str, Any], edition: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    price = int(row.get("price_coins") or 0)
    fee = _fee_coins(price)
    return {
        "listing_id": row.get("listing_id"),
        "edition_id": row.get("edition_id"),
        "sku": (edition or {}).get("sku") or row.get("sku"),
        "name": (edition or {}).get("name"),
        "serial": (edition or {}).get("serial"),
        "seller_id": row.get("seller_id"),
        "price_coins": price,
        "fee_coins": fee,
        "seller_receives_coins": price - fee,
        "status": row.get("status"),
        "created_at": row.get("created_at"),
    }


def catalog() -> Dict[str, Any]:
    state = _read_state()
    skus = [
        _public_sku(row, _minted_count(state, str(row.get("sku"))))
        for row in (_load_catalog().get("skus") or [])
        if isinstance(row, dict) and row.get("sku")
    ]
    return {
        "success": True,
        "secondary_fee_percent": _fee_percent(),
        "min_list_coins": _min_list_coins(),
        "wallet_schema_version": int(_load_catalog().get("wallet_schema_version") or 2),
        "settlement": "Primary: PayPal USD or shop coins. Resale: shop coins, house keeps the fee.",
        "skus": skus,
    }


def _coin_balance(user_id: str) -> float:
    payload = points_mod.unified_points_db.get_all_points(user_id).get("points") or {}
    try:
        return float(payload.get("coins") or 0)
    except (TypeError, ValueError):
        return 0.0


def _move_coins(user_id: str, amount: float, source: str, reference: str) -> Dict[str, Any]:
    return points_mod.unified_points_db.add_points(
        user_id,
        "coins",
        amount,
        source=source,
        metadata={"reference": reference},
    )


def _append_trade(state: Dict[str, Any], row: Dict[str, Any]) -> None:
    trades = state.setdefault("trades", [])
    trades.append(row)


def _mint(state: Dict[str, Any], user_id: str, sku_row: Dict[str, Any], source: str, order_id: str = "") -> Dict[str, Any]:
    sku = str(sku_row["sku"])
    supply = int(sku_row.get("supply") or 0)
    minted = _minted_count(state, sku)
    if minted >= supply:
        return {"success": False, "error": "sold_out"}
    serial = minted + 1
    edition = {
        "edition_id": f"{sku}#{serial}",
        "sku": sku,
        "name": sku_row.get("name") or sku,
        "serial": serial,
        "owner_id": user_id,
        "status": "held",
        "mint_source": source,
        "order_id": order_id or "",
        "minted_at": _iso(),
    }
    state.setdefault("editions", []).append(edition)
    return {"success": True, "edition": edition}


def buy_with_coins(user_id: str, sku: str) -> Dict[str, Any]:
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}
    sku_row = _sku_map().get(str(sku or "").strip())
    if not sku_row:
        return {"success": False, "error": "unknown_sku"}
    price = int(sku_row.get("price_coins") or 0)
    if price <= 0:
        return {"success": False, "error": "sku_not_for_sale"}

    with _LOCK:
        state = _read_state()
        if _minted_count(state, sku_row["sku"]) >= int(sku_row.get("supply") or 0):
            return {"success": False, "error": "sold_out"}
        if _coin_balance(uid) < price:
            return {"success": False, "error": "insufficient_coins"}
        ref = f"nft-primary:{uuid.uuid4().hex[:12]}"
        debit = _move_coins(uid, -price, "nft_primary", ref)
        if not debit.get("success"):
            return {"success": False, "error": debit.get("error") or "coin_debit_failed"}
        minted = _mint(state, uid, sku_row, "coins")
        if not minted.get("success"):
            _move_coins(uid, price, "nft_primary_refund", ref + ":refund")
            return minted
        _append_trade(state, {
            "trade_id": uuid.uuid4().hex[:16],
            "kind": "primary",
            "edition_id": minted["edition"]["edition_id"],
            "sku": sku_row["sku"],
            "buyer_id": uid,
            "seller_id": "house",
            "price_coins": price,
            "fee_coins": price,
            "price_usd": 0,
            "created_at": _iso(),
        })
        _write_state(state)
        edition = minted["edition"]
    return {"success": True, "edition": _public_edition(edition), "price_coins": price}


def grant_paypal_mint(user_id: str, sku: str, order_id: str, amount_usd: float) -> Dict[str, Any]:
    """Mint one serial after a captured PayPal payment. Idempotent on order_id."""
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}
    order_id = str(order_id or "").strip()
    if not order_id:
        return {"success": False, "error": "missing_order_id"}
    sku_row = _sku_map().get(str(sku or "").strip())
    if not sku_row:
        return {"success": False, "error": "unknown_sku"}
    price = float(sku_row.get("price_usd") or 0)
    try:
        paid = float(amount_usd or 0)
    except (TypeError, ValueError):
        paid = 0.0
    if paid + 0.001 < price:
        return {"success": False, "error": "underpaid", "price_usd": price, "amount_usd": paid}

    with _LOCK:
        state = _read_state()
        existing = next(
            (row for row in state.get("editions") or [] if row.get("order_id") == order_id),
            None,
        )
        if existing:
            return {"success": True, "already_minted": True, "edition": _public_edition(existing)}
        minted = _mint(state, uid, sku_row, "paypal", order_id=order_id)
        if not minted.get("success"):
            return minted
        _append_trade(state, {
            "trade_id": uuid.uuid4().hex[:16],
            "kind": "primary",
            "edition_id": minted["edition"]["edition_id"],
            "sku": sku_row["sku"],
            "buyer_id": uid,
            "seller_id": "house",
            "price_coins": 0,
            "fee_coins": 0,
            "price_usd": price,
            "order_id": order_id,
            "created_at": _iso(),
        })
        _write_state(state)
        edition = minted["edition"]
    return {"success": True, "edition": _public_edition(edition), "price_usd": price}


def _editions_for_owner(owner_id: str) -> List[Dict[str, Any]]:
    oid = str(owner_id or "").strip()
    state = _read_state()
    return [
        _public_edition(row)
        for row in state.get("editions") or []
        if row.get("owner_id") == oid
    ]


def _user_prefs(state: Dict[str, Any]) -> Dict[str, Any]:
    prefs = state.get("user_prefs")
    return prefs if isinstance(prefs, dict) else {}


def holdings(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    state = _read_state()
    rows = _editions_for_owner(uid)
    pref = _user_prefs(state).get(uid) if isinstance(_user_prefs(state).get(uid), dict) else {}
    return {
        "success": True,
        "user_id": uid,
        "wallet_schema_version": int(_load_catalog().get("wallet_schema_version") or 2),
        "equipped_avatar_edition_id": pref.get("equipped_avatar_edition_id"),
        "equipped_emblem_edition_id": pref.get("equipped_emblem_edition_id"),
        "editions": rows,
    }


def agent_owner_id(agent_id: str) -> str:
    return f"{_AGENT_OWNER_PREFIX}{str(agent_id or '').strip()}"


def agent_nft_wallet(agent_id: str) -> Dict[str, Any]:
    aid = str(agent_id or "").strip()
    editions = _editions_for_owner(agent_owner_id(aid))
    return {
        "success": True,
        "agent_id": aid,
        "wallet_schema_version": int(_load_catalog().get("wallet_schema_version") or 2),
        "nft_editions": editions,
        "edition_count": len(editions),
    }


def list_agent_nft_wallets() -> Dict[str, Any]:
    provision_trader_agent_nft_wallets()
    try:
        from backend.services.agent_trader_service import trader_agent_ids

        agent_ids = trader_agent_ids()
    except Exception:
        agent_ids = []
    wallets = [agent_nft_wallet(aid) for aid in agent_ids]
    return {"success": True, "wallets": wallets, "count": len(wallets)}


def list_agent_edition_for_resale(agent_id: str, edition_id: str, price_coins: Any) -> Dict[str, Any]:
    """List an agent-owned edition on the coin book (no human earn-user check)."""
    aid = str(agent_id or "").strip()
    edition_id = str(edition_id or "").strip()
    oid = agent_owner_id(aid)
    try:
        price = int(price_coins)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_price"}
    if price < _min_list_coins():
        return {"success": False, "error": "price_below_minimum", "min_list_coins": _min_list_coins()}
    with _LOCK:
        state = _read_state()
        edition = _edition_by_id(state, edition_id)
        if not edition or edition.get("owner_id") != oid:
            return {"success": False, "error": "not_owner"}
        if edition.get("status") != "held":
            return {"success": False, "error": "edition_not_available"}
        listing = {
            "listing_id": "nft_" + uuid.uuid4().hex[:12],
            "edition_id": edition_id,
            "sku": edition.get("sku"),
            "seller_id": oid,
            "price_coins": price,
            "status": "open",
            "created_at": _iso(),
        }
        edition["status"] = "listed"
        state.setdefault("listings", []).append(listing)
        _write_state(state)
    return {"success": True, "listing": _public_listing(listing, edition)}


def provision_trader_agent_nft_wallets() -> Dict[str, Any]:
    """Ensure each trader agent has a v2 NFT wallet edition; list one on the exchange book."""
    skus = list(_sku_map().keys())
    if not skus:
        return {"success": False, "error": "no_skus", "minted": []}
    try:
        from backend.services.agent_trader_service import trader_agent_ids

        agent_ids = trader_agent_ids()
    except Exception:
        agent_ids = []
    minted: List[Dict[str, Any]] = []
    for index, aid in enumerate(agent_ids):
        oid = agent_owner_id(aid)
        if _editions_for_owner(oid):
            continue
        sku = skus[index % len(skus)]
        result = mint_agent_edition(aid, sku, source="agent_wallet_bootstrap")
        if not result.get("success"):
            continue
        edition = result.get("edition") or {}
        minted.append({"agent_id": aid, "edition_id": edition.get("edition_id"), "sku": sku})
        sku_row = _sku_map().get(sku) or {}
        ask = int(sku_row.get("price_coins") or _min_list_coins())
        list_agent_edition_for_resale(aid, str(edition.get("edition_id") or ""), ask)
    return {"success": True, "minted": minted, "count": len(minted)}


def mint_agent_edition(agent_id: str, sku: str, *, source: str = "agent_grant") -> Dict[str, Any]:
    aid = str(agent_id or "").strip()
    if not aid:
        return {"success": False, "error": "missing_agent_id"}
    sku_row = _sku_map().get(str(sku or "").strip())
    if not sku_row:
        return {"success": False, "error": "unknown_sku"}
    with _LOCK:
        state = _read_state()
        if _minted_count(state, sku_row["sku"]) >= int(sku_row.get("supply") or 0):
            return {"success": False, "error": "sold_out"}
        minted = _mint(state, agent_owner_id(aid), sku_row, source)
        if not minted.get("success"):
            return minted
        _write_state(state)
        edition = minted["edition"]
    return {"success": True, "edition": _public_edition(edition)}


def trophy_definitions() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sku, row in _sku_map().items():
        tid = row.get("trophy_id")
        if not tid:
            continue
        rows.append({
            "id": tid,
            "name": row.get("name") or sku,
            "description": row.get("description") or f"Own {row.get('name') or sku} NFT edition",
            "icon": row.get("emblem_icon") or "💎",
            "category": "nft",
            "reward": int(row.get("price_coins") or 0) // 10,
            "requirement": f"Mint or buy {row.get('name') or sku}",
            "rarity": row.get("rarity") or "common",
            "progress_metric": None,
            "progress_target": None,
            "set": "nft_collector",
            "nft_sku": sku,
        })
    return rows


def trophy_unlocks_for_user(user_id: str) -> List[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    owned_skus = {row.get("sku") for row in _editions_for_owner(uid)}
    unlocks: List[Dict[str, Any]] = []
    for sku, row in _sku_map().items():
        if sku not in owned_skus:
            continue
        tid = row.get("trophy_id")
        if not tid:
            continue
        unlocks.append({
            "id": tid,
            "trophy_id": tid,
            "earned": True,
            "earned_at": None,
            "source": "nft_edition",
            "nft_sku": sku,
        })
    return unlocks


def emblems_for_user(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    emblems = []
    for edition in _editions_for_owner(uid):
        emblems.append({
            "id": edition.get("edition_id"),
            "name": edition.get("name"),
            "icon": edition.get("emblem_icon") or "💎",
            "victory_type": "nft_edition",
            "viking_blood_frenzy": 0,
            "serial": edition.get("serial"),
            "sku": edition.get("sku"),
        })
    return {"success": True, "user_id": uid, "emblems": emblems, "total_emblems": len(emblems)}


def avatar_presets_for_user(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    presets = []
    for edition in _editions_for_owner(uid):
        url = edition.get("avatar_url")
        if not url:
            continue
        presets.append({
            "edition_id": edition.get("edition_id"),
            "label": f"{edition.get('name')} #{edition.get('serial')}",
            "avatar_url": url,
            "sku": edition.get("sku"),
        })
    state = _read_state()
    pref = _user_prefs(state).get(uid) if isinstance(_user_prefs(state).get(uid), dict) else {}
    return {
        "success": True,
        "user_id": uid,
        "presets": presets,
        "equipped_avatar_edition_id": pref.get("equipped_avatar_edition_id"),
    }


def equip_avatar(user_id: str, edition_id: str) -> Dict[str, Any]:
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}
    edition_id = str(edition_id or "").strip()
    owned = {row.get("edition_id") for row in _editions_for_owner(uid)}
    if edition_id not in owned:
        return {"success": False, "error": "not_owner"}
    edition = next(row for row in _editions_for_owner(uid) if row.get("edition_id") == edition_id)
    with _LOCK:
        state = _read_state()
        prefs = _user_prefs(state)
        row = prefs.setdefault(uid, {})
        row["equipped_avatar_edition_id"] = edition_id
        row["equipped_emblem_edition_id"] = edition_id
        state["user_prefs"] = prefs
        _write_state(state)
    avatar_url = edition.get("avatar_url")
    try:
        from backend.services.user_onboarding import user_onboarding

        if avatar_url and user_onboarding:
            profile = user_onboarding.get_user_profile(uid) or {}
            raw_prefs = profile.get("preferences") or {}
            if isinstance(raw_prefs, str):
                prefs = json.loads(raw_prefs) if raw_prefs else {}
            else:
                prefs = dict(raw_prefs)
            prefs["avatar_url"] = avatar_url
            prefs["nft_avatar_edition_id"] = edition_id
            user_onboarding.update_user_profile(uid, {"preferences": prefs})
    except Exception:
        pass
    return {
        "success": True,
        "avatar_url": avatar_url,
        "edition_id": edition_id,
    }


def exchange_market_payload(limit: int = 30) -> Dict[str, Any]:
    cat = catalog()
    book = deals(limit=limit)
    return {
        "success": True,
        "catalog": cat.get("skus") or [],
        "deals": book,
        "market_url": "/market",
    }


def _edition_by_id(state: Dict[str, Any], edition_id: str) -> Optional[Dict[str, Any]]:
    for row in state.get("editions") or []:
        if row.get("edition_id") == edition_id:
            return row
    return None


def list_for_sale(user_id: str, edition_id: str, price_coins: Any) -> Dict[str, Any]:
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}
    edition_id = str(edition_id or "").strip()
    try:
        price = int(price_coins)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_price"}
    if price < _min_list_coins():
        return {"success": False, "error": "price_below_minimum", "min_list_coins": _min_list_coins()}

    with _LOCK:
        state = _read_state()
        edition = _edition_by_id(state, edition_id)
        if not edition or edition.get("owner_id") != uid:
            return {"success": False, "error": "not_owner"}
        if edition.get("status") != "held":
            return {"success": False, "error": "edition_not_available"}
        listing = {
            "listing_id": "nft_" + uuid.uuid4().hex[:12],
            "edition_id": edition_id,
            "sku": edition.get("sku"),
            "seller_id": uid,
            "price_coins": price,
            "status": "open",
            "created_at": _iso(),
        }
        edition["status"] = "listed"
        state.setdefault("listings", []).append(listing)
        _write_state(state)
    return {"success": True, "listing": _public_listing(listing, edition)}


def cancel_listing(user_id: str, listing_id: str) -> Dict[str, Any]:
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}
    listing_id = str(listing_id or "").strip()
    with _LOCK:
        state = _read_state()
        listing = next(
            (row for row in state.get("listings") or [] if row.get("listing_id") == listing_id),
            None,
        )
        if not listing or listing.get("status") != "open":
            return {"success": False, "error": "listing_not_found"}
        if listing.get("seller_id") != uid:
            return {"success": False, "error": "not_seller"}
        edition = _edition_by_id(state, listing.get("edition_id"))
        listing["status"] = "cancelled"
        listing["cancelled_at"] = _iso()
        if edition and edition.get("owner_id") == uid:
            edition["status"] = "held"
        _write_state(state)
    return {"success": True, "listing_id": listing_id}


def buy_listing(buyer_id: str, listing_id: str) -> Dict[str, Any]:
    ok, buyer = require_earn_user(buyer_id)
    if not ok:
        return {"success": False, "error": buyer}
    listing_id = str(listing_id or "").strip()
    with _LOCK:
        state = _read_state()
        listing = next(
            (row for row in state.get("listings") or [] if row.get("listing_id") == listing_id and row.get("status") == "open"),
            None,
        )
        if not listing:
            return {"success": False, "error": "listing_not_found"}
        seller = str(listing.get("seller_id") or "")
        if seller == buyer:
            return {"success": False, "error": "cannot_buy_own_listing"}
        edition = _edition_by_id(state, listing.get("edition_id"))
        if not edition or edition.get("owner_id") != seller or edition.get("status") != "listed":
            return {"success": False, "error": "edition_not_available"}
        price = int(listing.get("price_coins") or 0)
        fee = _fee_coins(price)
        seller_gets = price - fee
        if _coin_balance(buyer) < price:
            return {"success": False, "error": "insufficient_coins"}
        ref = f"nft-fill:{listing_id}:{uuid.uuid4().hex[:8]}"
        debit = _move_coins(buyer, -price, "nft_resale_buy", ref)
        if not debit.get("success"):
            return {"success": False, "error": debit.get("error") or "coin_debit_failed"}
        credit = _move_coins(seller, seller_gets, "nft_resale_sell", ref + ":seller")
        if not credit.get("success"):
            _move_coins(buyer, price, "nft_resale_refund", ref + ":refund")
            return {"success": False, "error": credit.get("error") or "seller_credit_failed"}
        edition["owner_id"] = buyer
        edition["status"] = "held"
        listing["status"] = "sold"
        listing["buyer_id"] = buyer
        listing["sold_at"] = _iso()
        listing["fee_coins"] = fee
        trade = {
            "trade_id": uuid.uuid4().hex[:16],
            "kind": "resale",
            "edition_id": edition.get("edition_id"),
            "sku": edition.get("sku"),
            "buyer_id": buyer,
            "seller_id": seller,
            "price_coins": price,
            "fee_coins": fee,
            "seller_receives_coins": seller_gets,
            "listing_id": listing_id,
            "created_at": _iso(),
        }
        _append_trade(state, trade)
        _write_state(state)
    return {
        "success": True,
        "trade": trade,
        "edition": _public_edition(edition),
    }


def open_listings(limit: int = 50) -> Dict[str, Any]:
    state = _read_state()
    editions = {row.get("edition_id"): row for row in state.get("editions") or []}
    rows = []
    for listing in state.get("listings") or []:
        if listing.get("status") != "open":
            continue
        rows.append(_public_listing(listing, editions.get(listing.get("edition_id"))))
    rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    cap = max(1, min(int(limit or 50), 200))
    return {"success": True, "listings": rows[:cap], "count": len(rows)}


def deals(limit: int = 20) -> Dict[str, Any]:
    """Open asks plus recent fills. This is the NFT deal book."""
    state = _read_state()
    book = open_listings(limit=limit)
    trades = [row for row in state.get("trades") or [] if isinstance(row, dict)]
    cap = max(1, min(int(limit or 20), 100))
    recent = list(reversed(trades[-cap:]))
    primary_usd = 0.0
    resale_coins = 0
    house_fee_coins = 0
    for row in trades:
        kind = row.get("kind")
        if kind == "primary":
            try:
                primary_usd += float(row.get("price_usd") or 0)
            except (TypeError, ValueError):
                pass
            house_fee_coins += int(row.get("fee_coins") or 0)
        elif kind == "resale":
            resale_coins += int(row.get("price_coins") or 0)
            house_fee_coins += int(row.get("fee_coins") or 0)
    open_rows = book.get("listings") or []
    ask_coins = sum(int(row.get("price_coins") or 0) for row in open_rows)
    return {
        "success": True,
        "open_count": book.get("count") or 0,
        "open_ask_coins": ask_coins,
        "open_listings": open_rows,
        "recent_trades": recent,
        "primary_volume_usd": round(primary_usd, 2),
        "resale_volume_coins": resale_coins,
        "house_fee_coins": house_fee_coins,
        "minted": len(state.get("editions") or []),
    }


def wallet_summary(user_id: str) -> Dict[str, Any]:
    """MN2 wallet v2 companion payload (editions + equip state)."""
    hold = holdings(user_id)
    avatars = avatar_presets_for_user(user_id)
    return {
        "success": True,
        "wallet_schema_version": hold.get("wallet_schema_version"),
        "edition_count": len(hold.get("editions") or []),
        "editions": hold.get("editions") or [],
        "equipped_avatar_edition_id": hold.get("equipped_avatar_edition_id"),
        "avatar_presets": avatars.get("presets") or [],
    }
