"""Ledger-backed encoder orders — MN2 debits tied to encode fulfillment."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ORDERS_FILE = os.path.join(_BASE, "data", "encoder_orders.json")
_LOCK = threading.RLock()

_VALID_KINDS = frozenset({
    "generator_encode",
    "create_app_encode",
    "encoder_v2_unlock",
    "super_encode",
    "customer_fulfillment",
})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            root = json.load(f)
        enc = root.get("encoder_orders") if isinstance(root, dict) else {}
        return enc if isinstance(enc, dict) else {}
    except Exception:
        return {}


def encoder_orders_enabled() -> bool:
    return bool(_config().get("enabled", True))


def _load_store() -> Dict[str, Any]:
    if not os.path.isfile(_ORDERS_FILE):
        return {"version": 1, "orders": []}
    try:
        with open(_ORDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("orders"), list):
            return data
    except Exception:
        pass
    return {"version": 1, "orders": []}


def _save_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_ORDERS_FILE), exist_ok=True)
    tmp = _ORDERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _ORDERS_FILE)


def _new_order_id() -> str:
    return "encord_" + uuid.uuid4().hex[:12]


def quote_order(kind: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = dict(config or {})
    k = str(kind or "").strip().lower()
    if k not in _VALID_KINDS:
        return {"success": False, "error": "invalid_kind", "kind": k}

    if k == "encoder_v2_unlock":
        upgrade_id = str(cfg.get("upgrade_id") or "").strip()
        from backend.services.encoder_v2_service import catalog_by_id

        row = catalog_by_id().get(upgrade_id)
        if not row:
            return {"success": False, "error": "unknown_upgrade", "upgrade_id": upgrade_id}
        unlock = row.get("unlock") or {}
        cost = 0.0 if unlock.get("free") else float(unlock.get("mn2_cost") or 0)
        return {
            "success": True,
            "kind": k,
            "upgrade_id": upgrade_id,
            "price_mn2": cost,
            "currency": "MN2",
            "charged": cost > 0,
        }

    if k == "generator_encode":
        from backend.services.generator_mn2_service import quote_generation

        tier = str(cfg.get("tier") or cfg.get("mn2_tier") or "standard").strip().lower()
        q = quote_generation(
            duration=int(cfg.get("duration") or cfg.get("duration_sec") or 180),
            short_clip=bool(cfg.get("short_clip")),
            tier=tier,
            config=cfg,
        )
        return {**q, "success": True, "kind": k, "currency": "MN2"}

    if k in ("create_app_encode", "super_encode"):
        from backend.services.encoder_v2_service import build_v2_encode_package

        quality = str(cfg.get("quality_goal") or "balanced")
        pkg = build_v2_encode_package({**cfg, "quality_goal": quality})
        tier = str(pkg.get("video_profile") or "premium")
        from backend.services.generator_mn2_service import quote_generation

        q = quote_generation(
            duration=int(cfg.get("duration_sec") or 120),
            tier={"fast_ai": "express", "ultra": "ultra", "premium": "premium"}.get(tier, "premium"),
            config=cfg,
        )
        base = float(q.get("price_mn2") or 0)
        podcast = 0.02 if (cfg.get("include_podcast") or pkg.get("targets", {}).get("podcast")) else 0.0
        price = round(base + podcast, 8)
        return {
            "success": True,
            "kind": k,
            "price_mn2": price,
            "currency": "MN2",
            "charged": price > 0,
            "encode_package": pkg,
            "tier": tier,
        }

    if k == "customer_fulfillment":
        return {
            "success": True,
            "kind": k,
            "price_mn2": 0.0,
            "currency": "MN2",
            "charged": False,
            "label": "Discord customer aggregator fulfillment",
        }

    return {"success": False, "error": "unhandled_kind"}


def _debit_with_ledger(user_id: str, amount: float, meta: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    if amount <= 0:
        return {"success": True, "amount": 0.0, "skipped": True}

    points_result = unified_points_db.get_all_points(user_id)
    if not points_result.get("success", True):
        return {"success": False, "error": "balance_load_failed"}
    pts = points_result.get("points", {}) or {}
    balance = float(pts.get("mn2_balance", 0) or 0)
    if balance == 0 and isinstance(pts.get("systems"), dict):
        balance = float(pts["systems"].get("mn2_balance", 0) or 0)
    if balance < amount:
        return {
            "success": False,
            "error": "insufficient_mn2",
            "price_mn2": amount,
            "mn2_balance": balance,
        }

    result = unified_points_db.add_points(
        user_id,
        "mn2_balance",
        -amount,
        source="encoder_payment",
        metadata=meta,
    )
    if not result.get("success", True):
        return {"success": False, "error": result.get("error") or "debit_failed"}

    try:
        append_entry(
            user_id=user_id,
            entry_type="encoder_payment",
            amount=amount,
            metadata=meta,
        )
    except Exception:
        pass
    new_pts = unified_points_db.get_all_points(user_id).get("points", {}) or {}
    return {
        "success": True,
        "amount": amount,
        "mn2_balance": float(new_pts.get("mn2_balance", 0) or 0),
    }


def create_balance_order(
    user_id: str,
    kind: str,
    config: Optional[Dict[str, Any]] = None,
    *,
    auto_fulfill: bool = True,
) -> Dict[str, Any]:
    if not encoder_orders_enabled():
        return {"success": True, "skipped": True, "reason": "encoder_orders_disabled"}

    cfg = dict(config or {})
    k = str(kind or "").strip().lower()
    quote = quote_order(k, cfg)
    if not quote.get("success"):
        return quote

    price = float(quote.get("price_mn2") or 0)
    order_id = _new_order_id()
    meta = {
        "order_id": order_id,
        "kind": k,
        "reference": f"encoder-order:{order_id}",
        **{key: cfg.get(key) for key in ("doc_id", "app_id", "upgrade_id", "tier") if cfg.get(key)},
    }

    debit = _debit_with_ledger(user_id, price, meta)
    if not debit.get("success") and price > 0:
        return debit

    order = {
        "order_id": order_id,
        "user_id": user_id,
        "kind": k,
        "status": "paid" if price > 0 else "free",
        "amount_mn2": price,
        "payment_method": "balance",
        "config": cfg,
        "quote": quote,
        "created_at": _iso(),
        "fulfilled_at": None,
        "fulfillment": None,
        "ledger_entry_type": "encoder_payment",
    }

    with _LOCK:
        store = _load_store()
        store.setdefault("orders", []).append(order)
        _save_store(store)

    if auto_fulfill:
        return fulfill_order(order_id)
    return {"success": True, "order": order, "charged": price > 0}


def create_onchain_order(
    user_id: str,
    kind: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not encoder_orders_enabled():
        return {"success": False, "error": "encoder_orders_disabled"}

    cfg = dict(config or {})
    k = str(kind or "").strip().lower()
    quote = quote_order(k, cfg)
    if not quote.get("success"):
        return quote

    price = float(quote.get("price_mn2") or 0)
    if price <= 0:
        return create_balance_order(user_id, k, cfg, auto_fulfill=True)

    try:
        from backend.services.mn2_rpc_client import getnewaddress

        r = getnewaddress()
        if r.get("error"):
            return {"success": False, "error": r.get("error", "address_failed")}
        address = (r.get("result") or "").strip()
        if not address:
            return {"success": False, "error": "no_address"}
    except Exception as exc:
        return {"success": False, "error": str(exc)[:120]}

    order_id = _new_order_id()
    item_name = f"Encoder {k.replace('_', ' ')}"
    from backend.services.mn2_order_payment_service import create_order_payment

    onchain = create_order_payment(
        user_id=user_id,
        item_id=order_id,
        item_name=item_name,
        quantity=1,
        price_coins=0,
        price_mn2=price,
        address=address,
        product="encoder",
    )
    onchain["encoder_order_id"] = order_id
    onchain["encoder_kind"] = k
    onchain["encoder_config"] = cfg

    order = {
        "order_id": order_id,
        "user_id": user_id,
        "kind": k,
        "status": "pending_onchain",
        "amount_mn2": price,
        "payment_method": "onchain",
        "payment_ref": onchain.get("payment_ref"),
        "address": address,
        "config": cfg,
        "quote": quote,
        "created_at": _iso(),
        "fulfilled_at": None,
        "fulfillment": None,
    }
    with _LOCK:
        store = _load_store()
        store.setdefault("orders", []).append(order)
        _save_store(store)

    return {
        "success": True,
        "order": order,
        "onchain": onchain,
        "payment_ref": onchain.get("payment_ref"),
        "address": address,
        "amount_mn2": price,
        "expires_at": onchain.get("expires_at"),
    }


def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    oid = str(order_id or "").strip()
    for row in _load_store().get("orders") or []:
        if row.get("order_id") == oid:
            return row
    return None


def list_orders(user_id: str, *, limit: int = 50) -> Dict[str, Any]:
    rows = [
        o for o in (_load_store().get("orders") or [])
        if o.get("user_id") == user_id
    ]
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return {"success": True, "orders": rows[:limit], "total": len(rows)}


def fulfill_order(order_id: str) -> Dict[str, Any]:
    oid = str(order_id or "").strip()
    with _LOCK:
        store = _load_store()
        orders = store.get("orders") or []
        idx = next((i for i, o in enumerate(orders) if o.get("order_id") == oid), None)
        if idx is None:
            return {"success": False, "error": "order_not_found", "order_id": oid}
        order = dict(orders[idx])
        if order.get("status") == "fulfilled":
            return {"success": True, "order": order, "duplicate": True}

        result = _dispatch_fulfillment(order)
        if not result.get("success"):
            order["status"] = "fulfillment_failed"
            order["fulfillment_error"] = result.get("error")
            orders[idx] = order
            store["orders"] = orders
            _save_store(store)
            return {**result, "order": order}

        order["status"] = "fulfilled"
        order["fulfilled_at"] = _iso()
        order["fulfillment"] = result
        orders[idx] = order
        store["orders"] = orders
        _save_store(store)
        return {"success": True, "order": order, "fulfillment": result}


def fulfill_onchain_payment(onchain_order: Dict[str, Any], txid: str, amount_received: float) -> Dict[str, Any]:
    """Called from mn2_order_payment_service when product=encoder is paid on-chain."""
    order_id = str(onchain_order.get("item_id") or onchain_order.get("encoder_order_id") or "").strip()
    order = get_order(order_id)
    if not order:
        return {"success": False, "error": "encoder_order_not_found", "order_id": order_id}

    with _LOCK:
        store = _load_store()
        orders = store.get("orders") or []
        for i, row in enumerate(orders):
            if row.get("order_id") != order_id:
                continue
            row = dict(row)
            row["status"] = "paid"
            row["txid"] = txid
            row["amount_received"] = amount_received
            orders[i] = row
            store["orders"] = orders
            _save_store(store)
            break

    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            user_id=order.get("user_id") or "",
            entry_type="encoder_payment",
            amount=float(amount_received or order.get("amount_mn2") or 0),
            txid=txid,
            address=onchain_order.get("address"),
            metadata={
                "order_id": order_id,
                "kind": order.get("kind"),
                "onchain": True,
                "payment_ref": onchain_order.get("payment_ref"),
            },
        )
    except Exception:
        pass

    return fulfill_order(order_id)


def _dispatch_fulfillment(order: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(order.get("kind") or "")
    cfg = dict(order.get("config") or {})
    user_id = str(order.get("user_id") or "")

    if kind == "encoder_v2_unlock":
        from backend.services.encoder_upgrade_service import unlock_upgrade

        upgrade_id = str(cfg.get("upgrade_id") or "")
        if not upgrade_id:
            return {"success": False, "error": "upgrade_id_required"}
        res = unlock_upgrade(user_id, upgrade_id)
        if not res.get("success"):
            return res
        res["order_fulfilled"] = True
        return res

    if kind == "generator_encode":
        doc_id = str(cfg.get("doc_id") or "")
        if not doc_id:
            return {"success": False, "error": "doc_id_required"}
        from backend.services.generator_mn2_service import _load_charges, _save_charges

        charges = _load_charges()
        charges[doc_id] = {
            "user_id": user_id,
            "amount": float(order.get("amount_mn2") or 0),
            "tier": cfg.get("tier") or "premium",
            "charged_at": _iso(),
            "refunded": False,
            "earned": False,
            "encoder_order_id": order.get("order_id"),
        }
        _save_charges(charges)
        return {"success": True, "doc_id": doc_id, "charged_via_order": True}

    if kind in ("create_app_encode", "super_encode"):
        app_id = str(cfg.get("app_id") or "")
        if not app_id:
            return {"success": False, "error": "app_id_required"}
        from backend.services.create_app_service import _load_apps, _save_apps
        from backend.services.create_app_encode_service import start_encode_jobs_for_app

        data = _load_apps()
        app = next(
            (a for a in (data.get("apps") or []) if a.get("id") == app_id and a.get("user_id") == user_id),
            None,
        )
        if not app:
            return {"success": False, "error": "app_not_found", "app_id": app_id}
        enc = start_encode_jobs_for_app(user_id, app, force=bool(cfg.get("force")))
        app["encode_jobs"] = enc.get("encode_jobs") or {}
        app["encoder_order_id"] = order.get("order_id")
        for i, row in enumerate(data.get("apps") or []):
            if row.get("id") == app_id:
                data["apps"][i] = app
                break
        _save_apps(data)
        return {"success": True, "app_id": app_id, **enc}

    if kind == "customer_fulfillment":
        from backend.services.encoder_customer_fulfillment_service import fulfill_single_customer
        from backend.services.discord_customer_ingest_service import list_discord_customers

        discord_meta = None
        discord_id = str(cfg.get("discord_id") or "")
        if discord_id:
            try:
                from backend.services.discord_customer_ingest_service import _load_index

                discord_meta = (_load_index().get("customers") or {}).get(discord_id)
            except Exception:
                pass
        if not discord_meta:
            for row in (list_discord_customers(limit=5000).get("customers") or []):
                if row.get("user_id") == user_id:
                    discord_meta = row
                    break
        res = fulfill_single_customer(user_id, discord_meta=discord_meta, skip_if_done=False)
        if not res.get("success"):
            return res
        return {"success": True, "customer_fulfillment": res, "order_fulfilled": True}

    return {"success": False, "error": "unhandled_fulfillment", "kind": kind}
