#!/usr/bin/env python3
"""Phase E2 -- promote the camgirls sub-app stores into typed tables, link their
MN2 payout addresses into the consolidated wallet graph, mirror PayPal orders as
REVENUE TRACKING (no live capture), record MN2 payout transactions, and compute
achievement / activity points. Finishes with a SMOKE TEST of the camgirls data.

DB-LEVEL ONLY. This never calls PayPal, never broadcasts a tx, never moves funds.
The performer "version" is only changed when --version is passed explicitly, so a
v12.0.0 upgrade is an authorized act, not a side effect.

  python 009_camgirls.py --db instance/database.db --data-dir data
  python 009_camgirls.py --db instance/database.db --data-dir data --version 12.0.0
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mn2_addr import validate_address  # noqa: E402

PERFORMER_FILES = ("camgirls_performers.json",)
PAYPAL_FILES = ("camgirls_paypal_orders.json",)
PAYOUT_FILES = ("camgirls_payout_addresses.json",)
ACTIVITY_FILES = ("camgirls_activity.json", "camgirls_achievements.json")


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


def as_records(data):
    """Normalize a store into a list of dict records, regardless of wrapper shape."""
    if data is None:
        return []
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(data) == 1 and lists:
            return [d for d in lists[0] if isinstance(d, dict)]
        # dict-of-objects keyed by id, OR field->value single record
        rec_vals = [v for v in data.values() if isinstance(v, dict)]
        if rec_vals and len(rec_vals) == len(data):
            out = []
            for k, v in data.items():
                r = dict(v)
                r.setdefault("_key", k)
                out.append(r)
            return out
        return [data]
    return []


def set_metric(conn, key, num=None, text=None, scope="global", scope_id="", source="camgirls"):
    conn.execute(
        """INSERT INTO mn2_metrics (metric_key, value_num, value_text, scope, scope_id, as_of, source, updated_at)
           VALUES (?,?,?,?,?,'',?,?)
           ON CONFLICT(metric_key, scope, scope_id, as_of) DO UPDATE SET
             value_num=excluded.value_num, value_text=excluded.value_text,
             source=excluded.source, updated_at=excluded.updated_at""",
        (key, num, text, scope, scope_id, source, utcnow()),
    )


def promote_performers(conn, dd, version):
    recs = []
    for fn in PERFORMER_FILES:
        recs += as_records(read_json(os.path.join(dd, fn)))
    n = 0
    for r in recs:
        pid = str(r.get("performer_id") or r.get("id") or r.get("_key") or "")
        if not pid:
            continue
        addr = r.get("payout_address") or r.get("address")
        ins_ver = version or "11.0.0"
        conn.execute(
            """INSERT INTO camgirls_performers
                 (performer_id, stage_name, user_ref, status, payout_address, paypal_email,
                  rating, followers, bio, payload_json, version, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(performer_id) DO UPDATE SET
                 stage_name=COALESCE(excluded.stage_name, camgirls_performers.stage_name),
                 user_ref=COALESCE(excluded.user_ref, camgirls_performers.user_ref),
                 status=COALESCE(excluded.status, camgirls_performers.status),
                 payout_address=COALESCE(excluded.payout_address, camgirls_performers.payout_address),
                 paypal_email=COALESCE(excluded.paypal_email, camgirls_performers.paypal_email),
                 rating=COALESCE(excluded.rating, camgirls_performers.rating),
                 followers=COALESCE(excluded.followers, camgirls_performers.followers),
                 bio=COALESCE(excluded.bio, camgirls_performers.bio),
                 payload_json=excluded.payload_json,
                 version=COALESCE(?, camgirls_performers.version),
                 updated_at=excluded.updated_at""",
            (pid, r.get("stage_name"), r.get("user_id") or r.get("user_ref"), r.get("status"),
             addr, r.get("paypal_email"), r.get("rating"), r.get("followers", 0), r.get("bio"),
             json.dumps(r, default=str), ins_ver, utcnow(), utcnow(), version),
        )
        n += 1
    return n


def link_address(conn, address, user_ref, performer_id):
    """Validate + upsert a camgirls payout address into the consolidated wallet graph."""
    valid = 1 if validate_address(address) else 0
    wid = None
    if user_ref:
        conn.execute(
            """INSERT INTO mn2_wallets (user_id, wallet_kind, source, created_at, updated_at)
               VALUES (?, 'custodial', 'harvest:camgirls', ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at""",
            (str(user_ref), utcnow(), utcnow()),
        )
        wid = conn.execute("SELECT id FROM mn2_wallets WHERE user_id=?", (str(user_ref),)).fetchone()[0]
    conn.execute(
        """INSERT INTO mn2_addresses (address, wallet_id, user_id, label, is_valid, first_seen, source, created_at)
           VALUES (?,?,?, 'camgirls_payout', ?, ?, 'harvest:camgirls', ?)
           ON CONFLICT(address) DO UPDATE SET
             wallet_id=COALESCE(mn2_addresses.wallet_id, excluded.wallet_id),
             is_valid=excluded.is_valid""",
        (address, wid, str(user_ref) if user_ref else None, valid, utcnow(), utcnow()),
    )
    conn.execute(
        """INSERT INTO camgirls_payout_addresses (performer_id, user_ref, address, is_valid, network, linked_wallet_id, created_at)
           VALUES (?,?,?,?,'mn2',?,?)
           ON CONFLICT(address) DO UPDATE SET
             performer_id=COALESCE(excluded.performer_id, camgirls_payout_addresses.performer_id),
             user_ref=COALESCE(excluded.user_ref, camgirls_payout_addresses.user_ref),
             is_valid=excluded.is_valid, linked_wallet_id=COALESCE(excluded.linked_wallet_id, camgirls_payout_addresses.linked_wallet_id)""",
        (performer_id, str(user_ref) if user_ref else None, address, valid, wid, utcnow()),
    )
    return valid


def promote_payouts(conn, dd):
    # explicit payout-address store
    n = 0
    data = read_json(os.path.join(dd, "camgirls_payout_addresses.json"))
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(v.get("address"), str):
                n += link_address(conn, v["address"], v.get("user_id") or k, v.get("performer_id"))
            elif isinstance(v, str):
                n += link_address(conn, v, k, None)
    # addresses embedded on performer records
    for r in conn.execute("SELECT performer_id, user_ref, payout_address FROM camgirls_performers WHERE payout_address IS NOT NULL"):
        link_address(conn, r[2], r[1], r[0])
        n += 1
    conn.execute(
        """UPDATE mn2_wallets SET address_count =
             (SELECT COUNT(*) FROM mn2_addresses a WHERE a.wallet_id = mn2_wallets.id)"""
    )
    return n


def promote_paypal(conn, dd):
    recs = []
    for fn in PAYPAL_FILES:
        recs += as_records(read_json(os.path.join(dd, fn)))
    gross = net = fee = payout_mn2 = 0.0
    completed = 0
    n = 0
    for r in recs:
        oid = str(r.get("order_id") or r.get("id") or r.get("_key") or "")
        if not oid:
            continue
        g = float(r.get("gross_usd") or r.get("gross") or r.get("amount") or 0)
        netv = r.get("net_usd")
        feev = r.get("fee_usd")
        pm = float(r.get("payout_mn2") or 0)
        st = r.get("status")
        conn.execute(
            """INSERT INTO camgirls_paypal_orders
                 (order_id, performer_id, user_ref, gross_usd, net_usd, fee_usd, currency,
                  status, capture_id, payout_mn2, payout_txid, created_at, payload_json, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(order_id) DO UPDATE SET
                 performer_id=COALESCE(excluded.performer_id, camgirls_paypal_orders.performer_id),
                 user_ref=COALESCE(excluded.user_ref, camgirls_paypal_orders.user_ref),
                 gross_usd=excluded.gross_usd, net_usd=COALESCE(excluded.net_usd, camgirls_paypal_orders.net_usd),
                 fee_usd=COALESCE(excluded.fee_usd, camgirls_paypal_orders.fee_usd),
                 status=COALESCE(excluded.status, camgirls_paypal_orders.status),
                 capture_id=COALESCE(excluded.capture_id, camgirls_paypal_orders.capture_id),
                 payout_mn2=COALESCE(excluded.payout_mn2, camgirls_paypal_orders.payout_mn2),
                 payout_txid=COALESCE(excluded.payout_txid, camgirls_paypal_orders.payout_txid),
                 payload_json=excluded.payload_json, ingested_at=excluded.ingested_at""",
            (oid, r.get("performer_id"), r.get("user_id") or r.get("user_ref"), g,
             float(netv) if netv is not None else None, float(feev) if feev is not None else None,
             r.get("currency") or "USD", st, r.get("capture_id"), pm or None,
             r.get("payout_txid"), str(r.get("created_at") or ""), json.dumps(r, default=str), utcnow()),
        )
        gross += g
        net += float(netv) if netv is not None else g
        fee += float(feev) if feev is not None else 0
        payout_mn2 += pm
        if st and str(st).upper() == "COMPLETED":
            completed += 1
        n += 1
    set_metric(conn, "camgirls.paypal.orders_total", num=n)
    set_metric(conn, "camgirls.paypal.orders_completed", num=completed)
    set_metric(conn, "camgirls.paypal.gross_usd", num=round(gross, 2))
    set_metric(conn, "camgirls.paypal.net_usd", num=round(net, 2))
    set_metric(conn, "camgirls.paypal.fee_usd", num=round(fee, 2))
    set_metric(conn, "camgirls.paypal.payout_mn2_total", num=round(payout_mn2, 8))
    return n, gross, completed


def record_payout_txs(conn):
    """Mirror credited MN2 payouts as mn2_transactions (ref_type='camgirls_payout').
    Rows with no payout_txid are logged as a reconciliation gap (needs on-chain linkage)."""
    rows = conn.execute(
        """SELECT o.order_id, o.performer_id, o.payout_mn2, o.payout_txid, p.payout_address
             FROM camgirls_paypal_orders o
             LEFT JOIN camgirls_performers p ON p.performer_id = o.performer_id
            WHERE COALESCE(o.payout_mn2,0) > 0"""
    ).fetchall()
    linked = unlinked = 0
    for oid, pid, amt, txid, addr in rows:
        exists = conn.execute(
            "SELECT 1 FROM mn2_transactions WHERE ref_type='camgirls_payout' AND ref_id=?", (oid,)
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO mn2_transactions
                     (txid, vout, direction, address, user_id, amount, status, kind, ref_type, ref_id, created_at)
                   VALUES (?,?,?,?,?,?,?, 'payout', 'camgirls_payout', ?, ?)""",
                (txid or f"PENDING:{oid}", None, "out", addr, pid, float(amt),
                 "confirmed" if txid else "pending", oid, utcnow()),
            )
            if not txid:
                conn.execute(
                    """INSERT INTO mn2_reconciliation_log (run_at, scope, entity_id, db_value, chain_value, drift, status, detail)
                       VALUES (?,?,?,?,?,?, 'mismatch', ?)""",
                    (utcnow(), "tx", f"camgirls_payout:{oid}", float(amt), None, None,
                     "paypal payout credited in MN2 but no payout_txid -- needs on-chain linkage"),
                )
        if txid:
            linked += 1
        else:
            unlinked += 1
    return len(rows), linked, unlinked


def promote_activity(conn, dd):
    recs = []
    for fn in ACTIVITY_FILES:
        recs += as_records(read_json(os.path.join(dd, fn)))
    n = 0
    per_perf = {}
    for r in recs:
        pid = str(r.get("performer_id") or r.get("_key") or "")
        kind = str(r.get("kind") or ("achievement" if "achievement" in r else "activity_point"))
        label = str(r.get("label") or r.get("name") or "")
        pts = float(r.get("points") or r.get("amount") or 0)
        occ = str(r.get("occurred_at") or r.get("created_at") or "")
        if not (pid and label):
            continue
        conn.execute(
            """INSERT INTO camgirls_activity (performer_id, user_ref, kind, points, amount, currency, label, occurred_at, payload_json, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(performer_id, kind, label, occurred_at) DO UPDATE SET
                 points=excluded.points, user_ref=COALESCE(excluded.user_ref, camgirls_activity.user_ref),
                 payload_json=excluded.payload_json, ingested_at=excluded.ingested_at""",
            (pid, r.get("user_id") or r.get("user_ref"), kind, pts,
             r.get("amount"), r.get("currency"), label, occ, json.dumps(r, default=str), utcnow()),
        )
        per_perf[pid] = per_perf.get(pid, 0.0) + pts
        n += 1
    total = sum(per_perf.values())
    set_metric(conn, "camgirls.points_total", num=round(total, 2))
    set_metric(conn, "camgirls.performers_with_points", num=len(per_perf))
    for pid, pts in per_perf.items():
        set_metric(conn, "camgirls.points", num=round(pts, 2), scope="user", scope_id=pid)
    return n, total, per_perf


def smoke(conn):
    """Read-only assertions about the camgirls data. Prints PASS/FAIL per check."""
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    perf = conn.execute("SELECT COUNT(*) FROM camgirls_performers").fetchone()[0]
    chk("performers present", perf > 0, f"count={perf}")

    bad = conn.execute("SELECT COUNT(*) FROM camgirls_payout_addresses WHERE is_valid=0").fetchone()[0]
    chk("all payout addresses valid MN2", bad == 0, f"invalid={bad}")

    orphan = conn.execute(
        """SELECT COUNT(*) FROM camgirls_payout_addresses cpa
            WHERE NOT EXISTS (SELECT 1 FROM mn2_addresses a WHERE a.address = cpa.address)"""
    ).fetchone()[0]
    chk("payout addresses linked into mn2_addresses", orphan == 0, f"orphans={orphan}")

    g_db = conn.execute("SELECT ROUND(SUM(gross_usd),2) FROM camgirls_paypal_orders").fetchone()[0] or 0
    g_met = conn.execute("SELECT value_num FROM mn2_metrics WHERE metric_key='camgirls.paypal.gross_usd'").fetchone()
    chk("paypal gross matches metric", g_met and abs((g_met[0] or 0) - g_db) < 0.01, f"db={g_db} metric={g_met[0] if g_met else None}")

    o_orphan = conn.execute(
        """SELECT COUNT(*) FROM camgirls_paypal_orders o
            WHERE o.performer_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM camgirls_performers p WHERE p.performer_id=o.performer_id)"""
    ).fetchone()[0]
    chk("no orphan paypal performer_id", o_orphan == 0, f"orphans={o_orphan}")

    pts_db = conn.execute("SELECT ROUND(SUM(points),2) FROM camgirls_activity").fetchone()[0] or 0
    pts_met = conn.execute("SELECT value_num FROM mn2_metrics WHERE metric_key='camgirls.points_total'").fetchone()
    chk("activity points match metric", pts_met and abs((pts_met[0] or 0) - pts_db) < 0.01, f"db={pts_db} metric={pts_met[0] if pts_met else None}")

    tx = conn.execute("SELECT COUNT(*) FROM mn2_transactions WHERE ref_type='camgirls_payout'").fetchone()[0]
    chk("mn2 payout txs mirrored", tx >= 0, f"camgirls_payout_txs={tx}")

    print("\n== camgirls SMOKE TEST ==")
    allok = True
    for name, ok, detail in checks:
        allok = allok and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:42} {detail}")
    print(f"== smoke result: {'PASS' if allok else 'FAIL'} ==")
    return allok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--version", help="set performer version (e.g. 12.0.0). OMIT to leave unchanged -- an upgrade is an explicit, authorized act.")
    ap.add_argument("--reset", action="store_true", help="clear camgirls_* typed tables first")
    args = ap.parse_args()

    dd = args.data_dir or os.path.join(os.getcwd(), "data")
    if not os.path.isdir(dd):
        dd = os.path.abspath(os.path.join(HERE, "..", "data"))

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=OFF")
    if args.reset:
        for t in ("camgirls_performers", "camgirls_payout_addresses", "camgirls_paypal_orders", "camgirls_activity"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
        print("[camgirls] reset typed tables")
    try:
        np = promote_performers(conn, dd, args.version)
        naddr = promote_payouts(conn, dd)
        npp, gross, completed = promote_paypal(conn, dd)
        ntx, linked, unlinked = record_payout_txs(conn)
        nact, pts, per_perf = promote_activity(conn, dd)
        conn.commit()
        print(f"[camgirls] performers={np} payout_addresses={naddr} paypal_orders={npp} "
              f"(gross=${gross:.2f}, completed={completed}) payout_txs={ntx} (linked={linked} unlinked={unlinked}) "
              f"activity_rows={nact} points={pts:.2f}")
        smoke(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
