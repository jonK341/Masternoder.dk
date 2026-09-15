#!/usr/bin/env python3
"""Export site-wide finished or pending shop + hosting orders to /opt/cursor/artifacts/."""
from __future__ import annotations

import argparse
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
    "hosting_orders_audit": "/var/www/html/data/mn2_masternode_orders.jsonl",
    "onchain_orders": "/var/www/html/data/mn2_order_payments.json",
    "shop_db": "/var/www/html/instance/database.db",
    "paypal_log": "/var/www/html/logs/purchase_notifications.log",
    "auction_listings": "/var/www/html/logs/shop_marketplace/auction_listings.json",
    "exchange_purchases": "/var/www/html/data/crypto_exchange/exchange_shop_purchases.jsonl",
}

PROD_HTTP_PATHS = {
    "service": "/api/mn2/masternode/service",
    "hosting_ops": "/api/mn2/masternode/orders",
    "hosting_orders": "/api/shop/hosting-orders",
    "shop_purchases": "/api/shop/purchases",
    "users": "/api/user/db/all",
    "shop_analytics": "/api/shop/analytics?limit=50",
    "shop_paypal_panel": "/api/shop/paypal/control-panel",
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


def is_unfinished(status: Optional[str]) -> bool:
    raw = str(status or "completed").strip().lower()
    if raw in FINISHED_STATUSES:
        return False
    if raw in SKIP_STATUSES:
        return True
    if raw in ("completed", "captured", "fulfilled", "sold", "bought", "confirmed", "paid"):
        return False
    return bool(raw)


def include_for_export(status: Optional[str], pending: bool) -> bool:
    return is_unfinished(status) if pending else is_finished(status)


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


def _normalize_base_url() -> str:
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base and not base.startswith("http"):
        base = "https://" + base
    if not base.startswith("http"):
        try:
            from deploy_ssh_env import deploy_host

            host = deploy_host().strip()
            if host and not host.startswith("["):
                base = f"https://{host}"
        except Exception:
            pass
    return base


def _ops_secret() -> str:
    return (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 25) -> Tuple[Optional[int], Any]:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except Exception:
            return exc.code, {"error": str(exc)}
    except Exception as exc:
        return None, {"error": type(exc).__name__, "message": str(exc)}


def try_fetch_prod_http(pending: bool = False) -> Dict[str, Any]:
    """Best-effort read-only fetch from live site HTTP APIs. Never commits to git."""
    report: Dict[str, Any] = {"attempted": True, "ok": False, "endpoints": {}, "error": None}
    base = _normalize_base_url()
    if not base.startswith("http"):
        report["error"] = "BASE_URL unset or invalid"
        return report

    ops = _ops_secret()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    status, data = _http_get_json(base + PROD_HTTP_PATHS["service"])
    report["endpoints"]["service"] = {"status": status, "ok": status == 200}
    if status == 200 and isinstance(data, dict):
        report["hosting_stats"] = data.get("hosting_stats") or {}
        (CACHE_DIR / "prod_service.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        report["ok"] = True

    if ops:
        all_orders: List[Dict[str, Any]] = []
        offset = 0
        page_size = 500
        status_q = "" if pending else "paid"
        cache_name = "hosting_orders_api_pending.json" if pending else "hosting_orders_api.json"
        while offset < 5000:
            path = f"{PROD_HTTP_PATHS['hosting_ops']}?limit={page_size}&offset={offset}"
            if status_q:
                path += f"&status={status_q}"
            st, payload = _http_get_json(base + path, {"X-Ops-Token": ops})
            report["endpoints"].setdefault("hosting_ops", {"pages": []})
            report["endpoints"]["hosting_ops"]["pages"].append({"offset": offset, "status": st})
            if st != 200 or not isinstance(payload, dict):
                break
            batch = payload.get("orders") or []
            if not batch:
                break
            all_orders.extend(batch)
            total = int(payload.get("total") or len(all_orders))
            report["endpoints"]["hosting_ops"]["total"] = total
            report["endpoints"]["hosting_ops"]["by_status"] = payload.get("by_status")
            report["endpoints"]["hosting_ops"]["paid_by_payment_method"] = payload.get("paid_by_payment_method")
            if len(all_orders) >= total or len(batch) < page_size:
                break
            offset += page_size
        if all_orders:
            cache_path = CACHE_DIR / cache_name
            cache_path.write_text(json.dumps({"orders": all_orders, "total": len(all_orders)}, indent=2) + "\n", encoding="utf-8")
            report["hosting_orders_fetched"] = len(all_orders)
            report["ok"] = True

    for key, path in (("shop_analytics", PROD_HTTP_PATHS["shop_analytics"]), ("shop_paypal_panel", PROD_HTTP_PATHS["shop_paypal_panel"])):
        st, payload = _http_get_json(base + path)
        entry: Dict[str, Any] = {"status": st}
        if st == 200 and isinstance(payload, dict):
            if key == "shop_analytics":
                entry["popular_items"] = len(payload.get("popular_items") or [])
                entry["refund_stats"] = payload.get("refund_stats")
            if key == "shop_paypal_panel":
                entry["conversion"] = payload.get("conversion")
            report["ok"] = True
        report["endpoints"][key] = entry

    scan = fetch_orders_via_user_http_scan(base, pending=pending)
    report["user_scan"] = scan
    if scan.get("hosting_orders"):
        report["hosting_orders_fetched"] = len(scan["hosting_orders"])
        report["ok"] = True
    if scan.get("shop_orders"):
        report["shop_orders_fetched"] = len(scan["shop_orders"])
        report["ok"] = True

    if not report.get("ok") and not report.get("error"):
        report["error"] = "all_http_endpoints_failed"
    return report


def _fetch_all_prod_user_ids(base: str) -> List[str]:
    users: List[str] = []
    offset = 0
    page_size = 200
    while offset < 200000:
        path = f"{PROD_HTTP_PATHS['users']}?limit={page_size}&offset={offset}"
        status, data = _http_get_json(base + path, timeout=60)
        if status != 200 or not isinstance(data, dict):
            break
        batch = data.get("users") or []
        for row in batch:
            if isinstance(row, dict) and row.get("user_id"):
                users.append(str(row["user_id"]))
        total = int(data.get("total") or len(users))
        offset += page_size
        if offset >= total or not batch:
            break
    return users


def fetch_orders_via_user_http_scan(base: str, pending: bool = False) -> Dict[str, Any]:
    """Scan live site per-user hosting + shop APIs when ops/VPS are unavailable."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from urllib.parse import quote

    report: Dict[str, Any] = {
        "attempted": True,
        "ok": False,
        "users_total": 0,
        "users_scanned": 0,
        "hosting_orders": [],
        "shop_orders": [],
        "error": None,
    }
    cache_hosting = CACHE_DIR / "user_scan_hosting.json"
    cache_shop = CACHE_DIR / "user_scan_shop.json"
    if cache_hosting.is_file() and cache_shop.is_file() and not os.environ.get("FORCE_USER_SCAN"):
        hdata = _read_json(cache_hosting) or {}
        sdata = _read_json(cache_shop) or {}
        report["hosting_orders"] = list(hdata.get("orders") or [])
        report["shop_orders"] = list(sdata.get("orders") or [])
        report["users_scanned"] = int(hdata.get("users_scanned") or 0)
        report["users_total"] = int(hdata.get("users_total") or 0)
        if report["hosting_orders"] or report["shop_orders"]:
            report["ok"] = True
            report["from_cache"] = True
        return report

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    users = _fetch_all_prod_user_ids(base)
    report["users_total"] = len(users)
    if not users:
        report["error"] = "no_users"
        return report

    hosting_orders: List[Dict[str, Any]] = []
    shop_orders: List[Dict[str, Any]] = []
    workers = max(8, min(64, int(os.environ.get("USER_SCAN_WORKERS", "48"))))

    def _scan_user(uid: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        q = quote(uid, safe="")
        hrows: List[Dict[str, Any]] = []
        srows: List[Dict[str, Any]] = []
        st_h, payload_h = _http_get_json(
            f"{base}{PROD_HTTP_PATHS['hosting_orders']}?user_id={q}&limit=500",
            timeout=20,
        )
        if st_h == 200 and isinstance(payload_h, dict):
            for order in payload_h.get("hosting") or []:
                if not isinstance(order, dict):
                    continue
                order = dict(order)
                order.setdefault("user_id", uid)
                row = _hosting_row_from_order(order, origin="prod_http_user_scan", pending=pending)
                if row:
                    hrows.append(row)
        st_s, payload_s = _http_get_json(
            f"{base}{PROD_HTTP_PATHS['shop_purchases']}?user_id={q}&limit=500",
            timeout=20,
        )
        if st_s == 200 and isinstance(payload_s, dict):
            for rec in payload_s.get("purchases") or []:
                if not isinstance(rec, dict):
                    continue
                status = rec.get("purchase_status")
                status_s = str(status or "completed").strip().lower()
                if pending:
                    if status is None or status_s in FINISHED_STATUSES:
                        continue
                elif status is not None and not is_finished(status_s):
                    continue
                pts = rec.get("price_paid_points")
                if isinstance(pts, str) and pts.strip():
                    try:
                        pts = json.loads(pts)
                    except json.JSONDecodeError:
                        pts = {}
                srows.append({
                    "source": "shop",
                    "order_id": str(rec.get("id") or rec.get("order_id") or ""),
                    "user_id": str(rec.get("user_id") or uid),
                    "item": str(rec.get("item_name") or rec.get("item_id") or ""),
                    "qty": int(rec.get("quantity") or 1),
                    "amount": _amount_shop(rec.get("price_type"), rec.get("price_paid_coins"), pts),
                    "payment_method": _normalize_payment(rec.get("price_type")),
                    "status": status_s if status is not None else "completed",
                    "date": str(rec.get("created_at") or ""),
                    "origin": "prod_http_user_scan",
                })
        return hrows, srows

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_scan_user, uid): uid for uid in users}
        for fut in as_completed(futures):
            done += 1
            try:
                hpart, spart = fut.result()
                hosting_orders.extend(hpart)
                shop_orders.extend(spart)
            except Exception:
                pass
            if done % 1000 == 0:
                print(f"user_scan progress {done}/{len(users)} hosting={len(hosting_orders)} shop={len(shop_orders)}", flush=True)

    report["users_scanned"] = done
    report["hosting_orders"] = hosting_orders
    report["shop_orders"] = shop_orders
    report["ok"] = bool(hosting_orders or shop_orders)
    cache_hosting.write_text(
        json.dumps({"orders": hosting_orders, "users_total": len(users), "users_scanned": done}, indent=2) + "\n",
        encoding="utf-8",
    )
    cache_shop.write_text(
        json.dumps({"orders": shop_orders, "users_total": len(users), "users_scanned": done}, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def collect_hosting_from_user_scan(pending: bool = False) -> List[Dict[str, Any]]:
    data = _read_json(CACHE_DIR / "user_scan_hosting.json")
    rows: List[Dict[str, Any]] = []
    for order in (data or {}).get("orders") or []:
        if not isinstance(order, dict):
            continue
        if pending:
            if is_unfinished(order.get("status")):
                rows.append(order)
        elif str(order.get("status") or "").lower() == "paid":
            rows.append(order)
    return rows


def collect_shop_from_user_scan(pending: bool = False) -> List[Dict[str, Any]]:
    data = _read_json(CACHE_DIR / "user_scan_shop.json")
    rows: List[Dict[str, Any]] = []
    for row in (data or {}).get("orders") or []:
        if not isinstance(row, dict):
            continue
        if include_for_export(row.get("status"), pending):
            rows.append(row)
    return rows


def load_cached_snapshot() -> Dict[str, Any]:
    """Reuse earlier probe artifacts when live HTTP is down (counts only)."""
    out: Dict[str, Any] = {}
    sources: List[str] = []
    for name in ("_http_probe.json", "_http_probe2.json", "_prod_api_probe2.json", "mn2_live_service_summary.json"):
        path = ARTIFACT_DIR / name
        if not path.is_file():
            continue
        data = _read_json(path)
        if not isinstance(data, dict):
            continue
        stats = data.get("hosting_stats")
        if not stats and isinstance(data.get("endpoints"), dict):
            svc = data["endpoints"].get("/api/mn2/masternode/service") or data["endpoints"].get("service") or {}
            inner = svc.get("data") if isinstance(svc, dict) else {}
            stats = (inner or svc).get("hosting_stats") if isinstance(inner or svc, dict) else None
            if not stats and isinstance(svc, dict):
                stats = svc.get("hosting_stats")
        if stats and not out.get("hosting_stats"):
            out["hosting_stats"] = stats
            sources.append(name)
        if isinstance(data.get("endpoints"), dict):
            analytics = (
                data["endpoints"].get("/api/shop/analytics")
                or data["endpoints"].get("/api/shop/analytics?limit=50")
                or {}
            )
            body = analytics.get("body") if isinstance(analytics, dict) else {}
            if isinstance(body, dict) and body.get("refund_stats") and not out.get("shop_stats"):
                out["shop_stats"] = body["refund_stats"]
                if name not in sources:
                    sources.append(name)
    if sources:
        out["source_artifact"] = ",".join(sources)
    return out


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


_CACHE_ALIASES: Dict[str, List[str]] = {
    "mn2_masternode_orders.json": ["hosting_orders", "var_www_html_data_mn2_masternode_orders.json"],
    "mn2_order_payments.json": ["onchain_orders", "var_www_html_data_mn2_order_payments.json"],
    "mn2_onramp_orders.json": ["var_www_html_data_mn2_onramp_orders.json"],
}


def _data_path(name: str) -> Path:
    stem = name.replace("/", "_")
    candidates = [CACHE_DIR / stem]
    for alt in _CACHE_ALIASES.get(name, []):
        candidates.append(CACHE_DIR / alt)
    candidates.append(CACHE_DIR / f"var_www_html_data_{stem}")
    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            return path
    return ROOT / "data" / name


def _shop_dump_path() -> Optional[Path]:
    for name in ("shop_purchases_dump.json", "var_www_html_shop_purchases_dump.json"):
        path = CACHE_DIR / name
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


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


def _shop_row_from_record(
    rec: Dict[str, Any],
    origin: str,
    pending: bool,
) -> Optional[Dict[str, Any]]:
    status = str(rec.get("purchase_status") or rec.get("status") or "completed")
    if not include_for_export(status, pending):
        return None
    pts = rec.get("price_paid_points")
    if isinstance(pts, str) and pts.strip():
        try:
            pts = json.loads(pts)
        except json.JSONDecodeError:
            pts = {}
    return {
        "source": "shop",
        "order_id": str(rec.get("id") or rec.get("order_id") or ""),
        "user_id": str(rec.get("user_id") or ""),
        "item": str(rec.get("item_name") or rec.get("item_id") or ""),
        "qty": int(rec.get("quantity") or 1),
        "amount": _amount_shop(rec.get("price_type"), rec.get("price_paid_coins"), pts),
        "payment_method": _normalize_payment(rec.get("price_type") or rec.get("payment_method")),
        "status": status,
        "date": str(rec.get("created_at") or ""),
        "origin": origin,
    }


def collect_shop_sqlite(pending: bool = False) -> List[Dict[str, Any]]:
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
            row = _shop_row_from_record(dict(r), origin="shop_db", pending=pending)
            if row:
                rows.append(row)
        conn.close()
    except sqlite3.Error:
        pass
    return rows


def collect_shop_dump(pending: bool = False) -> List[Dict[str, Any]]:
    dump = _shop_dump_path()
    if not dump:
        return []
    data = _read_json(dump)
    if not isinstance(data, list):
        return []
    rows: List[Dict[str, Any]] = []
    for rec in data:
        if not isinstance(rec, dict):
            continue
        row = _shop_row_from_record(rec, origin="shop_dump", pending=pending)
        if row:
            rows.append(row)
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


def collect_shop_file_mode(pending: bool = False) -> List[Dict[str, Any]]:
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
            rec = dict(rec)
            rec.setdefault("user_id", user_id)
            row = _shop_row_from_record(rec, origin="shop_file_mode", pending=pending)
            if not row:
                continue
            if not row.get("order_id"):
                row["order_id"] = str(rec.get("purchase_id") or f"file:{path.name}:{rec.get('item_id')}")
            rows.append(row)
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


def collect_onchain_orders(pending: bool = False) -> List[Dict[str, Any]]:
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
        product = str(rec.get("product") or "shop")
        is_hosting = product == "mn2_masternode_hosting"
        if pending and is_hosting:
            source = "hosting"
        elif not pending and is_hosting:
            continue
        else:
            source = "shop"
        status = str(rec.get("status") or rec.get("purchase_status") or "pending").lower()
        if not include_for_export(status, pending):
            continue
        amt = rec.get("amount_mn2") or rec.get("amount_received")
        item = str(rec.get("item_name") or rec.get("item_id") or ("Masternode hosting" if is_hosting else "On-chain order"))
        rows.append({
            "source": source,
            "order_id": str(rec.get("payment_ref") or rec.get("id") or rec.get("item_id") or rec.get("order_id") or ""),
            "user_id": str(rec.get("user_id") or ""),
            "item": item,
            "qty": int(rec.get("quantity") or rec.get("slots") or 1),
            "amount": f"{float(amt or 0):.4f} MN2" if amt is not None else "MN2 on-chain",
            "payment_method": "MN2 on-chain",
            "status": status,
            "date": str(rec.get("fulfilled_at") or rec.get("created_at") or ""),
            "origin": "onchain_orders",
        })
    return rows


def collect_onchain_shop(pending: bool = False) -> List[Dict[str, Any]]:
    return [r for r in collect_onchain_orders(pending=pending) if r.get("source") == "shop"]


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


def collect_stall_listings(pending: bool = False) -> List[Dict[str, Any]]:
    data = _read_json(_auction_path())
    listings: List[Dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("listings"), list):
        listings = data["listings"]
    elif isinstance(data, list):
        listings = data
    rows: List[Dict[str, Any]] = []
    sold_statuses = frozenset({"sold", "bought", "completed"})
    for rec in listings:
        if not isinstance(rec, dict):
            continue
        status = str(rec.get("status") or "active").lower()
        if pending:
            if status in sold_statuses:
                continue
        elif status != "sold":
            continue
        rows.append({
            "source": "shop",
            "order_id": str(rec.get("listing_id") or rec.get("id") or ""),
            "user_id": str(rec.get("seller_id") or rec.get("buyer_id") or ""),
            "item": str(rec.get("item_name") or rec.get("item_id") or ""),
            "qty": int(rec.get("quantity") or 1),
            "amount": f"{int(rec.get('price_coins') or 0)} coins",
            "payment_method": "Coins",
            "status": status if pending else "sold",
            "date": str(rec.get("sold_at") or rec.get("cancelled_at") or rec.get("created_at") or ""),
            "origin": "stall",
        })
    return rows


def collect_stall_sold(pending: bool = False) -> List[Dict[str, Any]]:
    return collect_stall_listings(pending=False)


def collect_onramp_pending() -> List[Dict[str, Any]]:
    data = _read_json(_data_path("mn2_onramp_orders.json"))
    orders: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        raw = data.get("orders")
        if isinstance(raw, dict):
            orders = list(raw.values())
        elif isinstance(raw, list):
            orders = raw
        else:
            orders = [o for o in data.values() if isinstance(o, dict) and ("order_id" in o or "status" in o)]
    elif isinstance(data, list):
        orders = data
    rows: List[Dict[str, Any]] = []
    for rec in orders:
        if not isinstance(rec, dict):
            continue
        status = str(rec.get("status") or "pending_payment").lower()
        if not is_unfinished(status):
            continue
        usd = rec.get("usd_amount")
        mn2 = rec.get("mn2_amount")
        amount = "—"
        if usd is not None and mn2 is not None:
            amount = f"${float(usd):.2f} → {float(mn2):.4f} MN2"
        elif usd is not None:
            amount = f"${float(usd):.2f}"
        rows.append({
            "source": "shop",
            "order_id": str(rec.get("order_id") or rec.get("id") or ""),
            "user_id": str(rec.get("user_id") or ""),
            "item": "MN2 on-ramp",
            "qty": 1,
            "amount": amount,
            "payment_method": "PayPal",
            "status": status,
            "date": str(rec.get("created_at") or rec.get("quoted_at") or ""),
            "origin": "onramp",
        })
    return rows


def _hosting_row_from_order(order: Dict[str, Any], origin: str, pending: bool = False) -> Dict[str, Any]:
    status = str(order.get("status") or "").lower()
    if pending:
        if status == "paid":
            return {}
    elif status != "paid":
        return {}
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
    date = str(order.get("paid_at") or order.get("expires_at") or order.get("created_at") or "")
    return {
        "source": "hosting",
        "order_id": str(order.get("order_id") or order.get("id") or ""),
        "user_id": str(order.get("user_id") or ""),
        "item": f"Masternode hosting × {slots}",
        "qty": slots,
        "amount": amount,
        "payment_method": _normalize_payment(method),
        "status": status,
        "date": date,
        "origin": origin,
    }


def collect_hosting_from_cache(pending: bool = False) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    candidates = [
        CACHE_DIR / "hosting_orders",
        CACHE_DIR / "hosting_orders_api.json",
        CACHE_DIR / "hosting_orders_api_pending.json",
        CACHE_DIR / "var_www_html_data_mn2_masternode_orders.json",
    ]
    for path in candidates:
        if not path.is_file() or path.stat().st_size == 0:
            continue
        if path.suffix == ".json" and path.name not in ("hosting_orders",):
            data = _read_json(path)
            orders = data.get("orders") if isinstance(data, dict) else None
            if isinstance(orders, list):
                for order in orders:
                    if isinstance(order, dict):
                        row = _hosting_row_from_order(order, origin="prod_cache", pending=pending)
                        if row:
                            rows.append(row)
                continue
        data = _read_json(path)
        for order in _hosting_orders_from_blob(data):
            row = _hosting_row_from_order(order, origin="prod_cache", pending=pending)
            if row:
                rows.append(row)
    return rows


def collect_mn2_ledger_shop() -> List[Dict[str, Any]]:
    """MN2 ledger entries that represent completed shop/on-ramp purchases (local dev/test data)."""
    data = _read_json(ROOT / "data" / "mn2_ledger.json")
    entries = data.get("entries") if isinstance(data, dict) else []
    shop_types = {"paypal_mn2_pack", "exchange_paypal_mn2", "shop_purchase", "shop_paypal"}
    rows: List[Dict[str, Any]] = []
    for rec in entries or []:
        if not isinstance(rec, dict):
            continue
        typ = str(rec.get("type") or "")
        if typ not in shop_types:
            continue
        meta = rec.get("metadata") if isinstance(rec.get("metadata"), dict) else {}
        order_id = str(meta.get("order_id") or meta.get("reference") or rec.get("txid") or "")
        rows.append({
            "source": "shop",
            "order_id": order_id or f"ledger:{typ}:{rec.get('created_at')}",
            "user_id": str(rec.get("user_id") or ""),
            "item": str(meta.get("item_id") or meta.get("source") or typ),
            "qty": 1,
            "amount": f"{float(rec.get('amount') or 0):.4f} MN2",
            "payment_method": "PayPal" if "paypal" in typ else "MN2",
            "status": "completed",
            "date": str(rec.get("created_at") or ""),
            "origin": "mn2_ledger",
        })
    return rows


def collect_hosting(pending: bool = False) -> List[Dict[str, Any]]:
    data = _read_json(_data_path("mn2_masternode_orders.json"))
    orders = _hosting_orders_from_blob(data)
    rows: List[Dict[str, Any]] = []
    for order in orders:
        row = _hosting_row_from_order(order, origin="hosting_json", pending=pending)
        if row:
            rows.append(row)
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
    by_status_shop = dict(Counter(str(r.get("status") or "—") for r in shop))
    by_status_hosting = dict(Counter(str(r.get("status") or "—") for r in hosting))
    by_status_all = dict(Counter(str(r.get("status") or "—") for r in rows))
    by_origin = dict(Counter(r.get("origin") or "unknown" for r in rows))
    return {
        "generated_at": _now_iso(),
        "totals": {
            "shop": len(shop),
            "hosting": len(hosting),
            "combined": len(rows),
        },
        "by_status": {
            "shop": by_status_shop,
            "hosting": by_status_hosting,
            "combined": by_status_all,
        },
        "by_payment_method": {
            "shop": by_payment_shop,
            "hosting": by_payment_hosting,
            "combined": by_payment_all,
        },
        "by_origin": by_origin,
    }


def write_txt(
    path: Path,
    summary: Dict[str, Any],
    rows: List[Dict[str, Any]],
    notes: List[str],
    prod_snapshot: Optional[Dict[str, Any]] = None,
    *,
    shop_only: bool = False,
    pending: bool = False,
) -> None:
    if pending:
        title = "SHOP PENDING / UNFINISHED ORDERS" if shop_only else "ALL PENDING / UNFINISHED ORDERS — SHOP + MASTERNODE HOSTING"
    else:
        title = "SHOP FINISHED ORDERS" if shop_only else "ALL FINISHED ORDERS — SHOP + MASTERNODE HOSTING"
    lines = [
        title,
        "=" * 72,
        f"Generated: {summary['generated_at']}",
        f"Shop orders:     {summary['totals']['shop']}",
    ]
    if not shop_only:
        lines.extend([
            f"Hosting orders:  {summary['totals']['hosting']}",
            f"Combined total:  {summary['totals']['combined']}",
        ])
    status_key = "shop" if shop_only else "combined"
    lines.extend(["", "Status breakdown:"])
    for status, count in sorted(summary.get("by_status", {}).get(status_key, {}).items()):
        lines.append(f"  {status}: {count}")
    lines.extend(["", "Payment breakdown (shop):" if shop_only else "Payment breakdown (combined):"])
    payment_key = "shop" if shop_only else "combined"
    for method, count in sorted(summary["by_payment_method"][payment_key].items()):
        lines.append(f"  {method}: {count}")
    if prod_snapshot:
        hs = prod_snapshot.get("hosting_stats") or {}
        ss = prod_snapshot.get("shop_stats") or {}
        lines.extend([
            "",
            "Live-site snapshot (HTTP / cached probe — counts only when rows unavailable):",
            f"  Site paid hosting orders: {hs.get('paid_orders', '—')}",
            f"  Site pending hosting:     {hs.get('pending_orders', '—')}",
            f"  Site shop purchases (DB): {ss.get('total', '—')}",
            f"  Source:                   {prod_snapshot.get('source_artifact') or 'live HTTP'}",
        ])
        by_method = hs.get("by_payment_method")
        if isinstance(by_method, dict) and by_method:
            lines.append("  Hosting payment methods (site-wide):")
            for method, count in sorted(by_method.items()):
                lines.append(f"    {method}: {count}")
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


def write_json(path: Path, summary: Dict[str, Any], rows: List[Dict[str, Any]], notes: List[str], prod: Dict[str, Any], prod_http: Dict[str, Any], prod_snapshot: Dict[str, Any]) -> None:
    export_rows = []
    for row in rows:
        export_rows.append({**row, "user_id": redact_user_id(row.get("user_id"))})
    payload = {
        "summary": summary,
        "notes": notes,
        "vps_fetch": prod,
        "http_fetch": prod_http,
        "live_snapshot": prod_snapshot,
        "vps_order_files": PROD_REMOTE_PATHS,
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
    parser = argparse.ArgumentParser(description="Export finished or pending shop and/or hosting orders to artifacts.")
    parser.add_argument(
        "--shop-only",
        action="store_true",
        help="Export shop orders only (shop_finished_orders.* or shop_pending_orders.*)",
    )
    parser.add_argument(
        "--pending",
        "--unfinished",
        dest="pending",
        action="store_true",
        help="Export pending/unverified/unpaid orders instead of finished ones",
    )
    parser.add_argument(
        "--skip-vps-fetch",
        action="store_true",
        help="Use cached /opt/cursor/artifacts/_prod_cache/ only (no SSH fetch)",
    )
    args = parser.parse_args()
    shop_only = bool(args.shop_only)
    pending = bool(args.pending)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    prod = {"attempted": False, "ok": False, "skipped": True} if args.skip_vps_fetch else try_fetch_vps()
    prod_http = try_fetch_prod_http(pending=pending)
    prod_snapshot = load_cached_snapshot()
    if prod_http.get("hosting_stats") and not prod_snapshot.get("hosting_stats"):
        prod_snapshot = {"source_artifact": "live_http", "hosting_stats": prod_http["hosting_stats"]}
    notes: List[str] = []

    if prod.get("ok"):
        notes.append("Deploy VPS files fetched read-only into artifact cache (not committed to git).")
    else:
        notes.append(
            "Deploy VPS fetch failed (SSH auth rejected). Order rows on the live server are NOT in this export "
            "unless fetched via HTTP ops API or cached locally."
        )
        notes.append("VPS files containing orders: " + ", ".join(PROD_REMOTE_PATHS.values()))

    if prod_http.get("ok"):
        fetched = prod_http.get("hosting_orders_fetched")
        shop_fetched = prod_http.get("shop_orders_fetched")
        scan = prod_http.get("user_scan") or {}
        if scan.get("from_cache"):
            notes.append("Reused cached per-user HTTP scan (_prod_cache/user_scan_*.json).")
        elif scan.get("users_scanned"):
            notes.append(
                f"Per-user HTTP scan: {scan.get('users_scanned')} users, "
                f"{len(scan.get('hosting_orders') or [])} hosting + {len(scan.get('shop_orders') or [])} shop rows."
            )
        if fetched:
            notes.append(f"Live-site HTTP ops API returned {fetched} paid hosting order rows (cached).")
        if shop_fetched:
            notes.append(f"Live-site per-user shop API returned {shop_fetched} purchase rows (cached).")
        elif prod_http.get("hosting_stats"):
            notes.append(
                "Live-site HTTP /api/mn2/masternode/service reachable; "
                f"site paid_orders={prod_http['hosting_stats'].get('paid_orders', '?')}."
            )
    elif prod_snapshot.get("hosting_stats"):
        notes.append(
            "Live HTTP unreachable; using cached live-site probe for site-wide hosting counts "
            f"(paid_orders={prod_snapshot['hosting_stats'].get('paid_orders', '?')})."
        )
    else:
        notes.append("Live-site HTTP fetch failed (timeout/unreachable).")

    local_db = ROOT / "instance" / "database.db"
    if local_db.is_file():
        try:
            conn = sqlite3.connect(str(local_db))
            total = conn.execute("SELECT COUNT(*) FROM shop_purchases").fetchone()[0]
            conn.close()
            if total == 0:
                notes.append("Local shop_purchases table is empty (0 rows). Live-site shop rows are in VPS instance/database.db.")
        except sqlite3.Error:
            pass

    if pending:
        chunks = [
            collect_shop_sqlite(pending=True),
            collect_shop_dump(pending=True),
            collect_shop_file_mode(pending=True),
            collect_onchain_orders(pending=True),
            collect_stall_listings(pending=True),
            collect_onramp_pending(),
            collect_hosting(pending=True),
            collect_hosting_from_cache(pending=True),
        ]
    else:
        chunks = [
            collect_shop_sqlite(pending=False),
            collect_shop_dump(pending=False),
            collect_shop_file_mode(pending=False),
            collect_shop_from_user_scan(pending=False),
            collect_paypal_log(),
            collect_onchain_shop(pending=False),
            collect_exchange_shop(),
            collect_stall_sold(pending=False),
            collect_hosting(pending=False),
            collect_hosting_from_cache(pending=False),
            collect_hosting_from_user_scan(pending=False),
        ]
    rows = merge_rows(chunks)
    if shop_only:
        rows = [r for r in rows if r.get("source") == "shop"]
    summary = summarize(rows)

    if pending:
        notes.append(
            "Pending export includes shop DB rows with explicit non-completed status, "
            "on-chain awaiting confirmation, PayPal on-ramp quotes, stall listings not sold, "
            "and hosting orders not status paid."
        )
    else:
        site_paid = (prod_snapshot.get("hosting_stats") or prod_http.get("hosting_stats") or {}).get("paid_orders")
        if not shop_only and site_paid and summary["totals"]["hosting"] < int(site_paid):
            notes.append(
                f"Gap: live site reports {site_paid} paid hosting orders but only "
                f"{summary['totals']['hosting']} hosting rows exported. "
                "Full list requires VPS /var/www/html/data/mn2_masternode_orders.json "
                "or deployed GET /api/mn2/masternode/orders (ops token)."
            )
        if summary["totals"]["shop"] and summary["by_origin"].get("mn2_ledger"):
            notes.append(
                "Shop rows from data/mn2_ledger.json are local dev/test ledger credits — "
                "NOT live-site catalog purchases (those live in VPS shop_purchases + purchase_notifications.log)."
            )

    if pending:
        prefix = "shop_pending_orders" if shop_only else "all_pending_orders"
    else:
        prefix = "shop_finished_orders" if shop_only else "all_finished_orders"
    write_txt(
        ARTIFACT_DIR / f"{prefix}.txt",
        summary,
        rows,
        notes,
        prod_snapshot,
        shop_only=shop_only,
        pending=pending,
    )
    write_json(ARTIFACT_DIR / f"{prefix}.json", summary, rows, notes, prod, prod_http, prod_snapshot)
    write_pdf(ARTIFACT_DIR / f"{prefix}.pdf", summary, rows, notes)

    print(json.dumps({
        "pending": pending,
        "shop_only": shop_only,
        "summary": summary,
        "notes": notes,
        "live_snapshot": prod_snapshot,
        "artifact_dir": str(ARTIFACT_DIR),
        "artifacts": {
            "txt": str(ARTIFACT_DIR / f"{prefix}.txt"),
            "json": str(ARTIFACT_DIR / f"{prefix}.json"),
            "pdf": str(ARTIFACT_DIR / f"{prefix}.pdf"),
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
