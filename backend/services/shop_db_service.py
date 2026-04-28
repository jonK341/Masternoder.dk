"""
Shop Database Service
Read/write shop_items, shop_purchases, user_inventory. Safe when migration not run (no tables).

When `shop_items` table is missing, purchases + inventory persist under logs/shop_file_mode/
so Shop v4 and profile can still show owned items.
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import text, inspect

# Lazy imports to avoid circular deps; assume called within Flask app context
def _get_db():
    from src.db.models import db
    return db


class ShopFulfillmentError(RuntimeError):
    """Raised when a paid shop item cannot be attached to a user's inventory."""


def shop_tables_exist() -> bool:
    """Return True if shop_items table exists (migration has been run)."""
    try:
        db = _get_db()
        inspector = inspect(db.engine)
        return 'shop_items' in inspector.get_table_names()
    except Exception:
        return False


def get_shop_storage_info() -> Dict[str, Any]:
    """
    Ops/health: DB-backed shop vs JSON fallback under shop_file_mode/.

    If migrations are not applied, purchases and inventory persist as JSON (fine for
    single-node recovery; use DB mode for backups and multi-server).
    """
    try:
        if shop_tables_exist():
            return {"mode": "database", "migrations_applied": True}
        root = _shop_file_root()
        return {
            "mode": "file",
            "migrations_applied": False,
            "persistence_path": root,
            "hint": "Apply shop migrations (e.g. python scripts/shop_purchase_migration.py --standalone) for durable catalog/inventory.",
        }
    except Exception as e:
        return {"mode": "unknown", "error": str(e)}


def _safe_uid(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", (user_id or "unknown").strip())[:200] or "unknown"


def _shop_file_root() -> str:
    base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    root = os.path.join(base, "shop_file_mode")
    os.makedirs(root, exist_ok=True)
    os.makedirs(os.path.join(root, "inventory"), exist_ok=True)
    os.makedirs(os.path.join(root, "purchases"), exist_ok=True)
    return root


def _inventory_file_path(user_id: str) -> str:
    return os.path.join(_shop_file_root(), "inventory", f"{_safe_uid(user_id)}.json")


def _purchases_file_path(user_id: str) -> str:
    return os.path.join(_shop_file_root(), "purchases", f"{_safe_uid(user_id)}.json")


def _read_json_file(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json_file(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def get_shop_items_from_db() -> Optional[List[Dict[str, Any]]]:
    """
    Return list of shop items from DB in same shape as _seed_shop_items().
    Returns None if table missing or empty (caller should use _seed_shop_items).
    """
    if not shop_tables_exist():
        return None
    try:
        db = _get_db()
        rows = db.session.execute(
            text("SELECT id, name, description, category, price_type, price_coins, price_points, icon, rarity FROM shop_items WHERE is_active = 1")
        ).fetchall()
        if not rows:
            return None
        items = []
        for r in rows:
            price = r.price_coins if r.price_type == 'coins' else (json.loads(r.price_points) if r.price_points else 0)
            items.append({
                'id': r.id,
                'name': r.name,
                'description': r.description or '',
                'category': r.category,
                'price': price,
                'icon': r.icon or '🛍️',
                'rarity': r.rarity or 'common',
            })
        return items
    except Exception:
        return None


def _record_purchase_file(
    user_id: str,
    item_id: str,
    item_name: str,
    quantity: int,
    price_type: str,
    price_paid_coins: int,
    price_paid_points: Optional[Dict] = None,
    balance_before: Optional[Dict] = None,
    balance_after: Optional[Dict] = None,
) -> Optional[int]:
    path = _purchases_file_path(user_id)
    data = _read_json_file(path, {"purchases": []})
    purchases = data.get("purchases") if isinstance(data, dict) else []
    if not isinstance(purchases, list):
        purchases = []
    next_id = 1
    for p in purchases:
        if not isinstance(p, dict):
            continue
        try:
            next_id = max(next_id, int(p.get("id") or 0) + 1)
        except (TypeError, ValueError):
            pass
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": next_id,
        "user_id": user_id,
        "item_id": item_id,
        "item_name": item_name,
        "quantity": quantity,
        "price_type": price_type,
        "price_paid_coins": int(price_paid_coins or 0),
        "price_paid_points": price_paid_points,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "purchase_status": "completed",
        "created_at": now,
    }
    purchases.insert(0, row)
    data = {"purchases": purchases[:500]}
    if _write_json_file(path, data):
        return next_id
    return None


def record_purchase(
    user_id: str,
    item_id: str,
    item_name: str,
    quantity: int,
    price_type: str,
    price_paid_coins: int,
    price_paid_points: Optional[Dict] = None,
    balance_before: Optional[Dict] = None,
    balance_after: Optional[Dict] = None,
) -> Optional[int]:
    """
    Insert into shop_purchases. Returns purchase_id or None if table missing/error.
    When DB tables are missing, uses logs/shop_file_mode/*.json.
    """
    if not shop_tables_exist():
        return _record_purchase_file(
            user_id, item_id, item_name, quantity, price_type,
            price_paid_coins, price_paid_points, balance_before, balance_after,
        )
    try:
        db = _get_db()
        db.session.execute(
            text("""
                INSERT INTO shop_purchases 
                (user_id, item_id, item_name, quantity, price_type, price_paid_coins, price_paid_points, balance_before, balance_after)
                VALUES (:user_id, :item_id, :item_name, :quantity, :price_type, :price_paid_coins, :price_paid_points, :balance_before, :balance_after)
            """),
            {
                'user_id': user_id,
                'item_id': item_id,
                'item_name': item_name,
                'quantity': quantity,
                'price_type': price_type,
                'price_paid_coins': price_paid_coins,
                'price_paid_points': json.dumps(price_paid_points) if price_paid_points else None,
                'balance_before': json.dumps(balance_before) if balance_before else None,
                'balance_after': json.dumps(balance_after) if balance_after else None,
            }
        )
        row = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
        db.session.commit()
        return row
    except Exception:
        try:
            db = _get_db()
            db.session.rollback()
        except Exception:
            pass
        return None


def _add_to_inventory_file(
    user_id: str, item_id: str, item_name: str, quantity: int, purchase_id: Optional[int] = None,
) -> bool:
    path = _inventory_file_path(user_id)
    data = _read_json_file(path, {"items": []})
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []
    now = datetime.now(timezone.utc).isoformat()
    found = False
    for i in items:
        if isinstance(i, dict) and i.get("item_id") == item_id:
            i["quantity"] = int(i.get("quantity") or 0) + int(quantity)
            i["item_name"] = item_name
            i["updated_at"] = now
            if purchase_id is not None:
                i["last_purchase_id"] = purchase_id
            found = True
            break
    if not found:
        items.append({
            "item_id": item_id,
            "item_name": item_name,
            "quantity": int(quantity),
            "last_purchase_id": purchase_id,
            "created_at": now,
            "updated_at": now,
        })
    return _write_json_file(path, {"items": items})


def _reserve_inventory_file(user_id: str, item_id: str, quantity: int) -> Optional[Dict[str, Any]]:
    path = _inventory_file_path(user_id)
    data = _read_json_file(path, {"items": []})
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return None
    qty = int(quantity or 0)
    if qty <= 0:
        return None
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("item_id") != item_id:
            continue
        current = int(item.get("quantity") or 0)
        if current < qty:
            return None
        item_name = item.get("item_name") or item_id
        remaining = current - qty
        if remaining > 0:
            item["quantity"] = remaining
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            items.pop(idx)
        if _write_json_file(path, {"items": items}):
            return {"item_id": item_id, "item_name": item_name, "quantity": qty}
        return None
    return None


def add_to_inventory(user_id: str, item_id: str, item_name: str, quantity: int, purchase_id: Optional[int] = None) -> bool:
    """
    Insert or increment user_inventory. Returns True on success.
    """
    if not shop_tables_exist():
        return _add_to_inventory_file(user_id, item_id, item_name, quantity, purchase_id)
    try:
        db = _get_db()
        existing = db.session.execute(
            text("SELECT id, quantity FROM user_inventory WHERE user_id = :user_id AND item_id = :item_id"),
            {'user_id': user_id, 'item_id': item_id}
        ).fetchone()
        if existing:
            db.session.execute(
                text("UPDATE user_inventory SET quantity = quantity + :qty, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id AND item_id = :item_id"),
                {'qty': quantity, 'user_id': user_id, 'item_id': item_id}
            )
        else:
            db.session.execute(
                text("""
                    INSERT INTO user_inventory (user_id, item_id, item_name, quantity, purchase_id)
                    VALUES (:user_id, :item_id, :item_name, :quantity, :purchase_id)
                """),
                {'user_id': user_id, 'item_id': item_id, 'item_name': item_name, 'quantity': quantity, 'purchase_id': purchase_id}
            )
        db.session.commit()
        return True
    except Exception:
        try:
            db = _get_db()
            db.session.rollback()
        except Exception:
            pass
        return False


def reserve_inventory(user_id: str, item_id: str, quantity: int) -> Optional[Dict[str, Any]]:
    """
    Remove quantity from a user's active inventory and return the reserved item.

    Used by marketplace listings so a seller cannot list the same item twice.
    Call add_to_inventory() to restore the item if the listing is cancelled.
    """
    qty = int(quantity or 0)
    if qty <= 0:
        return None
    if not shop_tables_exist():
        return _reserve_inventory_file(user_id, item_id, qty)
    try:
        db = _get_db()
        row = db.session.execute(
            text("SELECT item_name, quantity FROM user_inventory WHERE user_id = :user_id AND item_id = :item_id AND is_active = 1"),
            {'user_id': user_id, 'item_id': item_id}
        ).fetchone()
        if not row or int(row.quantity or 0) < qty:
            return None
        remaining = int(row.quantity or 0) - qty
        if remaining > 0:
            db.session.execute(
                text("UPDATE user_inventory SET quantity = :qty, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id AND item_id = :item_id"),
                {'qty': remaining, 'user_id': user_id, 'item_id': item_id}
            )
        else:
            db.session.execute(
                text("UPDATE user_inventory SET quantity = 0, is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id AND item_id = :item_id"),
                {'user_id': user_id, 'item_id': item_id}
            )
        db.session.commit()
        return {"item_id": item_id, "item_name": row.item_name or item_id, "quantity": qty}
    except Exception:
        try:
            db = _get_db()
            db.session.rollback()
        except Exception:
            pass
        return None


def fulfill_shop_purchase(
    *,
    user_id: str,
    item_id: str,
    item_name: str,
    quantity: int,
    price_type: str,
    price_paid_coins: int,
    price_paid_points: Optional[Dict] = None,
    balance_before: Optional[Dict] = None,
    balance_after: Optional[Dict] = None,
) -> int:
    """
    Record a completed purchase and attach the item to the user's inventory.

    Payment providers should use this helper instead of calling record_purchase()
    and add_to_inventory() independently, because a paid checkout is not fulfilled
    until both the audit row and inventory row exist.
    """
    purchase_id = record_purchase(
        user_id=user_id,
        item_id=item_id,
        item_name=item_name,
        quantity=quantity,
        price_type=price_type,
        price_paid_coins=price_paid_coins,
        price_paid_points=price_paid_points,
        balance_before=balance_before,
        balance_after=balance_after,
    )
    if not purchase_id:
        raise ShopFulfillmentError(f"Could not record purchase for {item_id}")

    if not add_to_inventory(
        user_id=user_id,
        item_id=item_id,
        item_name=item_name,
        quantity=quantity,
        purchase_id=purchase_id,
    ):
        raise ShopFulfillmentError(f"Could not add {item_id} to inventory")

    return int(purchase_id)


def get_purchases(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return purchase history for user. Empty list if table missing."""
    if not shop_tables_exist():
        return _get_purchases_file(user_id, limit)
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT id, item_id, item_name, quantity, price_type, price_paid_coins, price_paid_points, purchase_status, created_at
                FROM shop_purchases WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit
            """),
            {'user_id': user_id, 'limit': limit}
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                'id': r.id,
                'item_id': r.item_id,
                'item_name': r.item_name,
                'quantity': r.quantity,
                'price_type': r.price_type,
                'price_paid_coins': r.price_paid_coins,
                'price_paid_points': json.loads(r.price_paid_points) if r.price_paid_points else None,
                'purchase_status': r.purchase_status,
                'created_at': r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at),
            })
        return out
    except Exception:
        return []


def _get_purchases_file(user_id: str, limit: int) -> List[Dict[str, Any]]:
    path = _purchases_file_path(user_id)
    data = _read_json_file(path, {"purchases": []})
    purchases = data.get("purchases") if isinstance(data, dict) else []
    if not isinstance(purchases, list):
        return []
    out: List[Dict[str, Any]] = []
    for p in purchases[: max(1, min(limit, 100))]:
        if not isinstance(p, dict):
            continue
        pp = p.get("price_paid_points")
        if isinstance(pp, dict):
            pp_out = pp
        else:
            pp_out = pp
        out.append({
            "id": p.get("id"),
            "item_id": p.get("item_id"),
            "item_name": p.get("item_name"),
            "quantity": p.get("quantity"),
            "price_type": p.get("price_type"),
            "price_paid_coins": p.get("price_paid_coins"),
            "price_paid_points": pp_out,
            "purchase_status": p.get("purchase_status") or "completed",
            "created_at": p.get("created_at", ""),
        })
    return out


def get_inventory(user_id: str) -> List[Dict[str, Any]]:
    """Return user inventory. Empty list if table missing."""
    if not shop_tables_exist():
        return _get_inventory_file(user_id)
    try:
        db = _get_db()
        rows = db.session.execute(
            text("SELECT item_id, item_name, quantity, is_active, created_at FROM user_inventory WHERE user_id = :user_id AND is_active = 1"),
            {'user_id': user_id}
        ).fetchall()
        return [
            {
                'item_id': r.item_id,
                'item_name': r.item_name,
                'quantity': r.quantity,
                'is_active': bool(r.is_active),
                'created_at': r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at),
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_inventory_file(user_id: str) -> List[Dict[str, Any]]:
    path = _inventory_file_path(user_id)
    data = _read_json_file(path, {"items": []})
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for i in items:
        if not isinstance(i, dict):
            continue
        out.append({
            "item_id": i.get("item_id"),
            "item_name": i.get("item_name"),
            "quantity": int(i.get("quantity") or 0),
            "is_active": True,
            "created_at": i.get("created_at") or i.get("updated_at") or "",
        })
    return out


# ---------- Phase 5: Analytics ----------

def get_analytics_popular_items(limit: int = 10) -> List[Dict[str, Any]]:
    """Most purchased items by quantity sold. Empty if table missing."""
    if not shop_tables_exist():
        return []
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT item_id, item_name, SUM(quantity) AS total_qty, COUNT(*) AS purchase_count
                FROM shop_purchases WHERE purchase_status = 'completed'
                GROUP BY item_id, item_name ORDER BY total_qty DESC LIMIT :limit
            """),
            {'limit': limit}
        ).fetchall()
        return [{'item_id': r.item_id, 'item_name': r.item_name, 'total_quantity': r.total_qty, 'purchase_count': r.purchase_count} for r in rows]
    except Exception:
        return []


def get_analytics_revenue_by_item() -> List[Dict[str, Any]]:
    """Revenue (coins) per item from completed purchases."""
    if not shop_tables_exist():
        return []
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT item_id, item_name, SUM(price_paid_coins) AS total_coins, SUM(quantity) AS total_qty
                FROM shop_purchases WHERE purchase_status = 'completed' AND price_type = 'coins'
                GROUP BY item_id, item_name ORDER BY total_coins DESC
            """)
        ).fetchall()
        return [{'item_id': r.item_id, 'item_name': r.item_name, 'total_coins': r.total_coins or 0, 'total_quantity': r.total_qty} for r in rows]
    except Exception:
        return []


def get_analytics_revenue_by_category(days: Optional[int] = None) -> List[Dict[str, Any]]:
    """Revenue by category (join shop_items for category). Optional days limit (None = all time)."""
    if not shop_tables_exist():
        return []
    try:
        db = _get_db()
        modifier = f'-{days} days' if days is not None else '-99999 days'
        rows = db.session.execute(
            text("""
                SELECT i.category, SUM(p.price_paid_coins) AS total_coins, SUM(p.quantity) AS total_qty
                FROM shop_purchases p
                JOIN shop_items i ON i.id = p.item_id
                WHERE p.purchase_status = 'completed' AND p.price_type = 'coins'
                  AND p.created_at >= datetime('now', :modifier)
                GROUP BY i.category ORDER BY total_coins DESC
            """),
            {'modifier': modifier}
        ).fetchall()
        return [{'category': r.category, 'total_coins': r.total_coins or 0, 'total_quantity': r.total_qty} for r in rows]
    except Exception:
        return []


def get_analytics_user_spending(user_id: str) -> Dict[str, Any]:
    """Total spending (coins + count) for one user."""
    if not shop_tables_exist():
        return {'total_coins': 0, 'purchase_count': 0, 'total_quantity': 0}
    try:
        db = _get_db()
        row = db.session.execute(
            text("""
                SELECT COALESCE(SUM(price_paid_coins), 0) AS total_coins, COUNT(*) AS purchase_count, COALESCE(SUM(quantity), 0) AS total_quantity
                FROM shop_purchases WHERE user_id = :user_id AND purchase_status = 'completed'
            """),
            {'user_id': user_id}
        ).fetchone()
        return {'total_coins': row.total_coins or 0, 'purchase_count': row.purchase_count or 0, 'total_quantity': row.total_quantity or 0}
    except Exception:
        return {'total_coins': 0, 'purchase_count': 0, 'total_quantity': 0}


def get_analytics_refund_stats() -> Dict[str, Any]:
    """Refund rate and counts (completed vs refunded)."""
    if not shop_tables_exist():
        return {'total': 0, 'completed': 0, 'refunded': 0, 'refund_rate': 0.0}
    try:
        db = _get_db()
        row = db.session.execute(
            text("""
                SELECT COUNT(*) AS total,
                    SUM(CASE WHEN purchase_status = 'completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN purchase_status = 'refunded' THEN 1 ELSE 0 END) AS refunded
                FROM shop_purchases
            """)
        ).fetchone()
        total = row.total or 0
        completed = row.completed or 0
        refunded = row.refunded or 0
        return {
            'total': total,
            'completed': completed,
            'refunded': refunded,
            'refund_rate': round(refunded / total, 4) if total else 0.0,
        }
    except Exception:
        return {'total': 0, 'completed': 0, 'refunded': 0, 'refund_rate': 0.0}
