"""Fiat payment system of record (PayPal now, any provider later).

WHY THIS EXISTS
  shop_purchases already had price_paid_usd / payment_method / payment_ref /
  purchase_status columns, but nothing ever wrote them: the INSERT in
  shop_db_service.record_purchase() omits them and the PayPal capture handler
  never passed them. Result: 0 of 4444 purchases had a fiat trail, coin-pack
  and MN2-pack PayPal payments wrote no shop_purchases row at all, and a
  replayed capture could grant twice.

  This module is the single place that records real money:
    * fiat_payments  -- authoritative record, UNIQUE on capture_id (idempotency)
    * shop_purchases -- fiat columns populated, or a row created when the
                        fulfillment path does not make one (coin/MN2 packs)

  Every function is non-fatal by design: a DB problem must never turn an
  already-captured payment into a 500 that loses the record.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _log(msg: str) -> None:
    try:
        from backend.utils.logger import get_logger
        get_logger(__name__).warning(msg)
    except Exception:
        import sys
        print(f"[fiat_payment_service] {msg}", file=sys.stderr)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _db_path() -> Optional[str]:
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or ""
    if not url.startswith("sqlite"):
        env = os.path.join(REPO, ".env")
        try:
            with open(env, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    m = re.match(r'\s*DATABASE_URL\s*=\s*["\']?(.+?)["\']?\s*$', line)
                    if m:
                        url = m.group(1)
                        break
        except Exception:
            url = ""
    if url.startswith("sqlite"):
        p = re.sub(r"^sqlite:///?", "", url).split("?", 1)[0]
        if not p.startswith("/"):
            p = os.path.join(REPO, p.replace("/", os.sep))
        return os.path.abspath(p)
    fallback = os.path.join(REPO, "instance", "database.db")
    return fallback if os.path.exists(fallback) else None


def _connect() -> Optional[sqlite3.Connection]:
    path = _db_path()
    if not path or not os.path.exists(path):
        _log(f"database not found ({path}); fiat payment not recorded")
        return None
    try:
        c = sqlite3.connect(path, timeout=30)
        c.row_factory = sqlite3.Row
        return c
    except Exception as e:
        _log(f"connect failed: {e}")
        return None


def _has_table(c: sqlite3.Connection, t: str) -> bool:
    try:
        return c.execute(
            "select 1 from sqlite_master where type='table' and name=?", (t,)
        ).fetchone() is not None
    except Exception:
        return False


def _has_column(c: sqlite3.Connection, t: str, col: str) -> bool:
    try:
        return col in {r[1] for r in c.execute(f"PRAGMA table_info({t})")}
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# idempotency
# --------------------------------------------------------------------------- #
def already_fulfilled(capture_id: Optional[str]) -> bool:
    """True only if this capture was already PAID OUT, not merely recorded.

    Deliberately narrower than "have we seen this id": the fiat row is written
    with status='captured' before granting, so blocking on mere presence would
    deny delivery if a grant crashed half-way. Blocking on completion still
    stops the real double-grant (client retry + webhook both firing).
    """
    if not capture_id:
        return False
    c = _connect()
    if not c:
        return False
    try:
        if _has_table(c, "fiat_payments"):
            row = c.execute(
                "select status from fiat_payments where capture_id=?", (capture_id,)
            ).fetchone()
            if row and (row[0] or "") in ("completed", "refunded"):
                return True
        if _has_table(c, "shop_purchases") and _has_column(c, "shop_purchases", "payment_ref"):
            # a purchase row carrying this ref means the grant path already ran
            row = c.execute(
                "select 1 from shop_purchases where payment_ref=? limit 1", (capture_id,)
            ).fetchone()
            return bool(row)
    except Exception as e:
        _log(f"already_fulfilled failed: {e}")
    finally:
        c.close()
    return False


# --------------------------------------------------------------------------- #
# fiat_payments
# --------------------------------------------------------------------------- #
def record_fiat_payment(
    *,
    capture_id: str,
    order_id: Optional[str] = None,
    provider: str = "paypal",
    user_id: Optional[str] = None,
    item_id: Optional[str] = None,
    item_name: Optional[str] = None,
    quantity: int = 1,
    amount: float = 0.0,
    currency: str = "USD",
    status: str = "captured",
    price_expected: Optional[float] = None,
    granted_kind: Optional[str] = None,
    granted_amount: Optional[float] = None,
    purchase_id: Optional[int] = None,
    webhook_verified: int = 0,
    raw: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """Insert (or update) the authoritative fiat record. Returns its id.

    Idempotent on capture_id: a replay updates rather than duplicates, so the
    UNIQUE(capture_id) constraint can never raise on a legitimate retry.
    """
    if not capture_id:
        return None
    price_match = None
    if price_expected is not None:
        try:
            price_match = 1 if abs(float(amount) - float(price_expected)) < 0.005 else 0
        except (TypeError, ValueError):
            price_match = None

    c = _connect()
    if not c:
        return None
    try:
        if not _has_table(c, "fiat_payments"):
            _log("fiat_payments table missing -- run scripts/mn2_settle_schema.py apply --yes")
            return None
        raw_json = json.dumps(raw, default=str) if raw is not None else None
        c.execute(
            """INSERT INTO fiat_payments
                 (provider, order_id, capture_id, user_id, item_id, item_name, quantity,
                  amount, currency, status, price_expected, price_match,
                  granted_kind, granted_amount, purchase_id, webhook_verified,
                  raw_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(capture_id) DO UPDATE SET
                 status=excluded.status,
                 amount=excluded.amount,
                 currency=excluded.currency,
                 price_expected=COALESCE(excluded.price_expected, fiat_payments.price_expected),
                 price_match=COALESCE(excluded.price_match, fiat_payments.price_match),
                 granted_kind=COALESCE(excluded.granted_kind, fiat_payments.granted_kind),
                 granted_amount=COALESCE(excluded.granted_amount, fiat_payments.granted_amount),
                 purchase_id=COALESCE(excluded.purchase_id, fiat_payments.purchase_id),
                 webhook_verified=MAX(excluded.webhook_verified, fiat_payments.webhook_verified),
                 updated_at=excluded.updated_at""",
            (provider, order_id, capture_id, user_id, item_id, item_name, int(quantity or 1),
             float(amount or 0), currency or "USD", status, price_expected, price_match,
             granted_kind, granted_amount, purchase_id, int(webhook_verified or 0),
             raw_json, _now(), _now()),
        )
        c.commit()
        row = c.execute(
            "select id from fiat_payments where capture_id=?", (capture_id,)
        ).fetchone()
        return row[0] if row else None
    except Exception as e:
        try:
            c.rollback()
        except Exception:
            pass
        _log(f"record_fiat_payment failed: {e}")
        return None
    finally:
        c.close()


def update_fiat_grant(
    capture_id: str,
    granted_kind: Optional[str],
    granted_amount: Optional[float],
    purchase_id: Optional[int] = None,
    status: str = "completed",
) -> bool:
    if not capture_id:
        return False
    c = _connect()
    if not c:
        return False
    try:
        if not _has_table(c, "fiat_payments"):
            return False
        c.execute(
            """UPDATE fiat_payments SET granted_kind=?, granted_amount=?,
                 purchase_id=COALESCE(?, purchase_id), status=?, updated_at=?
               WHERE capture_id=?""",
            (granted_kind, granted_amount, purchase_id, status, _now(), capture_id),
        )
        c.commit()
        return True
    except Exception as e:
        _log(f"update_fiat_grant failed: {e}")
        return False
    finally:
        c.close()


def mark_webhook_verified(capture_id: str, status: Optional[str] = None) -> bool:
    if not capture_id:
        return False
    c = _connect()
    if not c:
        return False
    try:
        if not _has_table(c, "fiat_payments"):
            return False
        if status:
            c.execute(
                "UPDATE fiat_payments SET webhook_verified=1, status=?, updated_at=? WHERE capture_id=?",
                (status, _now(), capture_id),
            )
        else:
            c.execute(
                "UPDATE fiat_payments SET webhook_verified=1, updated_at=? WHERE capture_id=?",
                (_now(), capture_id),
            )
        c.commit()
        return True
    except Exception as e:
        _log(f"mark_webhook_verified failed: {e}")
        return False
    finally:
        c.close()


# --------------------------------------------------------------------------- #
# shop_purchases
# --------------------------------------------------------------------------- #
def attach_fiat_to_purchase(
    purchase_id: Optional[int],
    *,
    amount_usd: float,
    capture_id: str,
    order_id: Optional[str] = None,
    provider: str = "paypal",
    status: str = "paid",
) -> bool:
    """Write the fiat columns onto an existing shop_purchases row.

    This is the fix for the original gap: the row was created by
    fulfill_shop_purchase() with price_paid_usd / payment_method / payment_ref /
    purchase_status all NULL.
    """
    if not purchase_id:
        return False
    c = _connect()
    if not c:
        return False
    try:
        if not _has_table(c, "shop_purchases"):
            return False
        sets, params = [], []
        for col, val in (("price_paid_usd", float(amount_usd or 0)),
                         ("payment_method", provider),
                         ("payment_ref", capture_id),
                         ("purchase_status", status)):
            if _has_column(c, "shop_purchases", col):
                sets.append(f"{col}=?")
                params.append(val)
        if not sets:
            return False
        params.append(int(purchase_id))
        c.execute(
            f"UPDATE shop_purchases SET {', '.join(sets)} WHERE id=?", tuple(params)
        )
        c.commit()
        return True
    except Exception as e:
        try:
            c.rollback()
        except Exception:
            pass
        _log(f"attach_fiat_to_purchase failed: {e}")
        return False
    finally:
        c.close()


def record_fiat_purchase_row(
    *,
    user_id: str,
    item_id: str,
    item_name: str,
    amount_usd: float,
    capture_id: str,
    quantity: int = 1,
    currency: str = "USD",
    provider: str = "paypal",
    status: str = "paid",
) -> Optional[int]:
    """Create a shop_purchases row for a fiat payment that made none.

    Coin packs and MN2 packs are granted through unified_points / the MN2
    ledger, so before this they left no row in shop_purchases at all.
    Idempotent: an existing payment_ref wins instead of raising on the UNIQUE
    partial index.
    """
    if not capture_id:
        return None
    c = _connect()
    if not c:
        return None
    try:
        if not _has_table(c, "shop_purchases"):
            return None
        existing = None
        if _has_column(c, "shop_purchases", "payment_ref"):
            row = c.execute(
                "select id from shop_purchases where payment_ref=? limit 1", (capture_id,)
            ).fetchone()
            existing = row[0] if row else None
        if existing:
            return existing

        cols = ["user_id", "item_id", "item_name", "quantity", "price_type", "created_at"]
        vals: list = [user_id, item_id, item_name, int(quantity or 1), provider, _now()]
        optional = {
            "price_paid_usd": float(amount_usd or 0),
            "price_paid_coins": 0,
            "payment_method": provider,
            "payment_ref": capture_id,
            "purchase_status": status,
        }
        for col, val in optional.items():
            if _has_column(c, "shop_purchases", col):
                cols.append(col)
                vals.append(val)
        placeholders = ",".join("?" * len(cols))
        cur = c.execute(
            f"INSERT INTO shop_purchases ({','.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )
        c.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        # lost a race with a concurrent duplicate capture -- return the winner
        try:
            c.rollback()
            row = c.execute(
                "select id from shop_purchases where payment_ref=? limit 1", (capture_id,)
            ).fetchone()
            return row[0] if row else None
        except Exception:
            return None
    except Exception as e:
        try:
            c.rollback()
        except Exception:
            pass
        _log(f"record_fiat_purchase_row failed: {e}")
        return None
    finally:
        c.close()
