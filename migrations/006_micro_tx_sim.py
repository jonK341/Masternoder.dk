#!/usr/bin/env python3
"""Phase D -- micro-transaction SIMULATOR ("set the small transaction start").

DRY-RUN ONLY. It computes exactly what small MN2 sends WOULD happen and records them
in mn2_micro_tx_plan with status='simulated'. It NEVER calls node RPC and NEVER
broadcasts a transaction. Use this to validate amounts, fees, quotas and recipients
before any (separately authorized) live phase.

Config source: data/mn2_micro_tx_config.json
  { enabled, min_amount_mn2, max_amount_mn2, fee_mn2, daily_limit_mn2, confirmations }

Examples:
  # simulate one small send from a user to the shop revenue address
  python 006_micro_tx_sim.py --db ../test_real.db --data-dir ../local_fixture_data \
      --user user_3001 --amount 0.5 --to <Jaddress>
  # simulate a batch: one min-size send per user that has an address
  python 006_micro_tx_sim.py --db instance/database.db --data-dir data --batch
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_CFG_KEYS = {"enabled": False, "min_amount_mn2": 0.1, "max_amount_mn2": 5.0,
                    "fee_mn2": 0.01, "daily_limit_mn2": 50.0, "confirmations": 1}


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(p):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


def load_cfg(dd):
    cfg = dict(DEFAULT_CFG_KEYS)
    real = read_json(os.path.join(dd, "mn2_micro_tx_config.json"))
    if isinstance(real, dict):
        cfg.update({k: real[k] for k in real if k in DEFAULT_CFG_KEYS})
    return cfg


def fnum(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def get_from_address(conn, user_id):
    row = conn.execute(
        "SELECT address FROM mn2_addresses WHERE user_id=? AND is_valid=1 "
        "ORDER BY balance DESC, id LIMIT 1", (user_id,)).fetchone()
    return row[0] if row else None


def resolve_to(conn, explicit):
    if explicit:
        return explicit
    row = conn.execute(
        "SELECT value_text FROM mn2_metrics WHERE metric_key='shop.revenue_address' LIMIT 1").fetchone()
    return row[0] if row and row[0] else None


def daily_used(conn, user_id, plan_run=None):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_mn2),0) FROM mn2_micro_tx_plan "
        "WHERE from_user_id=? AND status='simulated' AND date(created_at)=?",
        (user_id, today())).fetchone()
    return fnum(row[0] if row else 0)


def evaluate(conn, cfg, user_id, amount, to_addr):
    """Return (status, reason, fee, total). status in {simulated, rejected}."""
    fee = fnum(cfg.get("fee_mn2"))
    total = round(fnum(amount) + fee, 8)
    lo, hi = fnum(cfg.get("min_amount_mn2")), fnum(cfg.get("max_amount_mn2"))
    limit = fnum(cfg.get("daily_limit_mn2"))
    if to_addr is None:
        return "rejected", "no_destination_address", fee, total
    if fnum(amount) < lo:
        return "rejected", f"below_min({lo})", fee, total
    if fnum(amount) > hi:
        return "rejected", f"above_max({hi})", fee, total
    used = daily_used(conn, user_id)
    if used + fnum(amount) > limit:
        return "rejected", f"over_daily_limit(used={used},limit={limit})", fee, total
    if get_from_address(conn, user_id) is None:
        return "rejected", "sender_has_no_valid_address", fee, total
    note = "ok" if cfg.get("enabled") else "ok_but_config_disabled"
    return "simulated", note, fee, total


def record(conn, plan_run, user_id, amount, to_addr, status, reason, fee, total):
    frm = get_from_address(conn, user_id)
    conn.execute(
        """INSERT INTO mn2_micro_tx_plan
             (plan_run, from_user_id, from_address, to_address, amount_mn2, fee_mn2,
              total_debit, rpc_method, status, reason, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (plan_run, user_id, frm, to_addr, fnum(amount), fee, total,
         "sendtoaddress", status, reason, utcnow()),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--user")
    ap.add_argument("--amount", type=float)
    ap.add_argument("--to", help="destination MN2 address (default: shop revenue address)")
    ap.add_argument("--batch", action="store_true",
                    help="simulate one min-size send per user that has a valid address")
    ap.add_argument("--batch-limit", type=int, default=25)
    args = ap.parse_args()

    dd = args.data_dir or os.path.join(os.getcwd(), "data")
    if not os.path.isdir(dd):
        dd = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    cfg = load_cfg(dd)
    plan_run = datetime.now(timezone.utc).strftime("plan_%Y%m%d_%H%M%S")

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        print(f"[sim] config: enabled={cfg.get('enabled')} min={cfg.get('min_amount_mn2')} "
              f"max={cfg.get('max_amount_mn2')} fee={cfg.get('fee_mn2')} "
              f"daily_limit={cfg.get('daily_limit_mn2')}")
        print(f"[sim] plan_run={plan_run}  (DRY-RUN: nothing is broadcast)")
        to_default = resolve_to(conn, args.to)

        jobs = []
        if args.batch:
            users = [r[0] for r in conn.execute(
                "SELECT DISTINCT user_id FROM mn2_addresses WHERE is_valid=1 "
                "AND user_id IS NOT NULL AND user_id NOT LIKE '\\_\\_%' ESCAPE '\\' "
                "ORDER BY user_id LIMIT ?", (args.batch_limit,))]
            amt = fnum(cfg.get("min_amount_mn2"), 0.1)
            jobs = [(u, amt, to_default) for u in users]
        elif args.user:
            jobs = [(args.user, fnum(args.amount, cfg.get("min_amount_mn2")), args.to or to_default)]
        else:
            ap.error("provide --user (with --amount) or --batch")

        sim = rej = 0
        for uid, amt, to_addr in jobs:
            status, reason, fee, total = evaluate(conn, cfg, uid, amt, to_addr)
            record(conn, plan_run, uid, amt, to_addr, status, reason, fee, total)
            if status == "simulated":
                sim += 1
            else:
                rej += 1
            print(f"  {uid:24} amt={amt} fee={fee} total={total} -> {status} ({reason})")
        conn.commit()
        print(f"[sim] done: simulated={sim} rejected={rej}  destination={to_default}")
        print("[sim] NOTE: to actually send, a separate live phase must be explicitly authorized.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
