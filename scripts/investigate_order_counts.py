#!/usr/bin/env python3
"""Summarize shop vs masternode hosting order counts and payment rails (read-only)."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_hosting_orders() -> list:
    path = ROOT / "data" / "mn2_masternode_orders.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        orders = data.get("orders")
        if isinstance(orders, dict):
            return [o for o in orders.values() if isinstance(o, dict)]
        if isinstance(orders, list):
            return [o for o in orders if isinstance(o, dict)]
    return []


def _shop_purchase_counts() -> dict:
    db = ROOT / "instance" / "database.db"
    out = {"total": 0, "by_price_type": {}, "by_user": 0}
    if not db.is_file():
        return out
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        out["total"] = cur.execute("SELECT COUNT(*) FROM shop_purchases").fetchone()[0]
        out["by_price_type"] = dict(
            cur.execute(
                "SELECT COALESCE(price_type, 'unknown'), COUNT(*) FROM shop_purchases GROUP BY price_type"
            ).fetchall()
        )
        out["by_user"] = cur.execute("SELECT COUNT(DISTINCT user_id) FROM shop_purchases").fetchone()[0]
        conn.close()
    except sqlite3.Error:
        pass
    return out


def main() -> int:
    hosting = _load_hosting_orders()
    hosting_status = Counter(str(o.get("status") or "").lower() for o in hosting)
    hosting_paid_methods = Counter(
        str(o.get("payment_method") or "paypal").lower()
        for o in hosting
        if str(o.get("status") or "").lower() == "paid"
    )
    hosting_users = len({str(o.get("user_id") or "") for o in hosting if o.get("user_id")})

    shop = _shop_purchase_counts()

    try:
        from backend.services.mn2_masternode_hosting_service import hosting_stats

        site_stats = hosting_stats()
    except Exception as exc:
        site_stats = {"error": str(exc)}

    report = {
        "shop_purchases_sqlite": shop,
        "hosting_orders_json": {
            "total_records": len(hosting),
            "by_status": dict(hosting_status),
            "paid_by_payment_method": dict(hosting_paid_methods),
            "unique_users": hosting_users,
        },
        "hosting_stats_service": site_stats,
        "payment_rails": {
            "shop_catalog": ["coins", "credits", "unified_points", "points", "paypal", "mn2", "mn2_onchain"],
            "shop_stall": ["coins"],
            "masternode_hosting": ["paypal", "coins", "credits", "mn2", "mn2_onchain"],
        },
        "note": (
            "Shop 'My orders' shop panel = per-user catalog purchases only. "
            "Site-wide paid_orders in hosting_stats are masternode hosting slots, not missing shop rows."
        ),
    }

    out_dir = Path(os.environ.get("ARTIFACT_DIR", "/opt/cursor/artifacts"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "order-counts-investigation.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nWrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
