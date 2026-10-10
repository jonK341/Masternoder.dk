#!/usr/bin/env python3
"""Phase C -- compute "as many MN2 stats as possible" into the DB, and merge each
user's scattered identifiers into ONE canonical wallet identity.

Reads (all optional, best-effort): data/mn2_ledger.json, mn2_order_payments.json,
mn2_masternode_hosts.json, mn2_masternode_orders.json, mn2_p2p_orders.json,
mn2_p2p_listings.json, mn2_onramp_orders.json, mn2_micro_tx_state.json,
mn2_micro_tx_config.json, mn2_staking_reserve.json, mn2_treasury_addresses.json,
mn2_copy_trading.json, mn2_config.json, aggregator_mn2_awards.json
+ the mn2_wallets / mn2_addresses / mn2_transactions / shop_purchases tables.

Writes: mn2_identity_aliases, mn2_user_stats, mn2_metrics, mn2_stats_runs.
SAFE: DB-only aggregation. Moves NO funds, no chain writes. Idempotent (upserts).

  python 005_compute_stats.py --db instance/database.db --data-dir data
  python 005_compute_stats.py --db ../test_real.db --data-dir ../local_fixture_data --no-fetch-price
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

USER_ID_RE = re.compile(r"^user_[0-9a-z_]+$")


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


def as_list(obj, key=None):
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        if key and isinstance(obj.get(key), list):
            return obj[key]
        if key and isinstance(obj.get(key), dict):
            return list(obj[key].values())
        # dict-of-records (e.g. masternode_orders keyed by order_id)
        vals = list(obj.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return vals
    return []


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def norm(alias):
    return str(alias).strip().lower()


# ---------------------------------------------------------------------------
# Identity resolution: group raw identifiers that normalize to the same string.
# Conservative: only case/whitespace merges (e.g. 'Jon'/'jon'). Name<->user_id
# merges need evidence, so they are left separate (add manual rows to override).
# ---------------------------------------------------------------------------
def build_aliases(raw_ids_by_source):
    """raw_ids_by_source: {source: set(raw_id)} -> list of (alias, canonical, source)."""
    groups = defaultdict(set)  # normalized -> raw variants
    for src, ids in raw_ids_by_source.items():
        for rid in ids:
            if rid:
                groups[norm(rid)].add(str(rid))
    canonical_of = {}
    for nkey, variants in groups.items():
        # prefer a real user_id form as canonical, else the shortest/first variant
        user_forms = [v for v in variants if USER_ID_RE.match(v)]
        canonical = sorted(user_forms)[0] if user_forms else sorted(variants, key=lambda s: (len(s), s))[0]
        for v in variants:
            canonical_of[v] = canonical
    rows = []
    for src, ids in raw_ids_by_source.items():
        for rid in ids:
            if rid:
                method = "exact" if str(rid) == canonical_of[str(rid)] else "normalize"
                rows.append((str(rid), canonical_of[str(rid)], src, method,
                             1.0 if method == "exact" else 0.9))
    return rows, canonical_of


# ---------------------------------------------------------------------------
# Metric upserts
# ---------------------------------------------------------------------------
def set_metric(conn, key, *, num=None, text=None, scope="global", scope_id="", as_of="", source=None):
    conn.execute(
        """INSERT INTO mn2_metrics (metric_key, value_num, value_text, scope, scope_id, as_of, source, updated_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(metric_key, scope, scope_id, as_of) DO UPDATE SET
             value_num=COALESCE(excluded.value_num, mn2_metrics.value_num),
             value_text=COALESCE(excluded.value_text, mn2_metrics.value_text),
             source=COALESCE(excluded.source, mn2_metrics.source),
             updated_at=excluded.updated_at""",
        (key, num, text, scope, str(scope_id), str(as_of), source, utcnow()),
    )


def upsert_user_stats(conn, s):
    conn.execute(
        """INSERT INTO mn2_user_stats
             (canonical_user_id, display_label, alias_count, address_count, valid_address_count,
              tx_count, total_in, total_out, net, masternode_count, collateral_total,
              order_payment_count, order_payment_mn2, p2p_order_count, onramp_order_count,
              micro_tx_runs, staking_reserve, first_seen, last_seen, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(canonical_user_id) DO UPDATE SET
             display_label=excluded.display_label, alias_count=excluded.alias_count,
             address_count=excluded.address_count, valid_address_count=excluded.valid_address_count,
             tx_count=excluded.tx_count, total_in=excluded.total_in, total_out=excluded.total_out,
             net=excluded.net, masternode_count=excluded.masternode_count,
             collateral_total=excluded.collateral_total, order_payment_count=excluded.order_payment_count,
             order_payment_mn2=excluded.order_payment_mn2, p2p_order_count=excluded.p2p_order_count,
             onramp_order_count=excluded.onramp_order_count, micro_tx_runs=excluded.micro_tx_runs,
             staking_reserve=excluded.staking_reserve, first_seen=COALESCE(mn2_user_stats.first_seen, excluded.first_seen),
             last_seen=excluded.last_seen, updated_at=excluded.updated_at""",
        (s["canonical_user_id"], s["display_label"], s["alias_count"], s["address_count"],
         s["valid_address_count"], s["tx_count"], s["total_in"], s["total_out"], s["net"],
         s["masternode_count"], s["collateral_total"], s["order_payment_count"],
         s["order_payment_mn2"], s["p2p_order_count"], s["onramp_order_count"],
         s["micro_tx_runs"], s["staking_reserve"], s["first_seen"], s["last_seen"], utcnow()),
    )


def table_exists(conn, t):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None


def cols_of(conn, t):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}


def fetch_price(base):
    try:
        req = urllib.request.Request(base.rstrip("/") + "/api/mn2/balance",
                                     headers={"User-Agent": "mn2-stats/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return fnum(d.get("mn2_usd_price")) or None, d
    except Exception:  # noqa: BLE001
        return None, {}


# ---------------------------------------------------------------------------
def compute(conn, dd, base_url, do_fetch_price):
    ledger = as_list(read_json(os.path.join(dd, "mn2_ledger.json")), "entries")
    payments = as_list(read_json(os.path.join(dd, "mn2_order_payments.json")), "orders")
    hosts = as_list(read_json(os.path.join(dd, "mn2_masternode_hosts.json")), "hosts")
    mn_orders = as_list(read_json(os.path.join(dd, "mn2_masternode_orders.json")))
    p2p_orders = as_list(read_json(os.path.join(dd, "mn2_p2p_orders.json")))
    p2p_listings = as_list(read_json(os.path.join(dd, "mn2_p2p_listings.json")))
    onramp = as_list(read_json(os.path.join(dd, "mn2_onramp_orders.json")))
    micro_state = read_json(os.path.join(dd, "mn2_micro_tx_state.json")) or {}
    micro_cfg = read_json(os.path.join(dd, "mn2_micro_tx_config.json")) or {}
    staking = read_json(os.path.join(dd, "mn2_staking_reserve.json"))
    treasury = read_json(os.path.join(dd, "mn2_treasury_addresses.json"))
    copyt = read_json(os.path.join(dd, "mn2_copy_trading.json")) or {}
    cfg = read_json(os.path.join(dd, "mn2_config.json")) or {}
    awards = read_json(os.path.join(dd, "aggregator_mn2_awards.json"))

    # ---- collect raw identifiers per source ----
    ids = defaultdict(set)
    for e in ledger:
        if isinstance(e, dict) and e.get("user_id"):
            ids["ledger"].add(e["user_id"])
    for o in payments:
        if isinstance(o, dict) and o.get("user_id"):
            ids["order_payments"].add(o["user_id"])
    for h in hosts:
        if isinstance(h, dict) and h.get("owner_user_id"):
            ids["masternode_hosts"].add(h["owner_user_id"])
    for o in mn_orders:
        if isinstance(o, dict) and o.get("user_id"):
            ids["masternode_orders"].add(o["user_id"])
    for o in p2p_orders:
        if isinstance(o, dict):
            for k in ("buyer_id", "seller_id"):
                if o.get(k):
                    ids["p2p_orders"].add(o[k])
    for l in p2p_listings:
        if isinstance(l, dict) and l.get("seller_id"):
            ids["p2p_listings"].add(l["seller_id"])
    for o in onramp:
        if isinstance(o, dict) and o.get("user_id"):
            ids["onramp"].add(o["user_id"])
    if isinstance(micro_state.get("users"), dict):
        ids["micro_tx"].update(micro_state["users"].keys())
    if isinstance(copyt.get("followers"), dict):
        ids["copy_trading"].update(copyt["followers"].keys())
    if table_exists(conn, "mn2_addresses"):
        for (u,) in conn.execute("SELECT DISTINCT user_id FROM mn2_addresses WHERE user_id IS NOT NULL"):
            ids["db_addresses"].add(u)

    alias_rows, canon = build_aliases(ids)
    conn.executemany(
        """INSERT INTO mn2_identity_aliases (alias, canonical_user_id, source, method, confidence, created_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(alias, source) DO UPDATE SET canonical_user_id=excluded.canonical_user_id,
             method=excluded.method, confidence=excluded.confidence""",
        [(a, c, s, m, cf, utcnow()) for (a, c, s, m, cf) in alias_rows],
    )

    def C(raw):  # canonicalize a raw id
        return canon.get(str(raw), str(raw)) if raw else None

    # ---- per-user aggregation ----
    U = defaultdict(lambda: {"in": 0.0, "out": 0.0, "tx": 0, "addrs": set(), "valid": set(),
                             "mn": 0, "collateral": 0.0, "pay_n": 0, "pay_mn2": 0.0,
                             "p2p": 0, "onramp": 0, "micro": 0, "staking": 0.0,
                             "first": None, "last": None, "aliases": set()})
    for src, raws in ids.items():
        for r in raws:
            U[C(r)]["aliases"].add(str(r))

    for e in ledger:
        if not isinstance(e, dict):
            continue
        u = C(e.get("user_id"))
        if not u:
            continue
        amt = fnum(e.get("amount"))
        d = U[u]
        d["tx"] += 1
        if amt >= 0:
            d["in"] += amt
        else:
            d["out"] += -amt
        if e.get("address"):
            d["addrs"].add(e["address"])
        ts = e.get("created_at")
        if ts:
            d["first"] = min(d["first"], ts) if d["first"] else ts
            d["last"] = max(d["last"], ts) if d["last"] else ts
    for o in payments:
        if not isinstance(o, dict):
            continue
        u = C(o.get("user_id"))
        if u:
            U[u]["pay_n"] += 1
            U[u]["pay_mn2"] += fnum(o.get("amount_mn2", o.get("amount")))
            if o.get("address"):
                U[u]["addrs"].add(o["address"])
    for h in hosts:
        if not isinstance(h, dict):
            continue
        u = C(h.get("owner_user_id"))
        if u:
            U[u]["mn"] += 1
            U[u]["collateral"] += fnum(h.get("collateral_mn2"))
            for f in ("collateral_address", "broadcast_address"):
                if h.get(f):
                    U[u]["addrs"].add(h[f])
    for o in mn_orders:
        if isinstance(o, dict) and o.get("user_id"):
            U[C(o["user_id"])]["mn"] += 0  # orders counted under hosts; keep alias warm
    for o in p2p_orders:
        if isinstance(o, dict):
            for k in ("buyer_id", "seller_id"):
                if o.get(k):
                    U[C(o[k])]["p2p"] += 1
    for o in onramp:
        if isinstance(o, dict) and o.get("user_id"):
            U[C(o["user_id"])]["onramp"] += 1
    if isinstance(micro_state.get("users"), dict):
        for raw, st in micro_state["users"].items():
            u = C(raw)
            runs = st.get("runs") if isinstance(st, dict) else None
            U[u]["micro"] += fnum(runs) if runs is not None else 1

    # address validity + counts from DB (authoritative for stored addresses)
    db_addr = defaultdict(lambda: [0, 0])  # canonical -> [total, valid]
    if table_exists(conn, "mn2_addresses"):
        for u, valid in conn.execute("SELECT user_id, is_valid FROM mn2_addresses WHERE user_id IS NOT NULL"):
            cu = C(u)
            db_addr[cu][0] += 1
            db_addr[cu][1] += 1 if valid else 0

    for u, d in U.items():
        atot, avalid = db_addr.get(u, [len(d["addrs"]), len(d["addrs"])])
        upsert_user_stats(conn, {
            "canonical_user_id": u,
            "display_label": sorted(d["aliases"])[0] if d["aliases"] else u,
            "alias_count": len(d["aliases"]),
            "address_count": max(atot, len(d["addrs"])),
            "valid_address_count": avalid,
            "tx_count": d["tx"],
            "total_in": round(d["in"], 8),
            "total_out": round(d["out"], 8),
            "net": round(d["in"] - d["out"], 8),
            "masternode_count": d["mn"],
            "collateral_total": round(d["collateral"], 8),
            "order_payment_count": d["pay_n"],
            "order_payment_mn2": round(d["pay_mn2"], 8),
            "p2p_order_count": d["p2p"],
            "onramp_order_count": d["onramp"],
            "micro_tx_runs": int(d["micro"]),
            "staking_reserve": round(d["staking"], 8),
            "first_seen": d["first"],
            "last_seen": d["last"],
        })

    # ---- global metrics ----
    set_metric(conn, "identity.canonical_users", num=len(U), source="compute_stats")
    set_metric(conn, "identity.raw_aliases", num=len(alias_rows), source="compute_stats")
    set_metric(conn, "ledger.entries_total", num=len(ledger), source="mn2_ledger.json")
    set_metric(conn, "ledger.users_distinct", num=len({C(e.get('user_id')) for e in ledger if isinstance(e, dict)}), source="mn2_ledger.json")
    set_metric(conn, "ledger.with_txid", num=sum(1 for e in ledger if isinstance(e, dict) and e.get("txid")), source="mn2_ledger.json")
    vol_in = sum(fnum(e.get("amount")) for e in ledger if isinstance(e, dict) and fnum(e.get("amount")) >= 0)
    vol_out = sum(-fnum(e.get("amount")) for e in ledger if isinstance(e, dict) and fnum(e.get("amount")) < 0)
    set_metric(conn, "ledger.volume_in", num=round(vol_in, 8), source="mn2_ledger.json")
    set_metric(conn, "ledger.volume_out", num=round(vol_out, 8), source="mn2_ledger.json")
    set_metric(conn, "ledger.volume_net", num=round(vol_in - vol_out, 8), source="mn2_ledger.json")

    # by type
    tcount = Counter(e.get("type") for e in ledger if isinstance(e, dict))
    tvol = defaultdict(float)
    for e in ledger:
        if isinstance(e, dict):
            tvol[e.get("type")] += abs(fnum(e.get("amount")))
    for t, n in tcount.items():
        set_metric(conn, "ledger.type.count", num=n, scope="type", scope_id=str(t), source="mn2_ledger.json")
        set_metric(conn, "ledger.type.volume", num=round(tvol[t], 8), scope="type", scope_id=str(t), source="mn2_ledger.json")

    # by day
    dayc = Counter()
    dayv = defaultdict(float)
    for e in ledger:
        if isinstance(e, dict) and e.get("created_at"):
            day = str(e["created_at"])[:10]
            dayc[day] += 1
            dayv[day] += abs(fnum(e.get("amount")))
    for day, n in dayc.items():
        set_metric(conn, "ledger.day.tx_count", num=n, scope="day", as_of=day, source="mn2_ledger.json")
        set_metric(conn, "ledger.day.volume", num=round(dayv[day], 8), scope="day", as_of=day, source="mn2_ledger.json")

    # addresses / wallets from DB
    if table_exists(conn, "mn2_addresses"):
        set_metric(conn, "addresses.total", num=conn.execute("SELECT COUNT(*) FROM mn2_addresses").fetchone()[0], source="db")
        set_metric(conn, "addresses.valid", num=conn.execute("SELECT COUNT(*) FROM mn2_addresses WHERE is_valid=1").fetchone()[0], source="db")
        set_metric(conn, "addresses.invalid", num=conn.execute("SELECT COUNT(*) FROM mn2_addresses WHERE is_valid=0").fetchone()[0], source="db")
    if table_exists(conn, "mn2_wallets"):
        set_metric(conn, "wallets.total", num=conn.execute("SELECT COUNT(*) FROM mn2_wallets").fetchone()[0], source="db")
    if table_exists(conn, "mn2_transactions"):
        set_metric(conn, "transactions.total", num=conn.execute("SELECT COUNT(*) FROM mn2_transactions").fetchone()[0], source="db")
        set_metric(conn, "transactions.confirmed", num=conn.execute("SELECT COUNT(*) FROM mn2_transactions WHERE status='confirmed'").fetchone()[0], source="db")

    # masternodes
    set_metric(conn, "masternodes.hosts", num=len(hosts), source="mn2_masternode_hosts.json")
    set_metric(conn, "masternodes.collateral_total", num=round(sum(fnum(h.get("collateral_mn2")) for h in hosts if isinstance(h, dict)), 8), source="mn2_masternode_hosts.json")
    set_metric(conn, "masternodes.orders", num=len(mn_orders), source="mn2_masternode_orders.json")
    set_metric(conn, "masternodes.orders_mn2_total", num=round(sum(fnum(o.get("mn2_total")) for o in mn_orders if isinstance(o, dict)), 8), source="mn2_masternode_orders.json")

    # payments / shop
    set_metric(conn, "payments.count", num=len(payments), source="mn2_order_payments.json")
    set_metric(conn, "payments.mn2_total", num=round(sum(fnum(o.get("amount_mn2", o.get("amount"))) for o in payments if isinstance(o, dict)), 8), source="mn2_order_payments.json")
    if table_exists(conn, "shop_purchases"):
        set_metric(conn, "shop.purchases_total", num=conn.execute("SELECT COUNT(*) FROM shop_purchases").fetchone()[0], source="db")
        if "onchain" in cols_of(conn, "shop_purchases"):
            set_metric(conn, "shop.purchases_onchain", num=conn.execute("SELECT COUNT(*) FROM shop_purchases WHERE onchain=1").fetchone()[0], source="db")
        if "payment_method" in cols_of(conn, "shop_purchases"):
            for m, n in conn.execute("SELECT COALESCE(payment_method,'(null)'), COUNT(*) FROM shop_purchases GROUP BY 1"):
                set_metric(conn, "shop.purchases_by_method", num=n, scope="source", scope_id=str(m), source="db")

    # p2p / onramp
    set_metric(conn, "p2p.listings", num=len(p2p_listings), source="mn2_p2p_listings.json")
    set_metric(conn, "p2p.orders", num=len(p2p_orders), source="mn2_p2p_orders.json")
    set_metric(conn, "p2p.volume_mn2", num=round(sum(fnum(o.get("mn2_amount")) for o in p2p_orders if isinstance(o, dict)), 8), source="mn2_p2p_orders.json")
    set_metric(conn, "onramp.orders", num=len(onramp), source="mn2_onramp_orders.json")
    set_metric(conn, "onramp.mn2_total", num=round(sum(fnum(o.get("mn2_amount")) for o in onramp if isinstance(o, dict)), 8), source="mn2_onramp_orders.json")
    set_metric(conn, "onramp.usd_total", num=round(sum(fnum(o.get("usd_amount")) for o in onramp if isinstance(o, dict)), 8), source="mn2_onramp_orders.json")

    # micro-tx config (the "small transaction start" knobs -- reported, NOT changed)
    if isinstance(micro_cfg, dict):
        set_metric(conn, "microtx.enabled", text=str(micro_cfg.get("enabled")), source="mn2_micro_tx_config.json")
        set_metric(conn, "microtx.min_amount_mn2", num=fnum(micro_cfg.get("min_amount_mn2")), source="mn2_micro_tx_config.json")
        set_metric(conn, "microtx.max_amount_mn2", num=fnum(micro_cfg.get("max_amount_mn2")), source="mn2_micro_tx_config.json")
    if isinstance(micro_state.get("users"), dict):
        set_metric(conn, "microtx.users", num=len(micro_state["users"]), source="mn2_micro_tx_state.json")
        set_metric(conn, "microtx.runs", num=fnum(micro_state.get("runs")), source="mn2_micro_tx_state.json")

    # treasury / staking / copy-trading / awards / config
    taddrs = as_list(treasury, "addresses") if treasury else []
    set_metric(conn, "treasury.address_count", num=len(taddrs) if isinstance(treasury, (list, dict)) else 0, source="mn2_treasury_addresses.json")
    if isinstance(staking, dict):
        set_metric(conn, "staking.reserve_keys", num=len(staking), source="mn2_staking_reserve.json")
    if isinstance(copyt.get("followers"), dict):
        set_metric(conn, "copytrading.followers", num=len(copyt["followers"]), source="mn2_copy_trading.json")
    if awards is not None:
        set_metric(conn, "awards.entries", num=len(awards) if isinstance(awards, (list, dict)) else 0, source="aggregator_mn2_awards.json")
    if isinstance(cfg, dict):
        for k in ("ticker", "decimals", "confirmations"):
            if k in cfg:
                v = cfg[k]
                set_metric(conn, f"config.{k}", num=(fnum(v) if not isinstance(v, str) else None),
                           text=(str(v) if isinstance(v, str) else None), source="mn2_config.json")

    # live USD price + shop revenue address (best-effort, public endpoint)
    if do_fetch_price:
        price, bal = fetch_price(base_url)
        src = base_url + "/api/mn2/balance"
        if price:
            set_metric(conn, "price.mn2_usd", num=price, as_of=today(), source=src)
        if isinstance(bal, dict):
            if bal.get("coins_per_mn2") is not None:
                set_metric(conn, "price.coins_per_mn2", num=fnum(bal.get("coins_per_mn2")), source=src)
            if bal.get("shop_revenue_address"):
                set_metric(conn, "shop.revenue_address", text=str(bal.get("shop_revenue_address")), source=src)
            if bal.get("shop_revenue_explorer_url"):
                set_metric(conn, "shop.revenue_explorer_url", text=str(bal.get("shop_revenue_explorer_url")), source=src)

    return {"users": len(U), "aliases": len(alias_rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--base-url", default="https://masternoder.dk")
    ap.add_argument("--no-fetch-price", action="store_true")
    args = ap.parse_args()

    dd = args.data_dir or os.path.join(os.getcwd(), "data")
    if not os.path.isdir(dd):
        dd = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        res = compute(conn, dd, args.base_url, not args.no_fetch_price)
        n_metrics = conn.execute("SELECT COUNT(*) FROM mn2_metrics").fetchone()[0]
        conn.execute(
            "INSERT INTO mn2_stats_runs (run_at, status, users_computed, metrics_written, detail) VALUES (?,?,?,?,?)",
            (utcnow(), "ok", res["users"], n_metrics, f"data_dir={dd}"),
        )
        conn.commit()
        print(f"[stats] canonical_users={res['users']} aliases={res['aliases']} total_metrics_rows={n_metrics}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
