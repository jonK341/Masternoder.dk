#!/usr/bin/env python3
"""Export site-wide finished shop + hosting orders to /opt/cursor/artifacts/."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "/opt/cursor/artifacts"))
CACHE_DIR = ARTIFACT_DIR / "_prod_cache"
PAYPAL_LOG_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\] PURCHASE \| amount=(?P<amount>[^\s]+) (?P<currency>\S+) \| "
    r"item=(?P<item_id>[^\s]+) \((?P<item_name>[^)]*)\) \| user=(?P<user_id>[^|]+) \| "
    r"order=(?P<order_id>[^|]+) \| coins_granted=(?P<coins>\d+) \| source=(?P<source>\S+)"
)

FINISHED_STATUSES = frozenset(
    {"completed", "captured", "paid", "fulfilled", "sold", "bought", "confirmed"}
)
SKIP_STATUSES = frozenset(
    {"pending", "pending_payment", "quoted", "unpaid", "awaiting", "processing", "active", "listed", "reserved",
     "cancelled", "canceled", "expired", "failed", "refunded"}
)

PROD_REMOTE_PATHS = {
    "hosting_orders": "/var/www/html/data/mn2_masternode_orders.json",
    "onchain_orders": "/var/www/html/data/mn2_order_payments.json",
    "shop_db": "/var/www/html/instance/database.db",
    "paypal_log": "/var/www/html/logs/purchase_notifications.log",
    "auction_listings": "/var/www/html/logs/shop_marketplace/auction_listings.json",
    "exchange_purchases": "/var/www/html/data/crypto_exchange/exchange_shop_purchases.jsonl",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def redact_user_id(user_id: Optional[str]) -> str:
    uid = str(user_id or "").strip()
    if not uid:
        return "—"
    if len(uid) <= 6:
        return uid[:2] + "***"
    return f"{uid[:4]}***{uid[-2:]}"


def is_finished(status: Optional[str]) -> bool:
    raw = str(status or "completed").strip().lower()
    if raw in SKIP_STATUSES:
        return False
    if raw in FINISHED_STATUSES:
        return True
    return raw not in SKIP_STATUSES and raw != ""


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _hosting_orders_from_blob(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        if isinstance(data.get("orders"), dict):
            return [o for o in data["orders"].values() if isinstance(o, dict)]
        if isinstance(data.get("orders"), list):
            return [o for o in data["orders"] if isinstance(o, dict)]
        return [o for o in data.values() if isinstance(o, dict) and ("status" in o or "order_id" in o)]
    if isinstance(data, list):
        return [o for o in data if isinstance(o, dict)]
    return []


def try_fetch_vps() -> Dict[str, Any]:
    """Best-effort read-only fetch from deploy VPS. Never commits to git."""
    report: Dict[str, Any] = {"attempted": True, "ok": False, "files": {}, "error": None}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from deploy_ssh_env import connect_deploy_ssh

        ssh, method, _pw = connect_deploy_ssh()
        report["auth_method"] = method
        sftp = ssh.open_sftp()
        for key, remote in PROD_REMOTE_PATHS.items():
            local = CACHE_DIR / key.replace("/", "_")
            try:
                sftp.get(remote, str(local))
                report["files"][key] = {"remote": remote, "local": str(local), "bytes": local.stat().st_size}
            except OSError as exc:
                report["files"][key] = {"remote": remote, "error": str(exc)}
        sftp.close()
        ssh.close()
        report["ok"] = any(f.get("bytes", 0) > 0 for f in report["files"].values())
    except SystemExit:
        report["error"] = "ssh_auth_failed"
    except Exception as exc:
        report["error"] = str(exc)
    return report


def _data_path(name: str) -> Path:
    cached = CACHE_DIR / name.replace("/", "_")
    if cached.is_file():
        return cached
    return ROOT / "data" / name


def _shop_db_path() -> Path:
    cached = CACHE_DIR / "shop_db"
    if cached.is_file():
        return cached
    return ROOT / "instance" / "database.db"


def _paypal_log_path() -> Path:
    cached = CACHE_DIR / "paypal_log"
    if cached.is_file():
        return cached
    return ROOT / "logs" / "purchase_notifications.log"


def _auction_path() -> Path:
    cached = CACHE_DIR / "auction_listings"
    if cached.is_file():
        return cached
    log_root = os.environ.get("MASTERNODER_LOG_DIR") or str(ROOT / "logs")
    return Path(log_root) / "shop_marketplace" / "auction_listings.json"


def collect_shop_sqlite() -> List[Dict[str, Any]]:
    db = _shop_db_path()
    if not db.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, item_id, item_name, quantity, price_type,
                   price_paid_coins, price_paid_points, purchase_status, created_at
            FROM shop_purchases
            ORDER BY created_at DESC
            """
        )
        for r in cur.fetchall():
            status = str(r["purchase_status"] or "completed")
            if not is_finished(status):
                continue
            pts = r["price_paid_points"]
            if isinstance(pts, str) and pts.strip():
                try:
                    pts = json.loads(pts)
                except json.JSONDecodeError:
                    pts = {}
            rows.append({
                "source": "shop",
                "order_id": str(r["id"]),
                "user_id": str(r["user_id"] or ""),
                "item": str(r["item_name"] or r["item_id"] or ""),
                "qty": int(r["quantity"] or 1),
                "amount": _amount_shop(r["price_type"], r["price_paid_coins"], pts),
                "payment_method": _normalize_payment(r["price_type"]),
                "status": status,
                "date": str(r["created_at"] or ""),
                "origin": "shop_db",
            })
        conn.close()
    except sqlite3.Error:
        pass
    return rows


def _normalize_payment(raw: Optional[str]) -> str:
    pt = str(raw or "").strip().lower()
    mapping = {
        "paypal": "PayPal",
        "paypal_mn2_hosting": "PayPal",
        "coins": "Coins",
        "credits": "Coins",
        "mn2": "MN2",
        "mn2_onchain": "MN2 on-chain",
        "unified_points": "Points",
        "points": "Points",
        "exchange": "Exchange",
    }
    return mapping.get(pt, pt.replace("_", " ").title() if pt else "—")


def _amount_shop(price_type: Optional[str], coins: Any, points: Any) -> str:
    pt = str(price_type or "").lower()
    if pt in ("coins", "credits"):
        return f"{int(coins or 0)} coins"
    if pt in ("mn2", "mn2_onchain"):
        if isinstance(points, dict) and points.get("mn2") is not None:
            return f"{float(points['mn2']):.4f} MN2"
        return "MN2"
    if pt in ("paypal", "paypal_mn2_hosting"):
        if isinstance(points, dict) and points.get("usd") is not None:
            return f"${float(points['usd']):.2f}"
        return "PayPal"
    if pt in ("points", "unified_points") and isinstance(points, dict) and points:
        k = next(iter(points))
        return f"{points[k]} {k}"
    if coins:
        return f"{int(coins)} coins"
    return "—"


def collect_shop_file_mode() -> List[Dict[str, Any]]:
    root = ROOT / "logs" / "shop_file_mode" / "purchases"
    if CACHE_DIR.is_dir():
        cached = CACHE_DIR / "shop_file_mode_purchases"
        if cached.is_dir():
            root = cached
    rows: List[Dict[str, Any]] = []
    if not root.is_dir():
        return rows
    for path in root.glob("*.json"):
        user_id = path.stem
        data = _read_json(path)
        items = data.get("purchases") if isinstance(data, dict) else data
        if not isinstance(items, list):
            continue
        for rec in items:
            if not isinstance(rec, dict):
                continue
            status = str(rec.get("purchase_status") or rec.get("status") or "completed")
            if not is_finished(status):
                continue
            rows.append({
                "source": "shop",
                "order_id": str(rec.get("id") or rec.get("purchase_id") or f"file:{path.name}:{rec.get('item_id')}"),
                "user_id": str(rec.get("user_id") or user_id),
                "item": str(rec.get("item_name") or rec.get("item_id") or ""),
                "qty": int(rec.get("quantity") or 1),
                "amount": _amount_shop(rec.get("price_type"), rec.get("price_paid_coins"), rec.get("price_paid_points")),
                "payment_method": _normalize_payment(rec.get("price_type")),
                "status": status,
                "date": str(rec.get("created_at") or ""),
                "origin": "shop_file_mode",
            })
    return rows


def collect_paypal_log() -> List[Dict[str, Any]]:
    path = _paypal_log_path()
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        m = PAYPAL_LOG_RE.search(line)
        if not m:
            continue
        item_id = str(m.group("item_id") or "").strip()
        blob = f"{item_id} {m.group('item_name') or ''}".lower()
        if "masternode" in blob or item_id.startswith("mnq_"):
            continue
        try:
            usd = float(m.group("amount"))
        except (TypeError, ValueError):
            usd = 0.0
        source = str(m.group("source") or "paypal").strip().lower()
        method = "PayPal" if source in ("paypal", "paypal_mn2_pack") else _normalize_payment(source)
        rows.append({
            "source": "shop",
            "order_id": str(m.group("order_id") or "").strip() or f"paypal-log:{item_id}",
            "user_id": str(m.group("user_id") or "").strip(),
            "item": str(m.group("item_name") or item_id).strip() or item_id,
            "qty": 1,
            "amount": f"${usd:.2f}" if usd else method,
            "payment_method": method,
            "status": "completed",
            "date": str(m.group("ts") or "").replace(" UTC", "Z"),
            "origin": "paypal_log",
        })
    return rows


def collect_onchain_shop() -> List[Dict[str, Any]]:
    data = _read_json(_data_path("mn2_order_payments.json"))
    orders: List[Dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("orders"), list):
        orders = data["orders"]
    elif isinstance(data, list):
        orders = data
    rows: List[Dict[str, Any]] = []
    for rec in orders:
        if not isinstance(rec, dict):
            continue
        if str(rec.get("product") or "shop") == "mn2_masternode_hosting":
            continue
        status = str(rec.get("status") or rec.get("purchase_status") or "pending").lower()
        if not is_finished(status):
            continue
        amt = rec.get("amount_mn2") or rec.get("amount_received")
        rows.append({
            "source": "shop",
            "order_id": str(rec.get("payment_ref") or rec.get("id") or rec.get("item_id") or ""),
            "user_id": str(rec.get("user_id") or ""),
            "item": str(rec.get("item_name") or rec.get("item_id") or "On-chain order"),
            "qty": int(rec.get("quantity") or 1),
            "amount": f"{float(amt or 0):.4f} MN2" if amt is not None else "MN2 on-chain",
            "payment_method": "MN2 on-chain",
            "status": status,
            "date": str(rec.get("fulfilled_at") or rec.get("created_at") or ""),
            "origin": "onchain_orders",
        })
    return rows


def collect_exchange_shop() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    jsonl = _data_path("crypto_exchange/exchange_shop_purchases.jsonl")
    if jsonl.is_file():
        for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            rows.append(_exchange_row(rec, origin="exchange_jsonl"))
    state_dir = ROOT / "data" / "crypto_exchange" / "exchange_shop"
    cached_state = CACHE_DIR / "exchange_shop"
    dirs = [p for p in (cached_state, state_dir) if p.is_dir()]
    for sdir in dirs:
        for path in sdir.glob("*.json"):
            user_id = path.stem
            data = _read_json(path)
            if not isinstance(data, dict):
                continue
            for rec in data.get("purchases") or []:
                if isinstance(rec, dict):
                    rec = dict(rec)
                    rec.setdefault("user_id", user_id)
                    rows.append(_exchange_row(rec, origin="exchange_state"))
    return rows


def _exchange_row(rec: Dict[str, Any], origin: str) -> Dict[str, Any]:
    mn2 = rec.get("price_mn2") or rec.get("spent_mn2") or 0
    return {
        "source": "shop",
        "order_id": f"exchange:{rec.get('item_id')}:{rec.get('ts') or rec.get('user_id')}",
        "user_id": str(rec.get("user_id") or ""),
        "item": str(rec.get("item_name") or rec.get("item_id") or ""),
        "qty": 1,
        "amount": f"{float(mn2 or 0):.4f} MN2",
        "payment_method": "MN2",
        "status": "completed",
        "date": str(rec.get("ts") or ""),
        "origin": origin,
    }


def collect_stall_sold() -> List[Dict[str, Any]]:
    data = _read_json(_auction_path())
    listings: List[Dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("listings"), list):
        listings = data["listings"]
    elif isinstance(data, list):
        listings = data
    rows: List[Dict[str, Any]] = []
    for rec in listings:
        if not isinstance(rec, dict):
            continue
        if str(rec.get("status") or "").lower() != "sold":
            continue
        rows.append({
            "source": "shop",
            "order_id": str(rec.get("listing_id") or rec.get("id") or ""),
            "user_id": str(rec.get("buyer_id") or rec.get("seller_id") or ""),
            "item": str(rec.get("item_name") or rec.get("item_id") or ""),
            "qty": int(rec.get("quantity") or 1),
            "amount": f"{int(rec.get('price_coins') or 0)} coins",
            "payment_method": "Coins",
            "status": "sold",
            "date": str(rec.get("sold_at") or rec.get("created_at") or ""),
            "origin": "stall",
        })
    return rows


def collect_hosting() -> List[Dict[str, Any]]:
    data = _read_json(_data_path("mn2_masternode_orders.json"))
    orders = _hosting_orders_from_blob(data)
    rows: List[Dict[str, Any]] = []
    for order in orders:
        status = str(order.get("status") or "").lower()
        if status != "paid":
            continue
        method = str(order.get("payment_method") or "paypal").lower()
        slots = int(order.get("slots") or 1)
        amount = "—"
        if method in ("coins", "credits"):
            amount = f"{int(order.get('coins_total') or 0)} coins"
        elif method in ("mn2", "mn2_onchain"):
            amount = f"{float(order.get('mn2_total') or 0):.4f} MN2"
        else:
            usd = order.get("usd_total")
            if usd is not None:
                amount = f"${float(usd):.2f}"
            else:
                amount = "PayPal"
        rows.append({
            "source": "hosting",
            "order_id": str(order.get("order_id") or order.get("id") or ""),
            "user_id": str(order.get("user_id") or ""),
            "item": f"Masternode hosting × {slots}",
            "qty": slots,
            "amount": amount,
            "payment_method": _normalize_payment(method),
            "status": status,
            "date": str(order.get("paid_at") or order.get("created_at") or ""),
            "origin": "hosting_json",
        })
    return rows


def _dedupe_key(row: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("source") or ""),
        str(row.get("order_id") or ""),
        str(row.get("user_id") or ""),
        str(row.get("date") or "")[:19],
    )


def merge_rows(chunks: Iterable[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for chunk in chunks:
        for row in chunk:
            key = _dedupe_key(row)
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    out.sort(key=lambda r: str(r.get("date") or ""), reverse=True)
    return out


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    shop = [r for r in rows if r.get("source") == "shop"]
    hosting = [r for r in rows if r.get("source") == "hosting"]
    by_payment_shop = dict(Counter(r.get("payment_method") or "—" for r in shop))
    by_payment_hosting = dict(Counter(r.get("payment_method") or "—" for r in hosting))
    by_payment_all = dict(Counter(r.get("payment_method") or "—" for r in rows))
    by_origin = dict(Counter(r.get("origin") or "unknown" for r in rows))
    return {
        "generated_at": _now_iso(),
        "totals": {
            "shop": len(shop),
            "hosting": len(hosting),
            "combined": len(rows),
        },
        "by_payment_method": {
            "shop": by_payment_shop,
            "hosting": by_payment_hosting,
            "combined": by_payment_all,
        },
        "by_origin": by_origin,
    }


def write_txt(path: Path, summary: Dict[str, Any], rows: List[Dict[str, Any]], notes: List[str]) -> None:
    lines = [
        "ALL FINISHED ORDERS — SHOP + MASTERNODE HOSTING",
        "=" * 72,
        f"Generated: {summary['generated_at']}",
        f"Shop orders:     {summary['totals']['shop']}",
        f"Hosting orders:  {summary['totals']['hosting']}",
        f"Combined total:  {summary['totals']['combined']}",
        "",
        "Payment breakdown (combined):",
    ]
    for method, count in sorted(summary["by_payment_method"]["combined"].items()):
        lines.append(f"  {method}: {count}")
    if notes:
        lines.extend(["", "Data coverage notes:"])
        lines.extend(f"  - {n}" for n in notes)
    lines.extend(["", "-" * 72, ""])
    header = f"{'Source':8} {'Order ID':22} {'User':14} {'Item/Slot':28} {'Qty':4} {'Amount':16} {'Payment':14} {'Status':10} {'Date':20}"
    lines.append(header)
    lines.append("-" * len(header))
    for row in rows:
        lines.append(
            f"{str(row.get('source',''))[:8]:8} "
            f"{str(row.get('order_id',''))[:22]:22} "
            f"{redact_user_id(row.get('user_id')):14} "
            f"{str(row.get('item',''))[:28]:28} "
            f"{str(row.get('qty','')):>4} "
            f"{str(row.get('amount',''))[:16]:16} "
            f"{str(row.get('payment_method',''))[:14]:14} "
            f"{str(row.get('status',''))[:10]:10} "
            f"{str(row.get('date',''))[:20]:20}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, summary: Dict[str, Any], rows: List[Dict[str, Any]], notes: List[str], prod: Dict[str, Any]) -> None:
    export_rows = []
    for row in rows:
        export_rows.append({**row, "user_id": redact_user_id(row.get("user_id"))})
    payload = {
        "summary": summary,
        "notes": notes,
        "vps_fetch": prod,
        "orders": export_rows,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_pdf(path: Path, summary: Dict[str, Any], rows: List[Dict[str, Any]], notes: List[str]) -> None:
    from backend.services.shop_order_pdf_service import build_orders_pdf

    pdf_rows: List[Dict[str, Any]] = []
    for row in rows:
        src = str(row.get("source") or "shop")
        item = str(row.get("item") or "")
        if src == "hosting":
            pdf_rows.append({
                "source": "masternode_hosting",
                "item_name": item,
                "quantity": row.get("qty") or 1,
                "payment_method": str(row.get("payment_method") or "").lower(),
                "payment_method_label": row.get("payment_method"),
                "purchase_status": row.get("status"),
                "status": row.get("status"),
                "created_at": row.get("date"),
                "paid_at": row.get("date"),
                "usd_total": _parse_usd(row.get("amount")),
                "mn2_total": _parse_mn2(row.get("amount")),
                "coins_total": _parse_coins(row.get("amount")),
            })
        else:
            pdf_rows.append({
                "source": "purchase",
                "item_name": f"{item} [{row.get('payment_method')}]",
                "quantity": row.get("qty") or 1,
                "payment_method": str(row.get("payment_method") or "").lower(),
                "payment_method_label": row.get("payment_method"),
                "purchase_status": row.get("status"),
                "status": row.get("status"),
                "created_at": row.get("date"),
                "price_paid_coins": _parse_coins(row.get("amount")),
                "price_paid_points": _points_from_amount(row.get("amount")),
                "price_type": _price_type_from_payment(row.get("payment_method")),
            })
    meta_user = f"site-wide ({summary['totals']['combined']} orders)"
    pdf_bytes = build_orders_pdf(user_id=meta_user, rows=pdf_rows, generated_at=summary["generated_at"])
    if notes:
        # Append a note page is non-trivial; summary is in txt/json.
        pass
    path.write_bytes(pdf_bytes)


def _parse_usd(amount: Any) -> Optional[float]:
    text = str(amount or "")
    if text.startswith("$"):
        try:
            return float(text.replace("$", "").strip())
        except ValueError:
            return None
    return None


def _parse_mn2(amount: Any) -> Optional[float]:
    text = str(amount or "")
    if "MN2" in text.upper():
        try:
            return float(text.upper().replace("MN2", "").replace("(ON-CHAIN)", "").strip())
        except ValueError:
            return None
    return None


def _parse_coins(amount: Any) -> int:
    text = str(amount or "")
    if "coin" in text.lower():
        try:
            return int(text.lower().split("coin")[0].strip())
        except ValueError:
            return 0
    return 0


def _points_from_amount(amount: Any) -> Dict[str, Any]:
    usd = _parse_usd(amount)
    mn2 = _parse_mn2(amount)
    if usd is not None:
        return {"usd": usd}
    if mn2 is not None:
        return {"mn2": mn2}
    return {}


def _price_type_from_payment(method: Any) -> str:
    m = str(method or "").lower()
    if "paypal" in m:
        return "paypal"
    if "on-chain" in m or "onchain" in m:
        return "mn2_onchain"
    if "mn2" in m:
        return "mn2"
    if "coin" in m:
        return "coins"
    if "point" in m:
        return "points"
    return m or "unknown"


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    prod = try_fetch_vps()
    notes: List[str] = []
    if not prod.get("ok"):
        notes.append(
            "Deploy VPS fetch failed or unavailable (SSH auth/timeout). "
            "Site-wide shop + hosting orders on the live server are NOT included unless cached locally."
        )
        notes.append(
            "Expected VPS paths: "
            + ", ".join(PROD_REMOTE_PATHS.values())
        )
    else:
        notes.append("Deploy VPS files fetched read-only into artifact cache (not committed to git).")

    local_db = ROOT / "instance" / "database.db"
    if local_db.is_file():
        try:
            conn = sqlite3.connect(str(local_db))
            total = conn.execute("SELECT COUNT(*) FROM shop_purchases").fetchone()[0]
            conn.close()
            if total == 0 and not prod.get("ok"):
                notes.append("Local shop_purchases table is empty (0 rows).")
        except sqlite3.Error:
            pass

    chunks = [
        collect_shop_sqlite(),
        collect_shop_file_mode(),
        collect_paypal_log(),
        collect_onchain_shop(),
        collect_exchange_shop(),
        collect_stall_sold(),
        collect_hosting(),
    ]
    rows = merge_rows(chunks)
    summary = summarize(rows)

    if summary["totals"]["combined"] == 0 and not prod.get("ok"):
        notes.append(
            "VPS-only gap: paid masternode hosting lives in /var/www/html/data/mn2_masternode_orders.json; "
            "catalog purchases in VPS instance/database.db and logs/purchase_notifications.log."
        )

    write_txt(ARTIFACT_DIR / "all_finished_orders.txt", summary, rows, notes)
    write_json(ARTIFACT_DIR / "all_finished_orders.json", summary, rows, notes, prod)
    write_pdf(ARTIFACT_DIR / "all_finished_orders.pdf", summary, rows, notes)

    print(json.dumps({"summary": summary, "notes": notes, "artifact_dir": str(ARTIFACT_DIR)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
